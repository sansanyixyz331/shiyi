#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拾意 · 五屏生成器 —— 把一条消息，生成**整套**五屏卡。

README 的单屏版（gen_l0.py）只造第一屏；这里造全五屏：

  01-read  第一次识别（说了什么、出自哪里、还缺什么）
  02-ask   追问那两个缺口（选项按缺口类型生成）
  03-plan  给一版方案（按意图；样例并标注是样例）
  04-memo  旧记忆 -> 新记忆（旧值取自真记忆文件）
  05-done  回执（三行，按真实发生的事分列）

五屏共用一套**垂直流布局引擎**：块从上往下排，动作带钉在底部。
每屏只是"有哪些块"不同 —— 加/改一屏不动引擎。

    python build/gen_screens.py --text "下周三我得去趟深圳" --room 家庭群 --out build/_screens/trip
    python build/gen_screens.py --samples --out build/_screens

产出 <out>/cards/<screen>/{page.card,page.data.json,service-actions.json}
            + <out>/bundle/  （= read 屏 + kit/assets，可直接过门禁）

只往 --out 写。bundle/（冻结提交物）与 tag 不动。
"""

import argparse
import datetime as dt
import json
import os
import shutil
import sys

BUILD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BUILD)
import gen_l0  # noqa: E402

clean = gen_l0.clean
fmt_when = gen_l0.fmt_when
TYPE_ZH = gen_l0.TYPE_ZH

PAGE_W, PAGE_H = 412, 892
MARGIN, CONTENT_W = 24, 364
ACTION_A_TOP, ACTION_B_TOP = 740, 800
BLOCK_GAP = 14
ROW_H, NOTE_H = 22, 20
BAND_PAD = 12

SCREENS = ["shiyi-01-read", "shiyi-02-ask", "shiyi-03-plan", "shiyi-04-memo", "shiyi-05-done"]

COMPONENTS = """# ── components ───────────────────────────────────────────────────────────────
component Page(instance: text) {
  view Kit(component: "page", instance: instance) { slot }
}
component Slab(instance: text) {
  view Kit(component: "band", instance: instance) { slot }
}
component SlabSoft(instance: text) {
  view Kit(component: "band_soft", instance: instance) { slot }
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

COMP_TO_ZH = {"line": "Line", "note": "Note", "quote": "Quote", "source": "Source"}
KIT_OF = {"line": "row", "note": "note", "quote": "quote", "source": "source", "hairline": "hairline"}


# ==================================================================== 布局引擎

def block_h(blk):
    if blk.get("comp") in ("band", "band_soft"):
        inner = sum(ROW_H if r["comp"] == "line" else NOTE_H for r in blk["rows"])
        return BAND_PAD + inner + BAND_PAD + max(0, len(blk["rows"]) - 1) * 4
    return sum(ROW_H if r["comp"] == "line" else NOTE_H for r in blk["rows"])


def layout(spec):
    """垂直流：块从上往下排；动作带钉底部。返回 placements。"""
    P = {}

    def put(name, comp, x, y, w, h):
        P[name] = {"component": comp, "layout": {"x": x, "y": y, "w": w, "h": h}}

    put("page", "page", 0, 0, PAGE_W, PAGE_H)
    put("eyebrow", "eyebrow", MARGIN, 36, CONTENT_W, 16)
    put("heading", "heading", MARGIN, 58, CONTENT_W, 62)

    y = 136
    for b in spec["blocks"]:
        h = block_h(b)
        if b.get("comp") in ("band", "band_soft"):
            put(b["id"], b["comp"], MARGIN, y, CONTENT_W, h)
            yy = y + BAND_PAD
            for r in b["rows"]:
                put(r["id"], KIT_OF[r["comp"]], MARGIN + 20 if r["comp"] == "quote" else MARGIN + (20 if b.get("comp") else 0),
                    yy, CONTENT_W - (40 if r["comp"] == "quote" else 20), ROW_H if r["comp"] == "line" else NOTE_H)
                yy += (ROW_H if r["comp"] == "line" else NOTE_H) + 4
        else:
            yy = y
            for r in b["rows"]:
                put(r["id"], KIT_OF[r["comp"]], MARGIN, yy, CONTENT_W,
                    ROW_H if r["comp"] == "line" else NOTE_H)
                yy += (ROW_H if r["comp"] == "line" else NOTE_H)
        y += h + BLOCK_GAP

    # 动作带：两个按钮（上 ghost、下 fill），与 READ 版同一位置
    a, b2 = spec["actions"]
    put(a["id"], "action", MARGIN, ACTION_A_TOP, CONTENT_W, 46)
    put(a["id"] + "_bg", "action_ghost", MARGIN, ACTION_A_TOP, CONTENT_W, 46)
    put(a["id"] + "_ctl", "action_control", MARGIN, ACTION_A_TOP, CONTENT_W, 46)
    put(a["id"] + "_lbl", "ghost_label", MARGIN, ACTION_A_TOP + 13, CONTENT_W, 20)
    put(b2["id"], "action", MARGIN, ACTION_B_TOP, CONTENT_W, 54)
    put(b2["id"] + "_bg", "action_fill", MARGIN, ACTION_B_TOP, CONTENT_W, 54)
    put(b2["id"] + "_ctl", "action_control", MARGIN, ACTION_B_TOP, CONTENT_W, 54)
    put(b2["id"] + "_lbl", "action_label", MARGIN, ACTION_B_TOP + 16, CONTENT_W, 22)
    return P


def render_card(spec, version):
    copies, view_lines = [], []
    for b in spec["blocks"]:
        for r in b["rows"]:
            copies.append('copy %s { class: %s, en: "%s", zh: "%s" }'
                          % (r["id"], "user-copy" if r["comp"] == "quote" else "vocabulary",
                             clean(r["text"], 60), clean(r["text"], 60)))
        if b.get("comp") in ("band", "band_soft"):
            wrap = "SlabSoft" if b["comp"] == "band_soft" else "Slab"
            inner = "\n".join('    %s(instance: "%s", text: copy.%s)'
                              % (COMP_TO_ZH[r["comp"]], r["id"], r["id"]) for r in b["rows"])
            view_lines.append('  %s(instance: "%s") {\n%s\n  }' % (wrap, b["id"], inner))
        else:
            for r in b["rows"]:
                view_lines.append('  %s(instance: "%s", text: copy.%s)'
                                  % (COMP_TO_ZH[r["comp"]], r["id"], r["id"]))
    for a in spec["actions"]:
        copies.append('copy %s_lblcopy { class: vocabulary, en: "%s", zh: "%s" }'
                      % (a["id"], clean(a["label"], 30), clean(a["label"], 30)))

    a, b2 = spec["actions"]
    act_a_style = ("ActionGhost", "GhostLabel") if a["style"] == "ghost" else ("ActionFill", "ActionLabel")
    act_b_style = ("ActionGhost", "GhostLabel") if b2["style"] == "ghost" else ("ActionFill", "ActionLabel")

    def act(a, sty):
        tail, lbl = sty
        return ('  Action(instance: "%s") {\n    %s(instance: "%s_bg") {\n\n    }\n'
                '    ActionControl(instance: "%s_ctl", enabled: act_enabled)\n'
                '    %s(instance: "%s_lbl", text: copy.%s_lblcopy)\n  }'
                % (a["id"], tail, a["id"], a["id"], lbl, a["id"], a["id"]))

    return """# ledger %s@%s
# level: L0
# profile: ui/l0
# model: shiyi
#
# 拾意 · Pickup — GENERATED screen (%s).
# generator : build/gen_screens.py
# generated : %s
#
# 这一屏由识别结果生成：块是哪些、每块说什么、选项是什么，都随那条消息而变。
# 纪律与手写版一致：事实带来源，拿不准的写「还没定」，样例明确标"样例"。
theme light

state act_enabled { shape: bool, initial: true }

copy eyebrow { class: vocabulary, en: "%s", zh: "%s" }
copy heading { class: vocabulary, en: "%s", zh: "%s" }

%s

%s
# ── view ─────────────────────────────────────────────────────────────────────
view root Page(instance: "page") {
  Eyebrow(instance: "eyebrow", text: copy.eyebrow)
  Heading(instance: "heading", text: copy.heading)

%s

%s
}
""" % (spec["screen"], version, spec["role"], dt.datetime.now().isoformat(timespec="seconds"),
       clean(spec["eyebrow"], 40), clean(spec["eyebrow"], 40),
       clean(spec["heading"], 60), clean(spec["heading"], 60),
       "\n".join(copies), COMPONENTS.rstrip("\n"), "\n\n".join(view_lines),
       "\n".join(act(a, act_a_style) for a in [a]) + "\n" + act(b2, act_b_style))


def render_data(spec):
    return {"$kit": {"theme": "light",
                     "note": ("Generated vertical flow; the action band is pinned at the bottom. "
                              "Blocks are placed top-down in the order the screen spec lists them."),
                     "placements": layout(spec)}}


def render_actions(spec):
    return {"card": spec["screen"], "source": spec["source"],
            "note": ("A card here carries no tap events (the host's kit_pack passes only declared "
                     "props/layout/style). Each control's meaning is declared beside the card; the "
                     "Agent reads it to decide the next screen."),
            "controls": {a["id"]: {"event": a["event"], "enabled": True} for a in spec["actions"]}}


# ==================================================================== 五个屏的规格

def _adapter(kind):
    return gen_l0.adapter_for(kind)


def spec_read(card, p):
    f = card["fields"]
    blocks = [{"id": "quote_band", "comp": "band",
               "rows": [{"id": "quote", "comp": "quote", "text": p["quote_disp"]},
                        {"id": "qsrc", "comp": "source",
                         "text": "%s · %s · 消息原文" % (clean(card["source"].get("room", ""), 12),
                                                        clean(card["source"].get("at", ""), 20))}]}]
    rows = []
    for k in p["lines"]:
        rows.append({"id": "row_" + k, "comp": "line", "text": p["copies"][k]})
    rows.append({"id": "row_open", "comp": "note", "text": p["open_line"]})
    rows.append({"id": "row_src", "comp": "note",
                 "text": "识别来源 · 本地规则（设备助手可用时另加一行）"})
    blocks.append({"id": "fields", "comp": None, "rows": rows})
    if p["memo_lines"]:
        blocks.append({"id": "memo", "comp": None,
                       "rows": [{"id": "memo_%d" % i, "comp": "note", "text": t}
                                for i, t in enumerate(p["memo_lines"])]})
    return {"screen": "shiyi-01-read", "role": "read", "source": "intent.read",
            "eyebrow": "拾意 · 第一步 · 识别", "heading": p["heading"], "blocks": blocks,
            "actions": [{"id": "action_fix", "label": "不对，改一下", "style": "ghost", "event": "intent.reject"},
                        {"id": "action_yes", "label": "对，就是这件事", "style": "fill", "event": "intent.confirm"}]}


def _ask_options(q):
    """按缺口的类型，给两个候选。候选来自规则/记忆，不是凭空。"""
    fld = q.get("field")
    if fld == "when":
        return ["今天稍晚", "明天再说"]
    if fld == "where":
        return ["从家里出发", "从公司出发"]
    if fld == "reference":
        return ["就是上一次说的那件", "不是，是另一件"]
    return ["按常规来", "这次特殊"]


def spec_ask(card, p):
    qs = card.get("questions", [])
    q1 = qs[0] if qs else {"field": "when", "ask": "这事安排在哪天？"}
    q2 = qs[1] if len(qs) > 1 else {"field": "where", "ask": "从哪儿出发？"}
    o1, o2 = _ask_options(q1), _ask_options(q2)
    blocks = [
        {"id": "hint", "comp": None, "rows": [{"id": "hint", "comp": "note",
         "text": "能猜的我猜，猜不出的不装懂。就这两样。"}]},
        {"id": "q1_band", "comp": "band", "rows": [
            {"id": "q1_label", "comp": "line", "text": q1["ask"]},
            {"id": "q1_o1", "comp": "line", "text": o1[0]},
            {"id": "q1_o2", "comp": "line", "text": o1[1]}]},
        {"id": "q2_band", "comp": "band", "rows": [
            {"id": "q2_label", "comp": "line", "text": q2["ask"]},
            {"id": "q2_o1", "comp": "line", "text": o2[0]},
            {"id": "q2_o2", "comp": "line", "text": o2[1]}]},
    ]
    return {"screen": "shiyi-02-ask", "role": "ask", "source": "intent.ask",
            "eyebrow": "拾意 · 第二步 · 追问", "heading": "这件事还缺两样，只有你知道", "blocks": blocks,
            "actions": [{"id": "action_later", "label": "先放着，回头再说", "style": "ghost", "event": "ask.deferred"},
                        {"id": "action_go", "label": "就按这个查", "style": "fill", "event": "ask.settled"}]}


PLAN_SAMPLES = {
    "trip": [("样例班次 A · 08:12 开", "4小时12分 · 二等座余 6 · 推荐"),
             ("样例班次 B · 09:40 开", "4小时05分 · 二等座余 2"),
             ("样例班次 C · 14:20 开", "4小时30分 · 二等座充足")],
    "meeting": [("样例时段 · 上午 10:00", "30 分钟 · 常规会议室"),
                ("样例时段 · 下午 14:00", "30 分钟 · 常规会议室"),
                ("样例时段 · 下午 16:30", "30 分钟 · 常规会议室")],
    "errand": [("样例时段 · 上午", "顺路，不绕"),
               ("样例时段 · 午后", "稍绕一点"),
               ("样例时段 · 傍晚", "人不挤")],
}


def spec_plan(card, p):
    kind = p["intent_type"]
    picks = PLAN_SAMPLES.get(kind, PLAN_SAMPLES["meeting"])
    rows = [{"id": "memo", "comp": "note", "text": "记得：你坐高铁，不坐飞机。所以只按这个出。"}] \
        if p["memo_lines"] else [{"id": "memo", "comp": "note", "text": "按你这次的意图出一版。"}]
    blocks = [{"id": "top", "comp": None, "rows": rows}]
    for i, (main, sub) in enumerate(picks, 1):
        blocks.append({"id": "pick%d_band" % i, "comp": "band_soft" if i == 1 else "band",
                       "rows": [{"id": "pick%d" % i, "comp": "line", "text": main},
                                {"id": "pick%d_sub" % i, "comp": "note", "text": sub}]})
    blocks.append({"id": "foot", "comp": None, "rows": [
        {"id": "foot", "comp": "note",
         "text": "以上为样例，未查询任何外部服务；确认后才去查真实班次。"}]})
    return {"screen": "shiyi-03-plan", "role": "plan", "source": "intent.plan",
            "eyebrow": "拾意 · 第三步 · 方案", "heading": "按你的老规矩，先出一版", "blocks": blocks,
            "actions": [{"id": "action_other", "label": "换一版看看", "style": "ghost", "event": "plan.other"},
                        {"id": "action_take", "label": "就要第一版", "style": "fill", "event": "plan.take"}]}


def spec_memo(card, p, places=None):
    where = card["fields"]["where"].get("normalized") or "（未指明）"
    old = None
    if places and where in places:
        v = places[where]
        old = "去%s，默认%s，从%s出发。" % (where, v.get("default_depart", "?"), v.get("from", "?"))
    old_txt = old or "（这个地点还没记过；记下后，下次你说%s会自动按它来）" % where
    new_txt = "去%s，默认%s%s。" % (where, "早班" if p["memo_lines"] else "按这次说的",
                                   "，从家里出发" if p["memo_lines"] else "")
    blocks = [
        {"id": "old_band", "comp": "band", "rows": [
            {"id": "old_tag", "comp": "note", "text": "原来记着的"},
            {"id": "old_val", "comp": "line", "text": old_txt}]},
        {"id": "new_band", "comp": "band_soft", "rows": [
            {"id": "new_tag", "comp": "note", "text": "这次加上"},
            {"id": "new_val", "comp": "line", "text": new_txt}]},
        {"id": "foot", "comp": None, "rows": [{"id": "foot", "comp": "note",
         "text": "旧值来自本机记忆文件；想改随时说。"}]},
    ]
    return {"screen": "shiyi-04-memo", "role": "memo", "source": "intent.memo",
            "eyebrow": "拾意 · 第四步 · 记忆", "heading": "这件事，往后按这样办", "blocks": blocks,
            "actions": [{"id": "action_skip", "label": "这次别记", "style": "ghost", "event": "memo.skip"},
                        {"id": "action_keep", "label": "记下", "style": "fill", "event": "memo.keep"}]}


def spec_done(card, p):
    where = card["fields"]["where"].get("normalized") or "（未指明）"
    blocks = [{"id": "receipt_band", "comp": "band", "rows": [
        {"id": "r1", "comp": "line", "text": "写了记忆 · 去%s的默认走法（点“记下”才真写）" % where},
        {"id": "r2", "comp": "line", "text": "行程没动 · 方案里的班次是样例"},
        {"id": "r3", "comp": "line", "text": "日历与提醒没动 · 没碰系统"}]},
        {"id": "foot", "comp": None, "rows": [{"id": "foot", "comp": "note",
         "text": "只有你点过“记下”的那行真写进去了，其余一个字没动。"}]}]
    return {"screen": "shiyi-05-done", "role": "done", "source": "intent.done",
            "eyebrow": "拾意 · 第五步 · 完成", "heading": "记下了。别的没动，等你点头", "blocks": blocks,
            "actions": [{"id": "action_again", "label": "重开一条", "style": "ghost", "event": "app.restart"},
                        {"id": "action_open", "label": "看行程", "style": "fill", "event": "trip.open"}]}


# ==================================================================== 产出

def gen_all(text, room, prefs, places, version, out_dir):
    card = gen_l0.build_card(text, room=room, prefs=prefs)
    p = gen_l0.plan(card)
    specs = [spec_read(card, p), spec_ask(card, p), spec_plan(card, p),
             spec_memo(card, p, places), spec_done(card, p)]
    cards_dir = os.path.join(out_dir, "cards")
    for s in specs:
        d = os.path.join(cards_dir, s["screen"])
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "page.card"), "w", encoding="utf-8").write(render_card(s, version))
        with open(os.path.join(d, "page.data.json"), "w", encoding="utf-8") as fh:
            json.dump(render_data(s), fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        with open(os.path.join(d, "service-actions.json"), "w", encoding="utf-8") as fh:
            json.dump(render_actions(s), fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    # 顺带出一个 bundle（= read 屏 + kit/assets + 身份文件），可直接过门禁
    b = os.path.join(out_dir, "bundle")
    os.makedirs(b, exist_ok=True)
    shutil.copy2(os.path.join(cards_dir, "shiyi-01-read", "page.card"), os.path.join(b, "page.card"))
    shutil.copy2(os.path.join(cards_dir, "shiyi-01-read", "page.data.json"), os.path.join(b, "page.data.json"))
    for fn, obj in (("manifest.json", gen_l0.render_manifest("shiyi-gen", "拾意 · 生成卡", version)),
                    ("listing.json", gen_l0.render_listing("shiyi-gen", version, 5)),
                    ("bindings.json", gen_l0.render_bindings(card, p))):
        with open(os.path.join(b, fn), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=2, sort_keys=(fn == "manifest.json"))
            fh.write("\n")
    for src, nm in ((gen_l0.SHARED_KIT, "kit"), (gen_l0.SHARED_ASSETS, "assets")):
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(b, nm), dirs_exist_ok=True)
    return specs


def probe_all(out_dir, version, tag=""):
    """对每一屏：造一个 probe bundle -> 渲染 -> 视觉自评。返回结果表。"""
    import shot_bundle     # noqa: E402
    import visual_review   # noqa: E402
    results = []
    for s in SCREENS:
        src = os.path.join(out_dir, "cards", s)
        b = os.path.join(out_dir, "probe", tag + s, "bundle")
        if os.path.isdir(os.path.dirname(b)):
            shutil.rmtree(os.path.dirname(b))
        os.makedirs(b, exist_ok=True)
        for src_dir, nm in ((gen_l0.SHARED_KIT, "kit"), (gen_l0.SHARED_ASSETS, "assets")):
            if os.path.isdir(src_dir):
                shutil.copytree(src_dir, os.path.join(b, nm), dirs_exist_ok=True)
        listing = gen_l0.render_listing("shiyi-gen", version, 1)
        listing["screenshots"] = ["screenshots/01.png"]
        for fn, obj in (("manifest.json", gen_l0.render_manifest("shiyi-gen", "拾意 · 生成卡", version)),
                        ("listing.json", listing)):
            with open(os.path.join(b, fn), "w", encoding="utf-8") as fh:
                json.dump(obj, fh, ensure_ascii=False, indent=2, sort_keys=(fn == "manifest.json"))
                fh.write("\n")
        for fn in ("page.card", "page.data.json"):
            shutil.copy2(os.path.join(src, fn), os.path.join(b, fn))
        try:
            shot_bundle.shot(b)
            vr = visual_review.review_bundle(b)
            results.append((s, [i["kind"] for i in vr["issues"]], vr["debug"].get("n_blocks")))
        except Exception as e:  # noqa: BLE001
            results.append((s, ["render-error: %s" % e], None))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text")
    ap.add_argument("--room", default="家庭群")
    ap.add_argument("--samples", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--version", default="0.3.0")
    ap.add_argument("--verify", action="store_true", help="每屏造 probe bundle、渲染、视觉自评")
    ap.add_argument("--memory")
    args = ap.parse_args()

    if gen_l0.MemoryStore is None:
        prefs, places = None, {}
    else:
        st = gen_l0.MemoryStore(args.memory) if args.memory else gen_l0.MemoryStore()
        st.ensure()
        prefs, places = st.prefs(), st.places()

    os.makedirs(args.out, exist_ok=True)
    jobs = []
    if args.samples:
        from intent_card import SAMPLES  # noqa
        for i, (text, room) in enumerate(SAMPLES, 1):
            jobs.append((text, room, os.path.join(args.out, "%02d" % i)))
    elif args.text:
        jobs.append((args.text, args.room, args.out))
    else:
        ap.error("给 --text 或 --samples")

    for text, room, out in jobs:
        specs = gen_all(text, room, prefs, places, args.version, out)
        n = len(specs)
        okd = all(os.path.isfile(os.path.join(out, "cards", s["screen"], "page.card")) for s in specs)
        print("[%s] %-24s %d screens -> %s" % ("OK" if okd else "FAIL", text[:22], n, out))
        if args.verify:
            tag = os.path.basename(out) + "-"
            for s, issues, blocks in probe_all(out, args.version, tag):
                print("       %-18s render:%s blocks:%s visual:%s" %
                      (s, "ok" if blocks is not None else "FAIL", blocks,
                       ("CLEAN" if not issues else ",".join(issues))))
    print("\n五屏生成完成。bundle 在 <out>/bundle（read 屏）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
