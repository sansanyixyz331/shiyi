#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拾意 · L0 卡生成器 v2 —— 「意图 -> 卡」的完整机器。

v1 只是"把识别结果摆进一张卡"。v2 把六样能力真正装了进去：

  1) 意图识别引擎   src/intent_card.py            (规则 + 模型两路)
  2) 长期记忆层     src/memory_store.py           (真文件真读写，替掉硬编码)
  3) 契约 + 适配器   INTENT_ADAPTERS               (加一种意图 = 注册一条，核心不动)
  4) 反思 -> 自评修订  selfcheck() / revise()      (看自己排的版，越界/超带/溢出就改)
  5) 自动化工具链    build/pipeline.py            (生成->修订->渲染->门禁，一条命令)
  6) 应用造应用      本文件自身                    (一个 app，从一条消息造出另一个 app 包)

设计要点（都是踩过的坑）：
  · L0 遍地 `{}`，模板必须用 string.Template（`$var`），不能用 f-string/format。
  · 行数随意图变 => 每个节点的 y 必须重排，否则重叠 / 溢出 / 撞动作带。
  · 文本进 copy 前必须清洗 `"` `{}` 与换行，否则破坏 L0 解析。
  · 自评是"几何判据"：越界、内容越过动作带、文本超出可用格 —— 不靠肉眼。

用法:
    python build/gen_l0.py --text "下周三我得去趟深圳" --room 家庭群 --out build/_gen/trip
    python build/gen_l0.py --samples --out build/_gen
    （--memory 指向 memory.json；缺省用仓库 .local-state/memory.json）

只往 --out 写。bundle/ 与 tag 一字节不动。
"""

import argparse
import datetime as dt
import json
import math
import os
import re
import shutil
import subprocess
import sys
from string import Template

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
LINT = os.path.join(ROOT, "tools", "l0_bindings_lint.py")
SHARED_KIT = os.path.join(ROOT, "bundle", "kit")
SHARED_ASSETS = os.path.join(ROOT, "bundle", "assets")

sys.path.insert(0, SRC)
from intent_card import build_card            # noqa: E402  能力①
try:
    from memory_store import MemoryStore      # noqa: E402  能力②
except Exception:                             # pragma: no cover
    MemoryStore = None

WD = ["一", "二", "三", "四", "五", "六", "日"]
TYPE_ZH = {
    "trip": "出行安排", "meeting": "会面", "errand": "跑腿代办",
    "purchase": "采购", "reminder": "提醒", "unknown": "待确认",
}


# ==================================================================== 能力③ 契约 + 适配器
# 一种意图 = 一条适配器声明。加新意图只往这里加一行，generate 的核心不动。
# 这就是三三Claw 接口层那套"契约 + 自注册工厂"在一个新生态里的落法。
DEFAULT_ADAPTER = {
    "heading": "从你发过的话里，读出了一件事",
    "ask": "要把它落到实处",
}
INTENT_ADAPTERS = {
    "trip":     {"heading": "从你发过的话里，读出了一个安排", "ask": "要把它排成一次行程"},
    "meeting":  {"heading": "从你发过的话里，读出了一次会面", "ask": "要把它定成一次会面"},
    "errand":   {"heading": "从你发过的话里，读出了一件要办的事", "ask": "要把它办掉"},
    "purchase": {"heading": "从你发过的话里，读出了一件要买的", "ask": "要把它安排上"},
    "reminder": {"heading": "从你发过的话里，读出了一条提醒", "ask": "要把它记成一条提醒"},
}


def adapter_for(kind):
    return INTENT_ADAPTERS.get(kind, DEFAULT_ADAPTER)


# 记忆命中 -> 卡面文案
MEMO_ZH = {
    "excluded_flight": "从本机记忆里读到：你不坐飞机。",
    "filtered_to_rail": "所以往下只给你高铁方案。",
    "flagged_schedule_conflict": "注意：这天下午你通常不排事，可能冲突。",
}

# 每个组件能装多少字（粗略几何）：字号 px、行高 px。用于自评"文本溢出"。
TEXT_METRICS = {
    "eyebrow": (11.0, 15.0), "heading": (23.0, 31.0), "quote": (17.0, 26.0),
    "source": (12.0, 16.0), "row": (15.0, 21.0), "note": (13.0, 19.0),
    "action_label": (16.0, 21.0), "ghost_label": (15.0, 20.0),
}


# ==================================================================== 文本

def clean(s, limit=64):
    """把任意原文洗成能放进 L0 copy 双引号的单行文本。"""
    if s is None:
        return ""
    s = str(s).replace("\r", " ").replace("\n", " ").replace("\t", " ")
    s = s.replace('"', "”").replace("{", "（").replace("}", "）")
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > limit:
        s = s[: limit - 1] + "…"
    return s


def fmt_when(iso):
    if not iso:
        return None
    try:
        d = dt.datetime.fromisoformat(iso)
    except ValueError:
        return None
    s = "%d月%d日 周%s" % (d.month, d.day, WD[d.weekday()])
    if d.hour or d.minute:
        s += " %02d:%02d" % (d.hour, d.minute)
    return s


# ==================================================================== 能力① 识别 -> 行

def plan(card, drop_memo=0):
    """把识别结果摊成要渲染的行 + 每行文案。drop_memo 供自评修订从后往前丢记忆行。"""
    f = card["fields"]
    when, where, intent = f["when"], f["where"], f["intent"]
    ad = adapter_for(intent.get("type", "unknown"))

    lines, copies = [], {}

    if when.get("resolved"):
        txt = "时间 · %s · 出自原文" % fmt_when(when["resolved"])
        if when.get("confidence", 0) < 0.7:
            txt = "时间 · %s · 低置信，待你确认" % fmt_when(when["resolved"])
        copies["when"] = txt
        lines.append("when")
    elif when.get("clock"):
        copies["when"] = "时间 · 只有「%s」，没定哪天 · 待你确认" % clean(when["clock"], 16)
        lines.append("when")

    if where.get("normalized"):
        copies["where"] = "地点 · %s · 出自原文" % clean(where["normalized"], 24)
        lines.append("where")

    tz = TYPE_ZH.get(intent.get("type"), "待确认")
    conf = intent.get("confidence", 0)
    copies["kind"] = "类型 · %s · %s" % (tz, "识别所得" if conf >= 0.5 else "说不准，待你确认")
    lines.append("kind")

    qs = [q["ask"] for q in card.get("questions", [])]
    open_line = ("还没定：" + "；".join(clean(q, 30) for q in qs[:2])) if qs else "该定的都定了，没有要问的。"

    memo = []
    seen = set()
    for e in [x.get("effect") for x in card.get("memory", {}).get("effects", [])]:
        if e in MEMO_ZH and e not in seen:
            seen.add(e)
            memo.append(MEMO_ZH[e])
    if drop_memo:
        memo = memo[: max(0, len(memo) - drop_memo)]

    return {
        "lines": lines, "copies": copies, "open_line": open_line,
        "memo_lines": memo, "heading": ad["heading"], "ask": ad["ask"],
        "intent_type": intent.get("type", "unknown"), "intent_conf": conf,
        "quote_disp": clean(card.get("quote", ""), 40),
    }


# ==================================================================== 布局

PAGE_W, PAGE_H = 412, 892
ACTION_TOP = 740
TOP = (("eyebrow", "eyebrow", 24, 36, 364, 16),
       ("heading", "heading", 24, 58, 364, 62))

QUOTE_PER_LINE = 19        # quote 组件一行约装多少字（324px / 17px）


def quote_rows(t):
    """原文要几行才能放下 —— 卡会长高来装，而不是把原文一刀切。"""
    return max(1, math.ceil(len(t or "") / QUOTE_PER_LINE))
BOTTOM = (("action_fix", "action", 24, 740, 364, 46),
          ("action_fix_bg", "action_ghost", 24, 740, 364, 46),
          ("action_fix_ctl", "action_control", 24, 740, 364, 46),
          ("action_fix_lbl", "ghost_label", 24, 753, 364, 20),
          ("action_yes", "action", 24, 800, 364, 54),
          ("action_yes_bg", "action_fill", 24, 800, 364, 54),
          ("action_yes_ctl", "action_control", 24, 800, 364, 54),
          ("action_yes_lbl", "action_label", 24, 816, 364, 22))
# 合法叠加（子节点盖在容器上、控件/标签盖在按钮上）—— 自评"重叠"时要豁免
ALLOW_OVERLAP = {
    ("quote", "quote_band"), ("quote_src", "quote_band"),
}
BUTTON_GROUPS = ("action_yes", "action_fix")   # 一个按钮 = 底/控件/标签同位置叠放


def _exempt(a, b):
    """这一对节点的重叠是不是设计使然（容器/按钮内部结构）。"""
    if (a, b) in ALLOW_OVERLAP or (b, a) in ALLOW_OVERLAP:
        return True
    return any(a.startswith(g) and b.startswith(g) for g in BUTTON_GROUPS)


def placements(field_keys, memo_keys, quote_rows_n=1):
    P = {}

    def put(name, comp, x, y, w, h):
        P[name] = {"component": comp, "layout": {"x": x, "y": y, "w": w, "h": h}}

    put("page", "page", 0, 0, PAGE_W, PAGE_H)
    for name, comp, x, y, w, h in TOP:
        put(name, comp, x, y, w, h)

    # quote 区随原文行数长高：band = pad + quote + gap + source + pad
    qh = max(32, quote_rows_n * 26)
    band_h = qh + 78
    put("quote_band", "band", 24, 140, 364, band_h)
    put("quote", "quote", 44, 164, 324, qh)
    put("quote_src", "source", 44, 164 + qh + 16, 324, 16)
    rule1_y = 140 + band_h + 24
    put("rule_1", "hairline", 24, rule1_y, 364, 1)

    y = rule1_y + 18
    for k in field_keys:
        put("row_" + k, "row", 24, y, 364, 22)
        y += 26
    put("row_open", "note", 24, y, 364, 44)
    y += 50
    put("row_ai", "note", 24, y, 364, 44)
    y += 50
    put("row_src", "note", 24, y, 364, 20)
    y += 28
    put("rule_2", "hairline", 24, y, 364, 1)
    y += 20
    for k in memo_keys:
        put(k, "note", 24, y, 364, 20)
        y += 24

    for name, comp, x, y, w, h in BOTTOM:
        put(name, comp, x, y, w, h)
    return P


# ==================================================================== 能力④ 自评 -> 修订

def _capacity(comp, w, h):
    """一个文本组件大致能装多少字。"""
    fs, lh = TEXT_METRICS.get(comp, (14.0, 20.0))
    per_line = max(1, int(w // fs))
    rows = max(1, int(h // lh))
    return per_line * rows


def selfcheck(P, texts):
    """几何自评：越界 / 越过动作带 / 组件间重叠 / 文本超格。不靠肉眼。"""
    issues = []

    for name, node in P.items():
        L = node["layout"]
        if L["x"] < 0 or L["y"] < 0 or L["x"] + L["w"] > PAGE_W or L["y"] + L["h"] > PAGE_H:
            issues.append({"kind": "out-of-bounds", "node": name, "layout": L})

    # 内容区不得越过动作带（action_* 一律从 740 起，且是底层容器）
    content = {n: v for n, v in P.items()
               if not n.startswith("action_") and n not in ("page",)}
    bottom = max((v["layout"]["y"] + v["layout"]["h"] for v in content.values()), default=0)
    if bottom > ACTION_TOP - 8:
        issues.append({"kind": "content-overruns-band", "bottom": bottom,
                       "limit": ACTION_TOP - 8,
                       "excess_px": bottom - (ACTION_TOP - 8)})

    # 重叠
    names = [n for n in P if n != "page"]
    for i, a in enumerate(names):
        La = P[a]["layout"]
        for b in names[i + 1:]:
            Lb = P[b]["layout"]
            if _exempt(a, b):
                continue
            ox = min(La["x"] + La["w"], Lb["x"] + Lb["w"]) - max(La["x"], Lb["x"])
            oy = min(La["y"] + La["h"], Lb["y"] + Lb["h"]) - max(La["y"], Lb["y"])
            if ox > 0 and oy > 0:
                issues.append({"kind": "overlap", "a": a, "b": b, "overlap": [ox, oy]})

    # 文本超格
    for name, node in P.items():
        t = texts.get(name)
        if not t:
            continue
        cap = _capacity(node["component"], node["layout"]["w"], node["layout"]["h"])
        if len(t) > cap:
            issues.append({"kind": "text-overflow", "node": name,
                           "chars": len(t), "capacity": cap})
    return issues


def revise(p, issues, attempt):
    """按自评结论改：先短文案，再缩原文行数，再丢记忆行 —— 改的是"这一版"，不动引擎。"""
    fixes = []
    p = dict(p)
    p["copies"] = dict(p["copies"])
    over = {i["node"] for i in issues if i["kind"] == "text-overflow"}
    overruns = any(i["kind"] == "content-overruns-band" for i in issues)

    if "row_open" in over or overruns:
        old = p["open_line"]
        p["open_line"] = clean(old, max(16, len(old) - 14))
        if len(p["open_line"]) != len(old):
            fixes.append("shorten row_open %d->%d" % (len(old), len(p["open_line"])))

    for k in ("when", "where"):
        if "row_" + k in over and k in p["copies"]:
            p["copies"][k] = clean(p["copies"][k], 18)
            fixes.append("shorten row_%s" % k)

    # 还是顶到动作带：先缩原文一行，再丢记忆行
    if overruns:
        qd = p.get("quote_disp", "")
        rows = quote_rows(qd)
        if rows > 1:
            p["quote_disp"] = clean(qd, (rows - 1) * QUOTE_PER_LINE)
            fixes.append("trim quote %d->%d rows" % (rows, rows - 1))
        elif p["memo_lines"]:
            p["memo_lines"] = p["memo_lines"][:-1]
            fixes.append("drop last memo line (%d left)" % len(p["memo_lines"]))

    return p, fixes


def texts_of(p, card=None):
    t = {"heading": p["heading"], "row_open": p["open_line"]}
    if card is not None:
        t["quote"] = clean(card.get("quote", ""), 40)
    for k in p["lines"]:
        t["row_" + k] = p["copies"][k]
    for i, m in enumerate(p["memo_lines"]):
        t["memo_%d" % i] = clean(m, 48)
    return t


COMPONENTS = """# ── components ───────────────────────────────────────────────────────────────
component Page(instance: text) {
  view Kit(component: "page", instance: instance) { slot }
}
component Slab(instance: text) {
  view Kit(component: "band", instance: instance) { slot }
}
component Hairline(instance: text) {
  view Kit(component: "hairline", instance: instance)
}
component Eyebrow(instance: text, text: text) {
  view Kit(component: "eyebrow", instance: instance, text: text)
}
component Heading(instance: text, text: text) {
  view Kit(component: "heading", instance: instance, text: text)
}
component Quote(instance: text, text: text) {
  view Kit(component: "quote", instance: instance, text: text)
}
component Source(instance: text, text: text) {
  view Kit(component: "source", instance: instance, text: text)
}
component Line(instance: text, text: text) {
  view Kit(component: "row", instance: instance, text: text)
}
component Note(instance: text, text: text) {
  view Kit(component: "note", instance: instance, text: text)
}
component Action(instance: text) {
  view Kit(component: "action", instance: instance) { slot }
}
component ActionFill(instance: text) {
  view Kit(component: "action_fill", instance: instance) { slot }
}
component ActionGhost(instance: text) {
  view Kit(component: "action_ghost", instance: instance) { slot }
}
component ActionControl(instance: text, enabled: bool) {
  view Kit(component: "action_control", instance: instance, enabled: enabled)
}
component ActionLabel(instance: text, text: text) {
  view Kit(component: "action_label", instance: instance, text: text)
}
component GhostLabel(instance: text, text: text) {
  view Kit(component: "ghost_label", instance: instance, text: text)
}
"""

CARD_TMPL = Template("""# ledger shiyi-gen@${version}
# level: L0
# profile: ui/l0
# model: shiyi
#
# 拾意 · Pickup — GENERATED screen (intent -> card).
# generator  : build/gen_l0.py
# generated  : ${generated_at}
# intent     : ${intent_type} (confidence ${intent_conf})
# adapter    : ${adapter_note}
# memory     : ${memory_note}
# self-review: ${review_note}
# source     : ${source_desc}
#
# 这张卡不是手写的：它由「意图识别引擎」(src/intent_card.py) 的输出组装而成，
# 长出来的行、文案、位置随消息而变；排完之后还会自评一遍（越界/超带/超格），
# 有问题就改再出。纪律与手写版一致：每条事实都带来源；拿不准的写「还没定」。
# 宿主没有设备助手时，本地规则行照常渲染 —— 没有 AI 也完整可用。
theme light

state act_enabled { shape: bool, initial: true }
state read { shape: text }

copy eyebrow   { class: vocabulary, en: "${eyebrow}", zh: "${eyebrow}" }
copy heading   { class: vocabulary, en: "${heading}", zh: "${heading}" }

copy quote     { class: user-copy,  en: "「${quote}」", zh: "「${quote}」" }
copy quote_src { class: vocabulary, en: "${quote_src}", zh: "${quote_src}" }

${field_copies}
copy f_open    { class: vocabulary, en: "${open_line}", zh: "${open_line}" }
copy f_src     { class: vocabulary, en: "识别来源 · 本地规则（设备助手可用时另加一行）", zh: "识别来源 · 本地规则（设备助手可用时另加一行）" }

${memo_copies}
copy act_yes   { class: vocabulary, en: "对，就是这件事", zh: "对，就是这件事" }
copy act_fix   { class: vocabulary, en: "不对，改一下", zh: "不对，改一下" }

${components}
# ── view ─────────────────────────────────────────────────────────────────────
view root Page(instance: "page") {
  Eyebrow(instance: "eyebrow", text: copy.eyebrow)
  Heading(instance: "heading", text: copy.heading)

  Slab(instance: "quote_band") {
    Quote(instance: "quote", text: copy.quote)
    Source(instance: "quote_src", text: copy.quote_src)
  }

  Hairline(instance: "rule_1")

${field_rows}
  Note(instance: "row_open",  text: copy.f_open)

  # 设备助手的回答：只有它真回了才渲染（read.is_ok）。失败/未配置时这条
  # guard 为假、整条路径不求值 —— 一个哑掉的助手不会把这张卡弄崩。
  when read.is_ok { Note(instance: "row_ai", text: read.data.text) }

  Note(instance: "row_src",   text: copy.f_src)

  Hairline(instance: "rule_2")

${memo_rows}
  Action(instance: "action_yes") {
    ActionFill(instance: "action_yes_bg") {

    }
    ActionControl(instance: "action_yes_ctl", enabled: act_enabled)
    ActionLabel(instance: "action_yes_lbl", text: copy.act_yes)
  }
  Action(instance: "action_fix") {
    ActionGhost(instance: "action_fix_bg") {

    }
    ActionControl(instance: "action_fix_ctl", enabled: act_enabled)
    GhostLabel(instance: "action_fix_lbl", text: copy.act_fix)
  }
}
""")


def render_card(p, card, version, generated_at, review_note, memory_note):
    field_copies = "\n".join(
        'copy f_%s   { class: vocabulary, en: "%s", zh: "%s" }' % (k, p["copies"][k], p["copies"][k])
        for k in p["lines"])
    field_rows = "\n".join('  Line(instance: "row_%s", text: copy.f_%s)' % (k, k) for k in p["lines"])

    memo_keys = ["memo_%d" % i for i in range(len(p["memo_lines"]))]
    memo_copies = "\n".join('copy %s { class: vocabulary, en: "%s", zh: "%s" }' % (k, clean(t, 48), clean(t, 48))
                            for k, t in zip(memo_keys, p["memo_lines"]))
    if memo_copies:
        memo_copies += "\n"
    memo_rows = "\n".join('  Note(instance: "%s", text: copy.%s)' % (k, k) for k in memo_keys)

    src = card.get("source", {})
    quote_src = "%s · %s · 消息原文" % (clean(src.get("room", ""), 12), clean(src.get("at", ""), 20))
    ad = adapter_for(p["intent_type"])

    return CARD_TMPL.substitute(
        version=version, generated_at=generated_at,
        intent_type=p["intent_type"], intent_conf="%.2f" % p["intent_conf"],
        adapter_note="INTENT_ADAPTERS['%s'] -> %s" % (p["intent_type"], ad["ask"]),
        memory_note=memory_note, review_note=review_note,
        source_desc=quote_src,
        eyebrow="拾意 · 生成卡 · 第一次识别",
        heading=p["heading"],
        quote=p.get("quote_disp") or clean(card.get("quote", ""), 40),
        quote_src=quote_src,
        field_copies=field_copies,
        open_line=clean(p["open_line"], 60),
        memo_copies=memo_copies.rstrip("\n"),
        components=COMPONENTS.rstrip("\n"),
        field_rows=field_rows,
        memo_rows=memo_rows,
    )


def render_data(p):
    field_keys = list(p["lines"])
    memo_keys = ["memo_%d" % i for i in range(len(p["memo_lines"]))]
    return {
        "$kit": {
            "theme": "light",
            "note": ("Generated layout. Artboard 412x892 (card-host inner_size). The quote band "
                     "grows with the source line count; rows below are pushed down accordingly. "
                     "A geometric self-review checks bounds / action-band / text-fit before write."),
            "placements": placements(field_keys, memo_keys, quote_rows(p.get("quote_disp", ""))),
        },
        "read": {"is_ok": False, "error": "assistant has not answered yet"},
    }


def render_manifest(app_id, name, version):
    return {"agent": None,
            "capabilities": ["octos.session.open", "octos.turn.start"],
            "compute": {"instruction_budget": None, "memory_bytes": None},
            "id": app_id, "name": name, "network": {"hosts": []}, "schema": 1,
            "storage": {"max_bytes": None}, "version": version}


def render_bindings(card, p):
    """连"问设备助手什么"都是生成的：按意图换措辞（走适配器）。"""
    ad = adapter_for(p["intent_type"])
    prompt = ("你是拾意（Pickup）的设备助手。用户发来一句话：「%s」。%s，还缺哪两样信息？"
              "只回一行，不超过 28 个字，直接给答案，不要解释，不要使用任何工具。"
              % (clean(card.get("quote", ""), 40), ad["ask"]))
    return {"on_open": [
        {"service": "octos.session.open", "target": "session"},
        {"service": "octos.turn.start", "target": "read", "args": {"text": prompt}},
    ]}


def render_listing(app_id, version, n_screens):
    return {"schema": 1, "subtitle": "由意图生成的一张卡",
            "description": ("生成器把一条聊天消息识别成时间/地点/类型，现场组装出这张 L0 卡："
                            "渲染哪些行、每行说什么、摆在什么位置，都由识别结果决定；"
                            "排完还会自评一遍再出。"),
            "category": "utilities", "keywords": ["assistant", "intent", "generated", "l0"],
            "screenshots": [], "icon": "assets/icon.svg", "platforms": ["windows"],
            "publisher": {"name": "sansanyixyz331",
                          "support": "https://github.com/sansanyixyz331/shiyi",
                          "privacy_policy_url": "https://github.com/sansanyixyz331/shiyi/blob/main/PRIVACY.md"},
            "release_notes": "%s — %d generated screen(s)." % (version, n_screens),
            "age_rating": "all", "license": "Apache-2.0"}


# ==================================================================== 生成 + 自评闭环

def build_with_review(text, room, prefs, version, app_id, name, max_rounds=3, tighten=0):
    """能力④ 落地：生成一版 -> 自评 -> 有问题就改 -> 直到干净或用尽轮次。

    tighten>0：先按视觉/几何反馈收紧一版（更短的文案、更少的原文行）。
    """
    card = build_card(text, room=room, prefs=prefs)
    p = plan(card)
    if tighten:
        p["open_line"] = clean(p["open_line"], max(16, len(p["open_line"]) - 14 * tighten))
        qd = p.get("quote_disp", "")
        rows = quote_rows(qd)
        if rows > 1:
            p["quote_disp"] = clean(qd, max(QUOTE_PER_LINE, (rows - tighten) * QUOTE_PER_LINE))
    review = {"rounds": [], "converged": False}
    review_note = "clean on first pass"
    for r in range(max_rounds):
        P = placements(p["lines"], ["memo_%d" % i for i in range(len(p["memo_lines"]))],
                       quote_rows(p.get("quote_disp", "")))
        issues = selfcheck(P, texts_of(p, card))
        review["rounds"].append({"round": r + 1,
                                 "issues": [i["kind"] for i in issues],
                                 "detail": issues})
        if not issues:
            review["converged"] = True
            review_note = "clean on pass %d" % (r + 1)
            break
        p, fixes = revise(p, issues, r + 1)
        review["rounds"][-1]["fixes"] = fixes
        review_note = "revised %d issue(s) over %d pass(es)" % (
            sum(len(x["issues"]) for x in review["rounds"]), r + 1)
        if not fixes:
            review["rounds"][-1]["note"] = "no automatic fix available; stopping"
            break
    P = placements(p["lines"], ["memo_%d" % i for i in range(len(p["memo_lines"]))],
                   quote_rows(p.get("quote_disp", "")))
    return card, p, P, review, review_note


def write_bundle(out_dir, card, p, P, review, review_note, memory_note, app_id, name, version):
    b = os.path.join(out_dir, "bundle")
    os.makedirs(b, exist_ok=True)
    generated_at = dt.datetime.now().isoformat(timespec="seconds")

    open(os.path.join(b, "page.card"), "w", encoding="utf-8").write(
        render_card(p, card, version, generated_at, review_note, memory_note))
    for fn, obj in (("page.data.json", render_data(p)),
                    ("manifest.json", render_manifest(app_id, name, version)),
                    ("listing.json", render_listing(app_id, version, 1)),
                    ("bindings.json", render_bindings(card, p))):
        with open(os.path.join(b, fn), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=2, sort_keys=(fn == "manifest.json"))
            fh.write("\n")

    for src, nm in ((SHARED_KIT, "kit"), (SHARED_ASSETS, "assets")):
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(b, nm), dirs_exist_ok=True)

    # 自评过程单独落一份 —— 这就是复赛「复现证据」里的"看结果并改进"记录
    with open(os.path.join(out_dir, "review.json"), "w", encoding="utf-8") as fh:
        json.dump(review, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return b


def lint(bundle_dir):
    r = subprocess.run([sys.executable, LINT, bundle_dir],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def generate_one(text, room, out_dir, app_id, name, version, prefs, memory_note, tighten=0):
    card, p, P, review, review_note = build_with_review(text, room, prefs, version, app_id, name,
                                                       tighten=tighten)
    b = write_bundle(out_dir, card, p, P, review, review_note, memory_note, app_id, name, version)
    code, log = lint(b)
    n_issues = sum(len(x["issues"]) for x in review["rounds"])
    print("[%s] %-24s rows=%d memo=%d  review:%s  lint:%s"
          % ("PASS" if code == 0 else "FAIL", text[:22], len(p["lines"]), len(p["memo_lines"]),
             ("%d issue(s) fixed" % n_issues) if n_issues else "clean-first-pass",
             "ok" if code == 0 else "ERR"))
    return code, review


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text")
    ap.add_argument("--room", default="家庭群")
    ap.add_argument("--samples", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--id", default="shiyi-gen")
    ap.add_argument("--name", default="拾意 · 生成卡")
    ap.add_argument("--version", default="0.2.0")
    ap.add_argument("--memory", help="memory.json 路径；缺省用仓库 .local-state/memory.json")
    args = ap.parse_args()

    if not os.path.isdir(SHARED_KIT):
        sys.exit("找不到共享 kit：%s" % SHARED_KIT)

    # 能力② 长期记忆层：读真文件（不是写死的 DEFAULT_PREFS）
    if MemoryStore is None:
        prefs, memory_note = None, "builtin (memory_store unavailable)"
    else:
        st = MemoryStore(args.memory) if args.memory else MemoryStore()
        st.ensure()
        prefs = st.prefs()
        memory_note = "%s (prefs=%s)" % (st.rel_path, ",".join(sorted(k for k, v in prefs.items() if v)))

    os.makedirs(args.out, exist_ok=True)
    codes, reviews = [], []
    if args.samples:
        from intent_card import SAMPLES
        for i, (text, room) in enumerate(SAMPLES, 1):
            c, rv = generate_one(text, room, os.path.join(args.out, "%02d" % i),
                                 args.id, args.name, args.version, prefs, memory_note)
            codes.append(c); reviews.append(rv)
    elif args.text:
        c, rv = generate_one(args.text, args.room, os.path.join(args.out, "card"),
                             args.id, args.name, args.version, prefs, memory_note)
        codes.append(c); reviews.append(rv)
    else:
        ap.error("给 --text 或 --samples")

    bad = sum(1 for c in codes if c != 0)
    fixed = sum(sum(len(x["issues"]) for x in rv["rounds"]) for rv in reviews)
    print("\n生成 %d 张 | lint 通过 %d 失败 %d | 自评累计发现并修订 %d 处" %
          (len(codes), len(codes) - bad, bad, fixed))
    print("记忆来源：%s" % memory_note)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
