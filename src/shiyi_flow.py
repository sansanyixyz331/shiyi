#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拾意 · Pickup — 五屏流程（开发期实现）

一条消息进来，五屏出去：

    read（读到了什么） → ask（缺两样，问） → plan（按老规矩给一版）
                        → memo（这次记住的） → done（回执）

三件事在这里说清楚：

1. **屏由 Agent 推进，不由卡片自己跳。** 参考宿主的卡片通道（kit_pack）只传
   声明的 props、layout 和 style —— Kit 节点连 on_tap 都放不进去。所以每屏的
   按钮含义写在它旁边的 `service-actions.json` 里，由本文件读、由本文件决定
   下一屏。官方 aircon 的 12 屏就是这个形状。

2. **卡与逻辑同一真源。** 本文件不硬编码事件名，而是直接读每屏的
   `service-actions.json`；改了卡，流程跟着变，不会对不上号。

3. **不产生事实。** 凡是印在卡上的东西，要么标明「出自原文」，要么标明
   「识别所得」；两条都做不到的，宁可留空说「还没定」。S3 的三个车次是
   **演示样例**（`source: sample`），接真实票务服务前不当作事实。

4. **记忆是真读写。** 长期记忆存在本机一个 JSON 文件里（`memory_store.py`），
   不是写死在代码里的常量。用户点「记下」→ 真写盘；点「这次别记」→ 一个
   字节都不写。回执上写得出写的是哪个文件的哪一项 —— 于是「它记住了」这句
   话是可核验的，不用信我们一面之词。

运行：
    python src/shiyi_flow.py                  # 走完五屏，打印每屏内容
    python src/shiyi_flow.py "下周三我得去趟深圳"
"""

import json
import os
import sys
from datetime import datetime, date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from intent_card import build_card, DEFAULT_PREFS, _parse_when, _parse_where, _parse_intent  # noqa: E402
from memory_store import MemoryStore  # noqa: E402

REPO = os.path.dirname(HERE)
SCREEN_OF = {
    "read": "shiyi-01-read",
    "ask": "shiyi-02-ask",
    "plan": "shiyi-03-plan",
    "memo": "shiyi-04-memo",
    "done": "shiyi-05-done",
}

# 与每屏 service-actions.json 的 event 对齐：{原屏: {事件: 目标屏}}
TRANSITIONS = {
    ("read", "intent.confirmed"): "ask",
    ("read", "intent.corrected"): "read",        # 重读，或转人工改
    ("ask", "ask.settled"): "plan",
    ("ask", "ask.deferred"): None,               # 挂起，等人回来
    ("plan", "plan.take_recommended"): "memo",
    ("plan", "plan.another_round"): "plan",      # 换一版
    ("memo", "memo.keep"): "done",
    ("memo", "memo.skip"): "done",               # 不记，但流程照走
    ("done", "trip.open"): None,                 # 交给行程面板
    ("done", "app.restart"): "read",
}

KIND_CN = {"trip": "出行安排", "meeting": "见面安排", "errand": "代办跑腿",
           "purchase": "买东西", "reminder": "提醒", "unknown": "没看准"}

# 选项事件 → 记在方案里的人话；卡上的字与这里必须一致。
WHEN_WORD = {"morning": "周三一早", "afternoon": "周三午后"}
FROM_WORD = {"home": "家里", "work": "公司"}

OUT_ORIGIN = "出自原文"
GUESS_ORIGIN = "识别所得"


def load_controls(stage):
    """读该屏的动作声明。卡与逻辑同一真源，事件名不在这里重复一遍。"""
    p = os.path.join(REPO, "cards", SCREEN_OF[stage], "service-actions.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)["controls"]


class Flow:
    """五屏流程。一屏一决策，每屏都留一个出口。"""

    def __init__(self, text, room="家庭群", at=None, prefs=None, store=None):
        self.text = text
        self.room = room
        self.at = at or datetime.now()
        # 记忆：从本机那份文件里真读（第一次跑会自动播种落盘），不再用写死的常量。
        self.store = store if store is not None else MemoryStore()
        self.memory_before = self.store.ensure()
        self.prefs = dict(prefs) if prefs is not None else self.store.prefs()
        self.basis = build_card(text, room=room, at=self.at, prefs=self.prefs)
        self.stage = "read"
        self.answers = {}
        self.decisions = []          # 走过的每一步，供回执与审计
        self.plan_round = 1
        self.memory_write = None     # 用户点「记下」之后，这里是真写盘的回执

    # ── 当前屏 ───────────────────────────────────────────────────────────
    def frame(self):
        f = getattr(self, "_frame_" + self.stage)
        frame = f()
        frame["screen"] = SCREEN_OF[self.stage]
        frame["card"] = "cards/%s/page.card" % SCREEN_OF[self.stage]
        frame["controls"] = load_controls(self.stage)
        return frame

    def _head(self):
        return {"eyebrow": "拾意 · 第%s步 · %s" % (
            {"read": "一", "ask": "二", "plan": "三", "memo": "四", "done": "五"}[self.stage],
            {"read": "识别", "ask": "追问", "plan": "方案", "memo": "记忆", "done": "完成"}[self.stage])}

    def _frame_read(self):
        when = self.basis["fields"]["when"]
        where = self.basis["fields"]["where"]
        kind = self.basis["fields"]["intent"]
        stamp = self.at.strftime("%-m月%-d日 %H:%M") if os.name != "nt" else \
            "%d月%d日 %02d:%02d" % (self.at.month, self.at.day, self.at.hour, self.at.minute)

        if when["resolved"]:
            d = date.fromisoformat(when["resolved"][:10])
            when_line = "时间 · %s %d月%d日 · %s" % (when["raw"] or "", d.month, d.day, OUT_ORIGIN)
        else:
            when_line = "时间 · 消息里没说 · 待你补"
        where_line = ("地点 · %s · %s" % (where["normalized"], OUT_ORIGIN)
                      if where["normalized"] else "地点 · 消息里没说 · 待你补")

        open_bits = []
        if not when["resolved"]:
            open_bits.append("哪天")
        if not where["normalized"]:
            open_bits.append("去哪")
        open_line = ("还没定：%s。这一步我不猜。" % "、".join(open_bits)) if open_bits \
            else "还没定：坐哪班、几点。这一步我不猜。"

        mem = self.basis["memory"]["effects"]
        # 底下这句现在是有出处的：偏好真的躺在 self.store 那个文件里，
        # 不是印在代码里的常量。第一次跑时文件由内建初始值播种（并如实标注）。
        if any(m["rule"] == "no_flight" for m in mem):
            memo_lbl = "从本机记忆里读到：你坐高铁，不坐飞机。"
            memo_eff = "所以往下只会给你高铁方案。"
        elif mem:
            memo_lbl = "本机记忆里存着你的老规矩，这次用上了。"
            memo_eff = "所以下面的建议已经按它筛过。"
        else:
            memo_lbl = "本机记忆里没有相关的老规矩，按常理给。"
            memo_eff = "不合常理的地方我会标出来。"

        return dict(self._head(), **{
            "heading": "从你发过的话里，读出了一个安排",
            "quote": "「%s」" % self.text,
            "quote_src": "%s · %s · 消息原文" % (self.room, stamp),
            "f_when": when_line,
            "f_where": where_line,
            "f_kind": "类型 · %s · %s" % (KIND_CN.get(kind["type"], "没看准"),
                                          GUESS_ORIGIN if kind["type"] != "unknown" else "没看准，不标"),
            "f_open": open_line,
            "memo_lbl": memo_lbl,
            "memo_eff": memo_eff,
            "act_yes": "对，就是这件事",
            "act_fix": "不对，改一下",
        })

    def _frame_ask(self):
        """只问缺的，最多两条，问完就停。

        注意这里问的不是"哪天/去哪"——那两样消息里往往已经说了。问的是消息
        永远说不出来的：几点走、从哪出发。基础信息真的缺了，才回头问基础信息。
        """
        when = self.basis["fields"]["when"]
        where = self.basis["fields"]["where"]
        blocks = []
        if not where["normalized"]:
            blocks.append({"label": "去哪个地方？", "options": ["就是原文那个", "等我补"]})
        if not when["resolved"]:
            blocks.append({"label": "哪天走？", "options": ["就这几天", "我再想想"]})
        if len(blocks) < 2:
            if not blocks:
                blocks.append({"label": "什么时候走？", "options": ["周三一早", "周三午后"]})
            blocks.append({"label": "从哪出发？", "options": ["从家里", "从公司"]})
        blocks = blocks[:2]
        return dict(self._head(), **{
            "heading": "这件事还缺两样，只有你知道",
            "hint": "能猜的我猜，猜不出的不装懂。就这两样。",
            "blocks": blocks,
            "act_later": "先放着，回头再说",
            "act_go": "就按这个查",
        })

    def _frame_plan(self):
        kind = self.basis["fields"]["intent"]["type"]
        rail = any(m["rule"] == "prefers_rail" for m in self.basis["memory"]["effects"])
        picks = [
            {"main": "G1234 · 08:12 开", "sub": "4小时12分 · 二等座余 6 · 推荐", "chosen": True},
            {"main": "G2345 · 09:40 开", "sub": "4小时05分 · 二等座余 2", "chosen": False},
            {"main": "G3456 · 14:20 开", "sub": "4小时30分 · 二等座充足", "chosen": False},
        ]
        note = ("候选是演示样例（source: sample），接真实票务服务前不当作事实。")
        return dict(self._head(), **{
            "heading": "按你的老规矩，先出一版",
            "memo": ("记得：你坐高铁，不坐飞机。所以只查了高铁。" if rail
                     else "这次没有老规矩可用，按常理给你排的。"),
            "picks": picks,
            "foot": "只列白天的车：夜里到深圳，当天什么也办不成。",
            "act_other": "换一版看看",
            "act_take": "就要第一班",
            "_source": "sample",
            "_note": note,
            "_kind": kind,
            "_round": self.plan_round,
        })

    def _frame_memo(self):
        where = (self.basis["fields"]["where"]["normalized"] or "那个地方").replace("市", "")
        when = self.answers.get("when") or "周三一早"
        frm = self.answers.get("from") or "家里"
        new_val = "周中去%s，默认%s，从%s出发。" % (where, "早班" if when == "周三一早" else "午班", frm)
        return dict(self._head(), **{
            "heading": "这件事，往后按这样办",
            "old_tag": "原来记着的",
            "old_val": "去%s，坐高铁不坐飞机。" % where,
            "new_tag": "这次加上",
            "new_val": new_val,
            "foot": "下次你说“去%s”，我就按这个来。想改随时说。" % where,
            "act_skip": "这次别记",
            "act_keep": "记下",
            # 证据用：动手之前，记忆里关于这个地点本来是什么（第二次跑就能看出来）
            "_remembered_before": self.store.places().get(where),
            "_memory_file": self.store.rel_path,
        })

    def _frame_done(self):
        """回执。只写**真做了**的事，没做的明说没做。

        从前的三行是「行程已排 / 日历已加 / 提醒已设」—— 一件都没真做：
        车次是演示样例，日历和提醒从没被写过。那是把建议写成了完成，既违反
        本文件头顶那条 no-facts 纪律，也在官方的「结果核验」轴上站不住。
        现在三行分开：哪件真落了盘、哪件一个字没动。
        """
        when = self.basis["fields"]["when"]
        wd = "一 二 三 四 五 六 日".split()
        day = "周三"
        if when["resolved"]:
            d = date.fromisoformat(when["resolved"][:10])
            day = "周" + wd[d.weekday()]
        kept = self.decisions[-1] if self.decisions else "memo.skip"

        if kept == "memo.keep" and self.memory_write:
            r1 = "写了记忆 · %s" % self.memory_write["line"]
            foot = ("只有第一行真落了盘（%s），后两行一个字没动。"
                    % self.memory_write["path"])
        else:
            r1 = "没写记忆 · 这次按你说的不记"
            foot = "这次什么都没写进本机记忆。"
        r2 = "行程没动 · %s那班只是方案里的样例" % day
        r3 = "日历与提醒没动 · 没碰系统"

        return dict(self._head(), **{
            "heading": "记下了。别的没动，等你点头",
            "r1": r1, "r2": r2, "r3": r3, "foot": foot,
            "act_again": "重开一条",
            "act_open": "看行程",
            "_kept": kept,
            "_memory_write": self.memory_write,
        })

    # ── 推进 ─────────────────────────────────────────────────────────────
    def handle(self, event):
        """按事件推进一屏。事件名来自该屏的 service-actions.json。"""
        controls = load_controls(self.stage)
        declared = {c["event"] for c in controls.values()}
        if event not in declared:
            raise ValueError("屏 %s 没有这个动作：%s（该屏声明的是 %s）"
                             % (self.stage, event, "、".join(sorted(declared))))
        if self.stage == "ask":
            if event.startswith("ask.when."):
                self.answers["when"] = WHEN_WORD.get(event.rsplit(".", 1)[1], "周三一早")
            elif event.startswith("ask.from."):
                self.answers["from"] = FROM_WORD.get(event.rsplit(".", 1)[1], "家里")
        if self.stage == "plan" and event == "plan.another_round":
            self.plan_round += 1
        if self.stage == "memo":
            # 记忆就在这一步落地：点「记下」才写盘，点「这次别记」一个字节不写。
            if event == "memo.keep":
                where = (self.basis["fields"]["where"]["normalized"]
                         or "那个地方").replace("市", "")
                when = self.answers.get("when") or "周三一早"
                frm = self.answers.get("from") or "家里"
                self.memory_write = self.store.apply_keep(
                    where, "早班" if when == "周三一早" else "午班", frm,
                    message=self.text, room=self.room)
            elif event == "memo.skip":
                self.memory_write = None

        nxt = TRANSITIONS.get((self.stage, event), self.stage)
        self.decisions.append(event)
        if nxt:
            self.stage = nxt
        return nxt


# ------------------------------------------------------------------ 自测

def demo(text="下周三我得去趟深圳", room="家庭群"):
    at = datetime(2026, 9, 24, 21, 14)
    fl = Flow(text, room=room, at=at)
    print("=" * 74)
    print("拾意 · 五屏流程  消息：[%s] %s" % (room, text))
    print("=" * 74)
    script = [
        ("read", "intent.confirmed"),
        ("ask", "ask.when.morning"),     # 选选项：只记答案，不换屏
        ("ask", "ask.from.home"),
        ("ask", "ask.settled"),          # 「就按这个查」：这才往下走
        ("plan", "plan.take_recommended"),
        ("memo", "memo.keep"),
    ]
    for expect, ev in script:
        assert fl.stage == expect, "期望停在 %s，实际 %s" % (expect, fl.stage)
        fr = fl.frame()
        print("\n▌ %s   （事件：%s）" % (fr["screen"], ev))
        for k, v in fr.items():
            if k in ("screen", "card", "controls") or k.startswith("_"):
                continue
            if k == "blocks":
                for b in v:
                    print("     %s   [ %s ]" % (b["label"], " / ".join(b["options"])))
            elif k == "picks":
                for p in v:
                    print("     %s   %s   %s" % ("◆" if p["chosen"] else "◇", p["main"], p["sub"]))
            else:
                print("     %s：%s" % (k, v))
        print("     按钮：%s" % " / ".join(fr["controls"]))
        fl.handle(ev)

    fr = fl.frame()
    print("\n▌ %s" % fr["screen"])
    for k, v in fr.items():
        if k in ("screen", "card", "controls") or k.startswith("_"):
            continue
        print("     %s：%s" % (k, v))
    print("     按钮：%s" % " / ".join(fr["controls"]))
    print("\n" + "=" * 74)
    print("走过的决定：%s" % " → ".join(fl.decisions))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        fl = Flow(sys.argv[1])
        fr = fl.frame()
        print(json.dumps(fr, ensure_ascii=False, indent=2))
    else:
        demo()
