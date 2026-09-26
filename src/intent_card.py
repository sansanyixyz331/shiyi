#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拾意 · Pickup — 意图卡片核心逻辑（开发期原型）

作用：把一条聊天消息，转成一张「待用户确认的卡片」的语义结构。
    这是**开发期验证件**：用来先把"识别什么、标注什么、记忆怎么生效"跑通，
    正式交付物是经 Image-to-AppCard 工作流生成的 Card bundle（bundle/）。

no-facts 纪律：
    本文件只做**识别与组织**，不产生任何事实。
    所有对外可见的事实（时间/地点/来源）都必须带 `source` 字段，标明来处。

运行：
    python src/intent_card.py            # 跑自带样例自测
    python src/intent_card.py "下周三我得去趟深圳"
"""

import json
import re
import sys
from datetime import date, datetime, timedelta

try:  # Windows 控制台中文保护
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

WEEKDAYS = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}

CN_NUM = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5,
          "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12}

# 指代词：出现即"不猜"，出追问卡
AMBIG_REFS = ("那个", "那件", "那笔", "上次说的", "之前说的", "老地方")

# 地点白名单（识别用；非白名单的一律标 low_confidence，不猜）
CITIES = [
    "深圳", "北京", "上海", "广州", "杭州", "成都", "重庆", "武汉", "西安",
    "南京", "苏州", "天津", "长沙", "青岛", "厦门", "郑州", "合肥", "宁波",
]

# 意图类型：动词线索 → 类型
INTENT_RULES = [
    (("去", "出差", "飞", "高铁", "机票", "酒店"), "trip"),
    (("见", "碰", "开会", "约", "谈", "面"), "meeting"),
    (("寄", "快递", "送", "取", "还", "交"), "errand"),
    (("买", "订", "下单", "付款"), "purchase"),
    (("提醒", "别忘了", "记得"), "reminder"),
]

DEFAULT_PREFS = {
    "prefers_rail": True,     # 一贯坐高铁
    "no_flight": True,        # 不坐飞机
    "no_wednesday_pm": True,  # 周三下午不排事
}


# ---------------------------------------------------------------- 识别

def _parse_when(text: str, today: date):
    """返回 (原文, 解析日期 或 None, 置信度)。只认明确说法，不猜。"""
    if "今天" in text:
        return "今天", today, 0.95
    if "明天" in text:
        return "明天", today + timedelta(days=1), 0.95
    if "后天" in text:
        return "后天", today + timedelta(days=2), 0.9

    m = re.search(r"(下{1,2})?(?:周|星期|礼拜)([一二三四五六日天])", text)
    if m:
        nx, wd = m.group(1), WEEKDAYS[m.group(2)]
        raw = m.group(0)
        monday = today - timedelta(days=today.weekday())   # 本周一
        weeks = len(nx) if nx else 0                       # "下"=下 1 周，"下下"=下 2 周
        target = monday + timedelta(weeks=weeks, days=wd)
        if not nx and target < today:                      # 本周该天已过 → 指下周
            target += timedelta(weeks=1)
        return raw, target, 0.9 if nx else 0.8

    m = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]", text)
    if m:
        mo, dy = int(m.group(1)), int(m.group(2))
        year = today.year + (1 if mo < today.month else 0)
        try:
            return m.group(0), date(year, mo, dy), 0.9
        except ValueError:
            return m.group(0), None, 0.2

    m = re.search(r"(\d{1,2})\s*[:：]\s*(\d{2})", text)
    if m:  # 只有时刻、没有日期 → 不构成日程，交给人
        return m.group(0), None, 0.3

    return None, None, 0.0


def _parse_clock(text: str):
    """解析时刻：15:30 / 下午三点半 / 晚上8点。返回 (原文, 时, 分)；认不出返回 (None,None,None)。"""
    m = re.search(r"(\d{1,2})\s*[:：]\s*(\d{2})", text)
    if m:
        return m.group(0), int(m.group(1)), int(m.group(2))

    m = re.search(
        r"(上午|早上|中午|下午|傍晚|晚上)?\s*(十[一二]|[一二三四五六七八九十]|\d{1,2})\s*[点时](半|\d{1,2}分?)?",
        text)
    if not m:
        return None, None, None
    part, num, mm = m.group(1), m.group(2), m.group(3)
    h = int(num) if num.isdigit() else CN_NUM.get(num)
    if h is None:
        return None, None, None
    mi = 30 if mm == "半" else (int(re.sub(r"\D", "", mm)) if mm else 0)
    if part in ("下午", "傍晚", "晚上") and h < 12:
        h += 12
    if part == "中午" and h < 12:
        h = 12
    return m.group(0), h, mi


def _ambiguous_refs(text: str):
    return [w for w in AMBIG_REFS if w in text]


def _parse_where(text: str):
    for c in CITIES:
        if c in text:
            return c, "深圳市" if c == "深圳" else c, 0.9
    m = re.search(r"去(?:趟|一趟)?([\u4e00-\u9fa5]{2,4})", text)
    if m:
        return m.group(1), None, 0.4  # 非白名单 → 低置信，不补全
    return None, None, 0.0


def _parse_intent(text: str):
    for keys, kind in INTENT_RULES:
        for k in keys:
            if k in text:
                return kind, 0.75
    return "unknown", 0.0


def _memory_applies(intent: str, when, prefs: dict):
    """命中哪条长期偏好、因此改变了什么。"""
    hits = []
    if intent == "trip" and prefs.get("no_flight"):
        hits.append({"rule": "no_flight", "effect": "excluded_flight"})
    if intent == "trip" and prefs.get("prefers_rail"):
        hits.append({"rule": "prefers_rail", "effect": "filtered_to_rail"})
    if when and prefs.get("no_wednesday_pm") and when.weekday() == 2:
        hits.append({"rule": "no_wednesday_pm", "effect": "flagged_schedule_conflict"})
    return hits


# ---------------------------------------------------------------- 组卡

def build_card(text: str, room: str = "家庭群", at: datetime = None,
               prefs: dict = None, today: date = None):
    at = at or datetime.now()
    today = today or at.date()
    prefs = prefs if prefs is not None else DEFAULT_PREFS

    raw_when, when, conf_when = _parse_when(text, today)
    clock_raw, ch, cm = _parse_clock(text)
    if when is None and ch is not None:        # 只有时刻、没日期 → 默认今天，低置信，交人确认
        when, conf_when = today, 0.6
    when_dt = datetime(when.year, when.month, when.day, ch or 0, cm or 0) if when else None
    raw_where, where, conf_where = _parse_where(text)
    intent, conf_intent = _parse_intent(text)
    mem = _memory_applies(intent, when, prefs)
    ambig = _ambiguous_refs(text)

    facts = [
        {"what": "quote", "value": text, "from": "message_text"},
        {"what": "room", "value": room, "from": "message_meta"},
        {"what": "at", "value": at.isoformat(timespec="seconds"), "from": "system_clock"},
    ]
    if when_dt:
        facts.append({"what": "when", "value": when_dt.isoformat(), "from": "rules(parse_when)+text(clock)"})
    if where:
        facts.append({"what": "where", "value": where, "from": "rules(parse_where)"})

    questions = []
    if raw_when is None and clock_raw is None:
        questions.append({"field": "when", "ask": "这事安排在哪天？"})
    if where is None:
        questions.append({"field": "where", "ask": "什么地方？"})
    if ambig:
        questions.append({"field": "reference", "ask": "「%s」指的是哪一个？" % ambig[0]})

    card = {
        "card": "intent_confirm",
        "title": "拾到一个安排",
        "quote": text,
        "source": {"room": room, "at": at.isoformat(timespec="seconds"), "kind": "message"},
        "fields": {
            "when": {"raw": raw_when, "clock": clock_raw,
                     "resolved": when_dt.isoformat() if when_dt else None,
                     "confidence": conf_when, "needs_user": when_dt is None},
            "where": {"raw": raw_where, "normalized": where,
                      "confidence": conf_where, "needs_user": where is None},
            "intent": {"type": intent, "confidence": conf_intent},
        },
        "memory": {"hit": bool(mem), "effects": mem},
        "questions": questions,
        "actions": ["confirm", "edit", "dismiss"],
        "facts": facts,
        "disclaimer": "以上全部来自消息原文与本地规则；未查询任何外部服务。确认后才执行。",
    }
    return card


# ---------------------------------------------------------------- 自测

SAMPLES = [
    ("下周三我得去趟深圳", "家庭群"),
    ("明天下午三点跟老王在杭州碰一下", "同事群"),
    ("帮我把那个快递寄到上海", "家庭群"),
]


def _selftest():
    today = date(2026, 9, 25)
    at = datetime(2026, 9, 24, 21, 14)
    print("=" * 72)
    print("拾意 · 意图卡片原型自测   （基准日 %s）" % today.isoformat())
    print("=" * 72)
    for text, room in SAMPLES:
        c = build_card(text, room=room, at=at, today=today)
        print("\n▶ 消息：[%s]  %s" % (room, text))
        f = c["fields"]
        print("   时间：%s → %s  (conf %.2f)" % (f["when"]["raw"], f["when"]["resolved"], f["when"]["confidence"]))
        print("   地点：%s → %s  (conf %.2f)" % (f["where"]["raw"], f["where"]["normalized"], f["where"]["confidence"]))
        print("   类型：%s  (conf %.2f)" % (f["intent"]["type"], f["intent"]["confidence"]))
        if c["memory"]["hit"]:
            print("   记忆命中：%s" % json.dumps(c["memory"]["effects"], ensure_ascii=False))
        print("   待确认项：%s" % ("无" if not (f["when"]["needs_user"] or f["where"]["needs_user"]) else
                                " / ".join(k for k in ("when", "where") if f[k]["needs_user"])))
        if c["questions"]:
            print("   追问：%s" % " | ".join(q["ask"] for q in c["questions"]))
        print("   动作：%s" % " / ".join(c["actions"]))
        print("   事实来源：%s" % ", ".join("%s←%s" % (x["what"], x["from"]) for x in c["facts"]))
    print("\n" + "=" * 72)
    print("完整卡片 JSON（样例 1）：")
    print(json.dumps(build_card(SAMPLES[0][0], at=at, today=today), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(build_card(sys.argv[1]), ensure_ascii=False, indent=2))
    else:
        _selftest()
