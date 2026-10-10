#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拾意 · 甲方案「状态变化 → 原地改卡」—— 识别 + 匹配 + 时间写全 逻辑本地验证
（不编宿主、不碰提交物）

目的：把要加进 `octos/apps/shiyi/bundle/main.splash` 的逻辑（识别 update / 匹配旧卡 / 定动作 /
      「相对时间词 → 绝对日期」）用**同款正则**在本地跑通，证明"算法成立"，再落到 splash。
口径：与 os.shiyi `main.splash` 一致 —— `when_of` / `where_of` / `day_abs` / `week_abs`
      **逐字镜像**（见 splash）。`splash` 不支持的正则特性这里也不用（保持可移植）。
      日期换算用 `base` 注入基准日，便于用固定日期断言、且脚本永远可复跑。

跑：python build/verify_update_logic.py
"""

import re
from datetime import date, timedelta

# ---------------------------------------------------------------- 与 splash 同款正则（逐字复制）
DAY = r"(大后天|后天|明天|今天|明早|今晚|下下周|下下个月|下个月|这个月|这周末|周末|下周[一二三四五六日天]|下个星期|下星期|这个星期|周[一二三四五六日天]|星期[一二三四五六日天])"
PART = r"(上午|下午|晚上|中午|早上|凌晨|傍晚)"
WD_CH = ["一", "二", "三", "四", "五", "六", "日", "天"]


def grab(t, pat):
    m = re.search(pat, t)
    return m.group(0) if m else ""


def grab_cap(t, pat):
    m = re.search(pat, t)
    if not m or m.lastindex is None or m.lastindex < 1:
        return ""
    return m.group(1) or ""


# ---------------------------------------------------------------- 「相对时间词 → 绝对日期」（镜像 splash）
def _today(base):
    return base if base is not None else date.today()


def today_m(base=None):                 # 今天周几：周一=1 … 周日=7
    return _today(base).weekday() + 1   # Python: Mon=0 → 1


def wd_num(ch):                         # 「三」→ 3；「日 / 天」→ 7
    return {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}.get(ch, 7)


def date_str(base=None, off=0):         # base+off 天 → 「10月14日」
    d = _today(base) + timedelta(days=off)
    return "%d月%d日" % (d.month, d.day)


def week_abs(d, ch, base=None):         # 「下周三」「周五」→ 那天到底几月几号
    m = today_m(base)
    tgt = wd_num(ch)
    nx = tgt - m
    if nx <= 0:
        nx += 7                         # 本周这天已过 → 顺延到下周
    if re.search(r"下周|下星期|下礼拜", d):
        if tgt > m:                     # 只在这天还没到（仍在本周内）时才再顺延一周
            nx += 7
    return date_str(base, nx)


def day_abs(d, base=None):
    if not d:
        return ""
    if re.search(r"今天|今晚", d):
        return date_str(base)
    if re.search(r"明天|明早", d):
        return date_str(base, 1)
    if re.search(r"大后天", d):
        return date_str(base, 3)
    if re.search(r"后天", d):
        return date_str(base, 2)
    if re.search(r"周末", d):
        m = today_m(base)
        nx = 6 - m
        if nx < 0:
            nx += 7
        return date_str(base, nx)
    if re.search(r"下下个月", d):
        mo = _today(base).month + 2
        if mo > 12:
            mo -= 12
        return "%d月" % mo
    if re.search(r"下个月", d):
        mo = _today(base).month + 1
        if mo > 12:
            mo = 1
        return "%d月" % mo
    if re.search(r"这个月", d):
        return "%d月" % _today(base).month
    for c in WD_CH:
        if c in d:
            return week_abs(d, c, base)
    return ""


def when_of(t, base=None):
    # splash: 内联复合正则（when_of 不再拆 when_raw —— splash 里嵌套调用该复合正则会返回错值）
    pat = "(" + DAY + PART + r"?[0-9]{1,2}(点|时)[0-9]{0,2}分?|" + DAY + PART + "?|" + PART + r"[0-9]{0,2}(点|时)?)"
    raw = grab(t, pat)
    if raw == "":
        return ""
    d = grab(t, DAY)
    if d == "":
        return raw
    abs_ = day_abs(d, base)
    if abs_ == "":
        return raw
    return raw + "（" + abs_ + "）"


def when_phrase(w):
    """卡片存的 when 值（如「下周三（10月14日）」）→ 去掉括弧后的原话（「下周三」）。"""
    if not w:
        return ""
    ps = w.split("（")
    if len(ps) > 1:
        return ps[0]
    return w


def retime_body(text, old_when, new_when):
    """改卡时把**卡正文里**那句时间也一并换成新的（镜像 splash retime_body）。

    旧时间直接从卡片**已存的** when 值里取（old_when / when_phrase），不再对正文重跑正则
    （splash 里对正文再跑一遍那套复合正则会返回被截断的错值）。
    先按整段带日期替换；正文里若只有相对词，再退回按原话替换。换不到原样返回。
    """
    if new_when == "":
        return text
    if old_when != "":
        r = text.replace(old_when, new_when)
        if r != text:
            return r
        ph = when_phrase(old_when)
        if ph != "":
            r2 = text.replace(ph, new_when)
            if r2 != text:
                return r2
    return text


def where_of(t):
    # splash: "[去在到回来]([^，,。；;！!？? 的见开做吃拿买发打看聊谈写改送取接陪要想要去过讨了啊呢吧呀吗嘛哦哈就还也再都]{1,8})"
    # 排除字表新增句尾语气词（了/啊/呢/吧…）—— 否则「改到周五了啊」会把地点抓成「周五了啊」。
    return grab_cap(t, r"[去在到回来]([^，,。；;！!？? 的见开做吃拿买发打看聊谈写改送取接陪要想要去过讨了啊呢吧呀吗嘛哦哈就还也再都]{1,8})")


# ---------------------------------------------------------------- 第 7 类「状态变化」识别
UPD_VERB = r"(改到|改成|改在|换成|推迟|延后|提前|取消|不去了|不办了|不开了|不搞了)"
UPD_CANCEL = r"(取消|不去了|不办了|不开了|不搞了|算了)"
SUBJ = r"([^，,。；;！!？? 的见开做吃拿买发打看聊谈写改送取接陪要想要去过讨]{2,8}?)(那个|那趟|这趟|这张|这次|那次)"
SPLIT = r"(改到|改成|改在|换成|推迟到|推迟|延后到|延后|提前到|提前|取消|不去了|不办了|不开了|不搞了)"


def is_update(t):
    return re.search(UPD_VERB, t) is not None


def is_cancel(t):
    return re.search(UPD_CANCEL, t) is not None


def subject_of(t):
    return grab_cap(t, SUBJ)


def split_new(t):
    m = re.search(SPLIT, t)
    if not m:
        return t, ""
    return t[: m.start()], t[m.end():]


# ---------------------------------------------------------------- 卡索引（= splash 的 picks）
def match_card(picks, t):
    subj = subject_of(t)
    if subj != "":
        for e in picks:
            if e["where"] != "" and (subj.find(e["where"]) >= 0 or e["where"].find(subj) >= 0):
                return e, "指代→地点:" + e["where"]
        for e in picks:
            if subj in e["text"] or e["text"] in subj:
                return e, "指代→标题"
    for e in picks:
        if e["where"] != "" and e["where"] in t:
            return e, "句中地点:" + e["where"]
    if subj == "" and picks:
        return picks[-1], "无指代→最近一张"
    return None, "没匹配到"


def decide_action(picks, t, base=None):
    out = {"input": t, "is_update": False, "action": "", "card_id": "", "how": "",
           "new_when": "", "new_where": "", "note": ""}
    if not is_update(t):
        out["note"] = "不是状态变化 —— 走原造卡"
        return out
    out["is_update"] = True
    card, how = match_card(picks, t)
    out["how"] = how
    if card is None:
        out["action"] = "no_match"
        out["note"] = "没找到那张卡 —— 如实告诉用户（不新造）"
        return out
    out["card_id"] = card["id"]
    if is_cancel(t):
        out["action"] = "withdraw"
        out["note"] = "取消 → 撤掉那张卡"
        return out
    # 新值：与 splash 一致，从**整句**里取（不是只取「改后段」）。
    nw = when_of(t, base)
    npl = where_of(t)
    if npl != "" and (nw != "" and (npl in nw or nw in npl)):
        npl = ""
    out["new_when"] = nw
    out["new_where"] = npl
    out["action"] = "repin"
    out["note"] = "原地改卡：时间→" + (nw or "（不变）") + " 地点→" + (npl or "（不变）")
    return out


# ---------------------------------------------------------------- 日期换算单元测试（固定基准日）
def test_dates():
    BASE = date(2026, 10, 9)            # 2026-10-09 = 周五
    checks = [
        ("今天", "10月9日"),
        ("明天", "10月10日"),
        ("后天", "10月11日"),
        ("周六", "10月10日"),
        ("周末", "10月10日"),
        ("周五", "10月16日"),           # 今天周五 → 下一个周五
        ("下周五", "10月16日"),
        ("周三", "10月14日"),           # 本周三已过 → 下周三
        ("下周三", "10月14日"),
        ("下周一", "10月12日"),
        ("下个月", "11月"),
    ]
    print("=" * 78)
    print("日期换算：相对时间词 → 绝对日期（基准日固定为 2026-10-09 周五）")
    print("=" * 78)
    ok = 0
    for d, want in checks:
        got = day_abs(d, BASE)
        good = got == want
        if good:
            ok += 1
        print("  [%s] %-6s → %-10s %s" % ("PASS" if good else "FAIL", d, got or "(空)", "" if good else "期望 " + want))
    print("\n  日期换算: %d/%d 通过" % (ok, len(checks)))
    return ok, len(checks)


# ---------------------------------------------------------------- 正文改写单元测试（0.3.2：正文时间也跟着改）
def test_retime():
    BASE = date(2026, 10, 9)            # 2026-10-09 = 周五
    checks = [
        # (原正文, 卡上旧 when 值, 新时间串, 期望正文)
        # 首次改卡：正文里只有相对词，退回按「原话」替换
        ("下周三去深圳见客户", "下周三（10月14日）", "周五（10月16日）", "周五（10月16日）去深圳见客户"),
        # 二次改卡：正文已是「带日期的整段」，按整段替换（不能残留旧括弧）
        ("周五（10月16日）去深圳见客户", "周五（10月16日）", "周三（10月14日）", "周三（10月14日）去深圳见客户"),
        ("周五（10月16日）去深圳见客户", "周五（10月16日）", "周日（10月18日）", "周日（10月18日）去深圳见客户"),
        # 正文里根本没提时间 → 原样返回（不硬塞一个时间进去）
        ("见个客户", "", "周五（10月16日）", "见个客户"),
        # 新时间为空（只是改了地点）→ 正文不动
        ("下周三去深圳见客户", "下周三（10月14日）", "", "下周三去深圳见客户"),
    ]
    # when_phrase：卡片 when 值 → 去掉括弧后的原话
    phrase_checks = [
        ("下周三（10月14日）", "下周三"),
        ("下周三", "下周三"),
        ("", ""),
    ]
    print()
    print("=" * 78)
    print("正文改写：改卡时把卡正文里那句时间一并换新（旧时间取自卡片已存的 when 值）")
    print("=" * 78)
    ok = 0
    for src, ow, nw, want in checks:
        got = retime_body(src, ow, nw)
        good = got == want
        # 附加红线：结果里不许残留「旧括号日期」（两个「（M月D日）」并存）
        if len(re.findall(r"（\d+月\d+日）", got)) > 1:
            good = False
        if good:
            ok += 1
        print("  [%s] %-24s old=%-14s + %-14s → %s"
              % ("PASS" if good else "FAIL", src, ow or "(空)", nw or "(空)", got))
        if not good:
            print("        期望: %s" % want)
    pok = 0
    for w, want in phrase_checks:
        got = when_phrase(w)
        good = got == want
        if good:
            pok += 1
        print("  [%s] when_phrase(%-16s) → %s" % ("PASS" if good else "FAIL", w or "(空)", got or "(空)"))
    print("\n  正文改写: %d/%d 通过 ／ when_phrase: %d/%d" % (ok, len(checks), pok, len(phrase_checks)))
    return ok + pok, len(checks) + len(phrase_checks)


# ---------------------------------------------------------------- 跑用例
def main():
    P = [{"id": "shiyi-p1", "text": "下周三去深圳见客户", "when": "下周三", "where": "深圳", "at": "2026-10-6 14:08", "key": "k1"},
         {"id": "shiyi-p2", "text": "明天下午三点跟老王在杭州碰一下", "when": "明天下午三点", "where": "杭州", "at": "2026-10-6 14:09", "key": "k2"}]

    P_SH = [{"id": "shiyi-p9", "text": "下周三去上海见客户", "when": "下周三", "where": "上海", "at": "2026-10-9 19:40", "key": "k9"}]

    cases = [
        # (输入, 卡索引, 期望动作, 期望匹配说明, 期望新时间前缀, 期望新地点)
        ("深圳那个改到周五", P[:1], "repin", "指代→地点:深圳", "周五", ""),
        ("深圳那趟改到周五", P[:1], "repin", "指代→地点:深圳", "周五", ""),
        ("深圳那趟改到周五了啊", P[:1], "repin", "指代→地点:深圳", "周五", ""),
        ("上海那个改到深圳", P_SH, "repin", "指代→地点:上海", "", "深圳"),
        ("杭州那个改成下周四下午两点", P, "repin", "指代→地点:杭州", "", ""),
        ("深圳那个取消了", P[:1], "withdraw", "指代→地点:深圳", "", ""),
        ("改到周五", P, "repin", "无指代→最近一张", "周五", ""),
        ("杭州那个改到明天", P[:1], "no_match", "没匹配到", "", ""),
        ("明天下午三点跟老王在杭州碰一下", P, "", "不是状态变化 —— 走原造卡", "", ""),
        ("深圳那个改到周五", [], "no_match", "没匹配到", "", ""),
    ]

    print("=" * 78)
    print("拾意 · 甲方案「状态变化→原地改卡」识别+匹配 本地验证")
    print("=" * 78)
    ok = 0
    for t, picks, want_action, want_how, want_when, want_where in cases:
        r = decide_action(picks, t)
        got_action = r["action"]
        good = (got_action == want_action
                and (want_when == "" or r["new_when"].startswith(want_when))
                and (want_where == "" or r["new_where"] == want_where))
        if good:
            ok += 1
        print("\n[%s] 输入: %s" % ("PASS" if good else "FAIL", t))
        print("      卡索引: %s" % ([e["id"] + "/" + (e["where"] or "-") for e in picks] or "（空）"))
        print("      识别update=%s  匹配=%s" % (r["is_update"], r["how"]))
        print("      动作=%s  目标卡=%s  新时间=%s  新地点=%s" % (got_action, r["card_id"] or "-", r["new_when"] or "-", r["new_where"] or "-"))
        print("      说明: %s" % r["note"])
        if not good:
            print("      ⚠ 期望 动作=%s 新时间前缀=%s 新地点=%s" % (want_action, want_when or "(不校验)", want_where or "(不校验)"))
    print("\n" + "=" * 78)
    print("识别+匹配: %d/%d 通过" % (ok, len(cases)))
    print("=" * 78)

    print()
    dok, dtotal = test_dates()

    print()
    rok, rtotal = test_retime()

    print()
    all_ok = (ok == len(cases)) and (dok == dtotal) and (rok == rtotal)
    print("=" * 78)
    print("总结果: %s（识别+匹配 %d/%d ／ 日期换算 %d/%d ／ 正文改写 %d/%d）"
          % ("全通过 ✅" if all_ok else "有失败 ❌", ok, len(cases), dok, dtotal, rok, rtotal))
    print("=" * 78)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
