#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拾意 · 一条命令走完「生成 -> 自评 -> 渲染 -> 过门禁」。

    python build/pipeline.py --samples --out build/_gen
    python build/pipeline.py --text "下周三我得去趟深圳" --room 家庭群 --out build/_gen/one

四个阶段（每张卡都走）：
  1. 生成    build/gen_l0.py  —— 意图 -> bundle（内含自评修订回路）
  2. 渲染    build/shot_bundle.py —— card-host --remote 抓真实帧进 bundle
  3. 门禁    WSL 里的官方 Linux `hub stamp` + `hub check`（判定环境是 Linux）
  4. 汇总    build/_gen/pipeline_report.json —— 每张卡的行数/自评/门禁结论

为什么门禁放 WSL：Windows 的 hub 与 Linux 的 hub 对同一 bundle 算出的
bundle_blake3 不同，官方判据在 Linux，所以最终判定一律走 WSL。
"""

import argparse
import json
import os
import subprocess
import sys

BUILD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BUILD)
import gen_l0          # noqa: E402
import shot_bundle     # noqa: E402

WSL = ["wsl.exe", "-d", "Ubuntu-24.04", "-e", "bash", "-lc"]
LINUX_HUB = "$HOME/gosim_check/target/debug/hub"


def linux_stamp_check(bundle_dir):
    """把 Windows 路径翻成 /mnt/c/... 再交给 WSL 里的官方 hub。"""
    p = bundle_dir.replace("\\", "/")
    drive = p[0].lower()
    mnt = "/mnt/%s%s" % (drive, p[2:])
    cmd = "%s stamp %s >/dev/null 2>&1; %s check %s --allow-unsigned 2>&1 | head -8" % (
        LINUX_HUB, mnt, LINUX_HUB, mnt)
    r = subprocess.run(WSL + [cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    passed = "— PASSED" in out
    return passed, out.strip()


def stage(src_dir, bundle_dir, report):
    code, log = gen_l0.lint(bundle_dir)
    report["lint_ok"] = (code == 0)
    report["stages"]["lint"] = "ok" if code == 0 else "FAIL"
    if code != 0:
        return False
    shot_bundle.shot(bundle_dir)
    report["stages"]["render"] = "ok"
    passed, out = linux_stamp_check(bundle_dir)
    report["stages"]["hub_check"] = "PASSED" if passed else "REFUSED"
    report["hub_check_output"] = out
    return passed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text")
    ap.add_argument("--room", default="家庭群")
    ap.add_argument("--samples", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--id", default="shiyi-gen")
    ap.add_argument("--name", default="拾意 · 生成卡")
    ap.add_argument("--version", default="0.2.0")
    ap.add_argument("--memory")
    ap.add_argument("--no-render", action="store_true", help="只生成，不渲染/门禁")
    args = ap.parse_args()

    # 记忆（能力②）
    if gen_l0.MemoryStore is None:
        prefs, memory_note = None, "builtin"
    else:
        st = gen_l0.MemoryStore(args.memory) if args.memory else gen_l0.MemoryStore()
        st.ensure()
        prefs = st.prefs()
        memory_note = st.rel_path

    os.makedirs(args.out, exist_ok=True)
    jobs = []
    if args.samples:
        from intent_card import SAMPLES  # noqa
        for i, (text, room) in enumerate(SAMPLES, 1):
            jobs.append((text, room, os.path.join(args.out, "%02d" % i)))
    elif args.text:
        jobs.append((args.text, args.room, os.path.join(args.out, "card")))
    else:
        ap.error("给 --text 或 --samples")

    report = {"memory": memory_note, "cards": []}
    all_ok = True
    for text, room, out_dir in jobs:
        code, review = gen_l0.generate_one(text, room, out_dir, args.id, args.name,
                                           args.version, prefs, memory_note)
        b = os.path.join(out_dir, "bundle")
        rec = {"text": text, "bundle": b.replace("\\", "/"),
               "review_converged": review["converged"],
               "issues_fixed": sum(len(x["issues"]) for x in review["rounds"]),
               "stages": {"gen": "ok" if code == 0 else "FAIL"}}
        if args.no_render:
            ok = code == 0
        else:
            ok = stage(out_dir, b, rec)
        all_ok = all_ok and ok
        report["cards"].append(rec)

    rp = os.path.join(args.out, "pipeline_report.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("\n===== pipeline 汇总 =====")
    for c in report["cards"]:
        st = c["stages"]
        print("  %-26s gen:%s render:%s hub:%s" %
              (c["text"][:24], st.get("gen"), st.get("render", "-"), st.get("hub_check", "-")))
    print("  记忆: %s" % report["memory"])
    print("  报告: %s" % rp)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
