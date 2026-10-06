# -*- coding: utf-8 -*-
"""对已跟踪的证据文件做一次就地脱敏 —— 只改文本，保留全部证据语义。

用法：
    python build/scrub_evidence.py            # dry-run，只报告
    python build/scrub_evidence.py --apply    # 真的写回

规则与 verify_flow.scrub 一致：把本机私有路径/用户名换成中性占位。
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import verify_flow as VF  # noqa: E402

# 需要脱敏的证据文件（相对仓库根）
TARGETS = [
    "build/_evidence/flow_run.json",
    "build/_evidence/host_shiyi-01-read.log",
    "build/_evidence/host_shiyi-02-ask.log",
    "build/_evidence/host_shiyi-03-plan.log",
    "build/_evidence/host_shiyi-04-memo.log",
    "build/_evidence/host_shiyi-05-done.log",
    "build/_evidence/neg_tampered.log",
    "build/_evidence/neg_unsigned.log",
    "docs/evidence/repin/desktop_card_chat.jsonl",
]


def scan(path):
    with open(path, "rb") as f:
        raw = f.read()
    if b"\x00" in raw[:4096]:
        return None
    try:
        txt = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    new = VF._scrub_text(txt)
    n = sum(1 for a, b in zip(txt, new) if a != b)  # 粗略变化量
    return txt, new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的写回（默认 dry-run）")
    args = ap.parse_args()

    root = os.path.dirname(HERE)
    changed = 0
    for rel in TARGETS:
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            print("· 跳过（不存在）%s" % rel)
            continue
        r = scan(p)
        if r is None:
            print("· 跳过（二进制/非 UTF-8）%s" % rel)
            continue
        txt, new = r
        if txt == new:
            print("✓ 已干净  %s" % rel)
            continue
        changed += 1
        print("✎ 需脱敏  %s（%d 字节变化）" % (rel, len(new) - len(txt)))
        if args.apply:
            with open(p, "wb") as f:        # 二进制写：换行不受平台影响
                f.write(new.encode("utf-8"))
            print("   已写回")
    print("\n合计需脱敏文件：%d%s" % (changed, "" if args.apply else "（dry-run，未写回）"))


if __name__ == "__main__":
    sys.exit(main())
