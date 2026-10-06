#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""识别层对照演示 —— 同一句话，本地规则 vs 设备助手（本机模型）。

这是复赛「效果证据」的一件工具：一条命令产出**可核验的对照**（同一句话，
两条识别路各自认出了什么），并把机器可读的结果落盘，便于复核。

两条路的关系（不是二选一，是"有则用、无则退"）：

  · 助手可用（宿主提供 `model.complete`）→ 走模型，卡片标"识别来源 · 设备助手"；
  · 助手不可用（官方现状：没有任何 Shell 提供 model 服务）→ 回退本地规则，
    卡片标"识别来源 · 本地规则"。**两条路产出的卡同构，下游一行都不用改。**

用法：

    python build/demo_identify.py --samples
    python build/demo_identify.py --text "下个月初得去趟慕尼黑看展会" --json ev.json
    python build/demo_identify.py --samples --no-model     # 只看规则路
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (os.path.join(ROOT, "src"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from intent_card import SAMPLES, build_card            # noqa: E402
from intent_model import identify_card                 # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def _fmt(card):
    f = card["fields"]
    return {
        "when": f["when"]["resolved"] or f["when"]["raw"] or "",
        "where": f["where"]["normalized"] or f["where"]["raw"] or "",
        "kind": f["intent"]["type"],
        "open": [q["ask"] for q in card.get("questions", [])],
        "source": card.get("identify_source", "rules"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text")
    ap.add_argument("--samples", action="store_true")
    ap.add_argument("--room", default="家庭群")
    ap.add_argument("--no-model", action="store_true", help="只跑本地规则路")
    ap.add_argument("--json", help="把对照结果落盘到这个路径")
    args = ap.parse_args()

    texts = [t for t, _ in SAMPLES] if args.samples else ([args.text] if args.text else [])
    if not texts:
        ap.error("给 --text 或 --samples")

    host = None
    if not args.no_model:
        try:
            from host_local import LocalModelHost
            host = LocalModelHost()
        except Exception as e:  # noqa: BLE001
            print("[识别] 本机模型不可用，只跑规则路：%s" % e)

    print("=" * 78)
    print("识别层对照：同一句话 —— 本地规则 vs 设备助手（本机模型）")
    print("宿主：%s" % (host.describe() if host else "（未启用，只跑规则）"))
    print("=" * 78)

    rows = []
    for t in texts:
        rcard = build_card(t, room=args.room)
        rcard["identify_source"] = "rules"
        entry = {"text": t, "rules": _fmt(rcard)}
        if host:
            mcard, meta = identify_card(t, room=args.room, host=host)
            entry["model"] = _fmt(mcard)
            entry["identify"] = meta
        rows.append(entry)

        print("\n消息：%s" % t)
        print("  规则 : when=%-12s where=%-12s kind=%-9s open=%s"
              % (entry["rules"]["when"] or "—", entry["rules"]["where"] or "—",
                 entry["rules"]["kind"], "、".join(entry["rules"]["open"]) or "无"))
        if "model" in entry:
            print("  模型 : when=%-12s where=%-12s kind=%-9s open=%s"
                  % (entry["model"]["when"] or "—", entry["model"]["where"] or "—",
                     entry["model"]["kind"], "、".join(entry["model"]["open"]) or "无"))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("\n证据已落盘：%s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
