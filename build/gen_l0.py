#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拾意 · L0 卡生成器 —— 意图 -> 一张能过门禁的 L0 卡 bundle。

这不是"填模板"。识别引擎 (src/intent_card.py) 先读一条消息，得出
时间 / 地点 / 类型 / 记忆命中 / 待问项；生成器据此**决定渲染哪些行、
每行说什么、各自摆在什么位置**，再产出：

    page.card        随意图变化（copy 的值、渲染的行、y 坐标都不同）
    page.data.json   随渲染的节点变化（$kit.placements 跟着行数排）
    manifest.json    capabilities = 本卡真正用到的服务
    listing.json     商店元数据
    kit/ assets/     共享（从主 bundle 拷，含子集字体与图标）

然后它自己跑一遍 tools/l0_bindings_lint.py，不过关就非零退出。

为什么是"生成"而不是"手写"：官方文档教的就是不要手写 L0；这里让
一条消息走完 识别 -> 组卡 -> 排版 -> 产包 -> 自检，人只看结果。

用法:
    python build/gen_l0.py --text "下周三我得去趟深圳" --room 家庭群 --out build/_gen/trip
    python build/gen_l0.py --samples --out build/_gen         # 自带样例批量生成
    python build/gen_l0.py --text "..." --out DIR --version 0.1.0

不改任何既有文件；只往 --out 写。bundle/ 与 tag 一字节不动。
"""

import argparse
import datetime as dt
import json
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
from intent_card import build_card  # noqa: E402

WD = ["一", "二", "三", "四", "五", "六", "日"]
TYPE_ZH = {
    "trip": "出行安排", "meeting": "会面", "errand": "跑腿代办",
    "purchase": "采购", "reminder": "提醒", "unknown": "待确认",
}
MEMO_ZH = {
    "excluded_flight": "从本机记忆里读到：你不坐飞机。",
    "filtered_to_rail": "所以往下只给你高铁方案。",
    "flagged_schedule_conflict": "注意：这天下午你通常不排事，可能冲突。",
}


# ------------------------------------------------------------------ 文本

def clean(s, limit=64):
    """把任意原文洗成能放进 L0 copy 双引号里的单行文本。

    L0 的 copy 值用双引号括起、且 `{}` 是语法字符 —— 原文里的引号/花括号
    会破坏解析。这里是"别搞错"的第一道闸。
    """
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


# ------------------------------------------------------------------ 语义 -> 行

def plan(card):
    """把识别结果摊成"要渲染的行"和"每行的文案"。这是生成的核心。"""
    f = card["fields"]
    when, where, intent = f["when"], f["where"], f["intent"]

    lines = []          # [(key, component, text)]
    copies = {}         # key -> 文案

    # 时间：能定到具体日期才成行；只有时刻 -> 低置信行（交人确认）
    if when.get("resolved"):
        txt = "时间 · %s · 出自原文" % fmt_when(when["resolved"])
        if when.get("confidence", 0) < 0.7:
            txt = "时间 · %s · 低置信，待你确认" % fmt_when(when["resolved"])
        copies["when"] = txt
        lines.append(("when", "row"))
    elif when.get("clock"):
        copies["when"] = "时间 · 只有「%s」，没定哪天 · 待你确认" % clean(when["clock"], 16)
        lines.append(("when", "row"))

    # 地点：白名单命中才成行；认不准的写进追问，不猜
    if where.get("normalized"):
        copies["where"] = "地点 · %s · 出自原文" % clean(where["normalized"], 24)
        lines.append(("where", "row"))

    # 类型：总是有（unknown 也如实写）
    tz = TYPE_ZH.get(intent.get("type"), "待确认")
    conf = intent.get("confidence", 0)
    copies["kind"] = "类型 · %s · %s" % (tz, "识别所得" if conf >= 0.5 else "说不准，待你确认")
    lines.append(("kind", "row"))

    # 追问行：识别引擎知道"哪两样还缺"；没有要问的就如实说齐了
    qs = [q["ask"] for q in card.get("questions", [])]
    if qs:
        open_line = "还没定：" + "；".join(clean(q, 30) for q in qs[:2])
    else:
        open_line = "该定的都定了，没有要问的。"

    # 记忆行：命中长期偏好才出，并说明"所以接下来会怎样"
    memo_lines = []
    effs = [e.get("effect") for e in card.get("memory", {}).get("effects", [])]
    seen = set()
    for e in effs:
        if e in MEMO_ZH and e not in seen:
            seen.add(e)
            memo_lines.append(MEMO_ZH[e])
    return {
        "lines": lines,
        "copies": copies,
        "open_line": open_line,
        "memo_lines": memo_lines,
        "intent_type": intent.get("type", "unknown"),
        "intent_conf": conf,
    }


# ------------------------------------------------------------------ 布局

def placements(field_keys, memo_keys):
    """由"渲染了哪些行"算出每个节点的 box。行数变了，y 跟着排 —— 不重叠。"""
    P = {}

    def put(name, comp, x, y, w, h):
        P[name] = {"component": comp, "layout": {"x": x, "y": y, "w": w, "h": h}}

    put("page", "page", 0, 0, 412, 892)
    put("eyebrow", "eyebrow", 24, 36, 364, 16)
    put("heading", "heading", 24, 58, 364, 62)
    put("quote_band", "band", 24, 140, 364, 110)
    put("quote", "quote", 44, 164, 324, 32)
    put("quote_src", "source", 44, 212, 324, 16)
    put("rule_1", "hairline", 24, 274, 364, 1)

    y = 292
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

    # 动作带固定在底部：一屏、一问，答在拇指够得到的地方。
    put("action_fix", "action", 24, 740, 364, 46)
    put("action_fix_bg", "action_ghost", 24, 740, 364, 46)
    put("action_fix_ctl", "action_control", 24, 740, 364, 46)
    put("action_fix_lbl", "ghost_label", 24, 753, 364, 20)
    put("action_yes", "action", 24, 800, 364, 54)
    put("action_yes_bg", "action_fill", 24, 800, 364, 54)
    put("action_yes_ctl", "action_control", 24, 800, 364, 54)
    put("action_yes_lbl", "action_label", 24, 816, 364, 22)
    return P


# ------------------------------------------------------------------ 渲染

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
# source     : ${source_desc}
#
# 这张卡不是手写的：它由「意图识别引擎」(src/intent_card.py) 的输出组装而成 ——
# 同一个引擎，不同的一条消息，长出来的行、文案和位置都不一样。
# 纪律与手写版一致：每条事实都带来源；拿不准的写成「还没定」，不猜。
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


def render_card(p, card, version, generated_at):
    field_copies = "\n".join(
        'copy f_%s   { class: vocabulary, en: "%s", zh: "%s" }' % (k, p["copies"][k], p["copies"][k])
        for k, _ in p["lines"])
    field_rows = "\n".join(
        '  Line(instance: "row_%s", text: copy.f_%s)' % (k, k)
        for k, _ in p["lines"])

    memo_keys = ["memo_%d" % i for i in range(len(p["memo_lines"]))]
    memo_copies = "\n".join(
        'copy %s { class: vocabulary, en: "%s", zh: "%s" }' % (k, clean(t, 48), clean(t, 48))
        for k, t in zip(memo_keys, p["memo_lines"]))
    if memo_copies:
        memo_copies += "\n"
    memo_rows = "\n".join(
        '  Note(instance: "%s", text: copy.%s)' % (k, k) for k in memo_keys)

    quote = clean(card.get("quote", ""), 40)
    src = card.get("source", {})
    quote_src = "%s · %s · 消息原文" % (clean(src.get("room", ""), 12), clean(src.get("at", ""), 20))

    return CARD_TMPL.substitute(
        version=version,
        generated_at=generated_at,
        intent_type=p["intent_type"],
        intent_conf="%.2f" % p["intent_conf"],
        source_desc=quote_src,
        eyebrow="拾意 · 生成卡 · 第一次识别",
        heading="从你发过的话里，读出了一个安排",
        quote=quote,
        quote_src=quote_src,
        field_copies=field_copies,
        open_line=clean(p["open_line"], 60),
        memo_copies=memo_copies.rstrip("\n"),
        components=COMPONENTS.rstrip("\n"),
        field_rows=field_rows,
        memo_rows=memo_rows,
    )


def render_data(p):
    field_keys = [k for k, _ in p["lines"]]
    memo_keys = ["memo_%d" % i for i in range(len(p["memo_lines"]))]
    return {
        "$kit": {
            "theme": "light",
            "note": ("Generated layout. Artboard 412x892 (card-host inner_size). "
                     "Rows are placed top-down from the fields the reading produced; "
                     "the action band is pinned at the bottom."),
            "placements": placements(field_keys, memo_keys),
        },
        "read": {"is_ok": False, "error": "assistant has not answered yet"},
    }


def render_manifest(app_id, name, version):
    return {
        "agent": None,
        "capabilities": ["octos.session.open", "octos.turn.start"],
        "compute": {"instruction_budget": None, "memory_bytes": None},
        "id": app_id,
        "name": name,
        "network": {"hosts": []},
        "schema": 1,
        "storage": {"max_bytes": None},
        "version": version,
    }


PROMPT_LEAD = {
    "trip": "要把它排成一次行程",
    "meeting": "要把它定成一次会面",
    "errand": "要把它办掉",
    "purchase": "要把它安排上",
    "reminder": "要把它记成一条提醒",
}


def render_bindings(card, p):
    """连"问设备助手什么"都是生成出来的：按意图换措辞。"""
    lead = PROMPT_LEAD.get(p["intent_type"], "要把它落到实处")
    prompt = ("你是拾意（Pickup）的设备助手。用户发来一句话：「%s」。%s，还缺哪两样信息？"
              "只回一行，不超过 28 个字，直接给答案，不要解释，不要使用任何工具。"
              % (clean(card.get("quote", ""), 40), lead))
    return {
        "on_open": [
            {"service": "octos.session.open", "target": "session"},
            {"service": "octos.turn.start", "target": "read", "args": {"text": prompt}},
        ]
    }


def render_listing(app_id, version, n_screens):
    return {
        "schema": 1,
        "subtitle": "由意图生成的一张卡",
        "description": ("生成器把一条聊天消息识别成时间/地点/类型，现场组装出这张 L0 卡："
                        "渲染哪些行、每行说什么、摆在什么位置，都由识别结果决定。"),
        "category": "utilities",
        "keywords": ["assistant", "intent", "generated", "l0"],
        "screenshots": [],
        "icon": "assets/icon.svg",
        "platforms": ["windows"],
        "publisher": {
            "name": "sansanyixyz331",
            "support": "https://github.com/sansanyixyz331/shiyi",
            "privacy_policy_url": "https://github.com/sansanyixyz331/shiyi/blob/main/PRIVACY.md",
        },
        "release_notes": "%s — %d generated screen(s)." % (version, n_screens),
        "age_rating": "all",
        "license": "Apache-2.0",
    }


# ------------------------------------------------------------------ 产出

def write_bundle(out_dir, card, p, app_id, name, version):
    b = os.path.join(out_dir, "bundle")
    os.makedirs(b, exist_ok=True)
    generated_at = dt.datetime.now().isoformat(timespec="seconds")

    with open(os.path.join(b, "page.card"), "w", encoding="utf-8") as fh:
        fh.write(render_card(p, card, version, generated_at))
    with open(os.path.join(b, "page.data.json"), "w", encoding="utf-8") as fh:
        json.dump(render_data(p), fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(os.path.join(b, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(render_manifest(app_id, name, version), fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(b, "listing.json"), "w", encoding="utf-8") as fh:
        json.dump(render_listing(app_id, version, 1), fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(os.path.join(b, "bindings.json"), "w", encoding="utf-8") as fh:
        json.dump(render_bindings(card, p), fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    for src, name2 in ((SHARED_KIT, "kit"), (SHARED_ASSETS, "assets")):
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(b, name2), dirs_exist_ok=True)
    return b


def lint(bundle_dir):
    r = subprocess.run([sys.executable, LINT, bundle_dir],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def generate_one(text, room, out_dir, app_id, name, version, quiet=False):
    card = build_card(text, room=room)
    p = plan(card)
    b = write_bundle(out_dir, card, p, app_id, name, version)
    code, log = lint(b)
    tag = "PASS" if code == 0 else "FAIL"
    print("[%s] %-28s -> %s" % (tag, text[:26], b))
    if code != 0 or not quiet:
        print("\n".join("      " + ln for ln in log.strip().splitlines()))
    return code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", help="一条消息")
    ap.add_argument("--room", default="家庭群")
    ap.add_argument("--samples", action="store_true", help="用 intent_card 自带样例批量生成")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--id", default="shiyi-gen")
    ap.add_argument("--name", default="拾意 · 生成卡")
    ap.add_argument("--version", default="0.1.0")
    args = ap.parse_args()

    if not os.path.isdir(SHARED_KIT):
        sys.exit("找不到共享 kit：%s" % SHARED_KIT)

    os.makedirs(args.out, exist_ok=True)
    codes = []
    if args.samples:
        from intent_card import SAMPLES
        for i, (text, room) in enumerate(SAMPLES, 1):
            out = os.path.join(args.out, "%02d" % i)
            codes.append(generate_one(text, room, out, args.id, args.name, args.version))
    elif args.text:
        codes.append(generate_one(args.text, args.room, os.path.join(args.out, "card"),
                                  args.id, args.name, args.version))
    else:
        ap.error("给 --text 或 --samples")

    bad = sum(1 for c in codes if c != 0)
    print("\n生成 %d 张，lint 通过 %d，失败 %d" % (len(codes), len(codes) - bad, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
