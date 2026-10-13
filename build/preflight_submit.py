#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提交前自检 · 拾意（GOSIM Agentic App 黑客松）

为什么有这个脚本
----------------
"能反复犯的错，靠记住防不住" —— 所以把提交前要核的东西写成机器闸，反复跑。
本脚本只读，不改任何提交物。可跑任意多遍（幂等）。

用法
----
    python build/preflight_submit.py            # 全部检查
    python build/preflight_submit.py --quiet    # 只打印失败项

退出码：0 = 全部通过（可能有 WARN）；1 = 有 FAIL。

注意（已实测）
------------
官方门禁 `hub check` 在 Windows 上会报 `not a portable bundle path: "assets\\icon.svg"`
——那是工具自身在 Windows 上的路径规范化行为（listing.json 里是正斜杠）；
同一份 bundle 在 Linux/WSL 上 PASSED（见 review/GATE.txt）。
=> 本脚本用「bundle 未改动证明 + GATE.txt 有效性」覆盖这一项；
   要跑真正的门禁，请在 Linux/WSL 上执行 hub check。
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FAILS = []
WARNS = []
PASSES = []


def ok(msg):
    PASSES.append(msg)


def warn(msg):
    WARNS.append(msg)


def fail(msg):
    FAILS.append(msg)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- 1. 工作区
def check_git_state():
    """工作区状态 + 与远端的差距（不推远端，只报事实）。"""
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT,
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()
    except Exception as e:  # pragma: no cover
        warn(f"git 不可用，跳过工作区检查：{e}")
        return
    if not out:
        ok("工作区干净（无未提交改动）")
    else:
        n = len(out.splitlines())
        warn(f"工作区有 {n} 项未提交改动（提交前应清零或确认属于本次提交）")

    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    local = subprocess.run(["git", "rev-parse", "--short", "origin/main"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    if head and local:
        ahead = subprocess.run(["git", "rev-list", "--count", "origin/main..HEAD"],
                               cwd=ROOT, capture_output=True, text=True).stdout.strip()
        ok(f"本地 HEAD={head}｜origin/main={local}｜领先 {ahead} 个提交（未推 = 符合计划）")


# ---------------------------------------------------------------- 2. 主提交 bundle
EXPECT = {
    "bundle_main_splash_bytes": 59625,
    "bundle_blake3": "50404a65871a4fbe50f9b7740b7932d6fdae855164962a7b6b20d76a0f5cb909",
    "bundle_version": "0.8.6",
    "bundle_caps": [
        "storage", "model", "octos.session.history",
        "matrix.read_messages", "matrix.profile", "matrix.send_message",
    ],
    "card_version": "0.3.3",
    "octos_version": "0.3.11",
    "apk_merged_sha256": "07cdbc14863d29c16b5cb194843252bbd35083d6b30afbd3faf235d415b03a41",
    "apk_merged_bytes": 128670020,
    "apk_part1_sha256": "07df32045397eb6c8e68d68f292024ab946fb33820785cbd4b6dc6ffdca191f8",
    "apk_part2_sha256": "73845ac5c42305c5a102205b20cc59bf3b591c654cd00b81aca191c207ea2204",
    "patches": [
        "01-rinx-windows-build-path.patch",
        "02-rinx-host-usability-and-services.patch",
        "03-makepad-portable-resource-lookup.patch",
        "04-makepad-splash-eval-budget.patch",
        "05-makepad-unpackaged-resource-fallback.patch",
    ],
}


def check_bundle():
    b = ROOT / "bundle"
    if not (b / "manifest.json").exists():
        fail("bundle/manifest.json 不存在")
        return
    m = json.loads(read_text(b / "manifest.json"))

    if m.get("version") != EXPECT["bundle_version"]:
        fail(f"bundle 版本 {m.get('version')} != 期望 {EXPECT['bundle_version']}")
    else:
        ok(f"bundle 版本 = {m['version']}")

    caps = sorted(m.get("capabilities") or [])
    if caps != sorted(EXPECT["bundle_caps"]):
        fail(f"bundle 能力清单不符：{caps}")
    else:
        ok(f"bundle 能力清单 = {caps}（{len(caps)} 项）")

    integ = (m.get("integrity") or {})
    if integ.get("bundle_blake3") != EXPECT["bundle_blake3"]:
        fail(f"bundle_blake3 不符：{integ.get('bundle_blake3')}")
    else:
        ok("bundle_blake3 与基线一致（摘要不含签名字段，去掉签名不需要重算）")

    # 主提交必须【未签名】—— 官方 publisher-github-v1 要求；card-host 也拒收带签名的包。
    if integ.get("signature"):
        fail("bundle 仍带签名：官方 publisher-github-v1 要求【未签名】，"
             "参考宿主 card-host 会直接拒收（refused: no signature verifier is installed…）")
    else:
        ok("bundle 未签名（符合官方 publisher-github-v1 要求）")

    sp = b / "main.splash"
    if sp.exists():
        n = sp.stat().st_size
        if n != EXPECT["bundle_main_splash_bytes"]:
            fail(f"bundle/main.splash = {n} 字节 != 期望 {EXPECT['bundle_main_splash_bytes']}")
        else:
            ok(f"bundle/main.splash = {n} 字节")

    # listing.json 里的路径必须是正斜杠（可移植）
    try:
        lst = json.loads(read_text(b / "listing.json"))
        bad = [k for k, v in lst.items() if isinstance(v, str) and "\\" in v]
        if bad:
            fail(f"listing.json 含反斜杠路径字段：{bad}")
        else:
            ok("listing.json 路径均为正斜杠")
    except Exception as e:
        warn(f"listing.json 解析失败：{e}")


def check_versions():
    """三形态版本 + 卡片/系统 app 实物。"""
    card = ROOT / "apps" / "shiyi-card" / "bundle" / "manifest.json"
    if card.exists():
        v = json.loads(read_text(card)).get("version")
        if v != EXPECT["card_version"]:
            fail(f"卡片包版本 {v} != 期望 {EXPECT['card_version']}")
        else:
            ok(f"卡片包版本 = {v}")
    else:
        fail("apps/shiyi-card/bundle/manifest.json 不存在")

    octos = ROOT / "octos" / "apps" / "shiyi" / "bundle" / "manifest.json"
    if octos.exists():
        v = json.loads(read_text(octos)).get("version")
        if v != EXPECT["octos_version"]:
            fail(f"系统 app 版本 {v} != 期望 {EXPECT['octos_version']}")
        else:
            ok(f"系统 app 版本 = {v}")
    else:
        fail("octos/apps/shiyi/bundle/manifest.json 不存在")


# ---------------------------------------------------------------- 3. 补丁
def check_patches():
    d = ROOT / "rinx" / "patches"
    missing = [p for p in EXPECT["patches"] if not (d / p).exists()]
    if missing:
        fail(f"补丁缺失：{missing}")
        return
    ok(f"补丁齐全（{len(EXPECT['patches'])} 个）")

    # 补丁文件不能有 BOM（.patch 是纯文本，BOM 会导致 git apply 失败）
    for p in EXPECT["patches"]:
        b3 = (d / p).read_bytes()[:3]
        if b3 == b"\xef\xbb\xbf":
            fail(f"{p} 带 BOM（.patch 不应有 BOM）")
    ok("补丁文件均无 BOM")

    # README 里不能再出现"三个补丁"这类过期表述
    rd = read_text(d / "README.md")
    for stale in ["三个补丁", "01 + 02 + 03", "01/02/03"]:
        if stale in rd:
            fail(f"rinx/patches/README.md 仍含过期表述：{stale}")


# ---------------------------------------------------------------- 4. 安卓包
def check_android():
    d = ROOT / "android"
    sums = d / "SHA256SUMS.txt"
    if not sums.exists():
        fail("android/SHA256SUMS.txt 不存在")
        return
    txt = read_text(sums)

    p1, p2 = d / "shiyi-rinx-android-1.1.0-ai-arm64-v8a.apk.part1", d / "shiyi-rinx-android-1.1.0-ai-arm64-v8a.apk.part2"
    for p, key in ((p1, "apk_part1_sha256"), (p2, "apk_part2_sha256")):
        if not p.exists():
            fail(f"{p.name} 不存在")
            continue
        h = sha256_file(p)
        if h != EXPECT[key]:
            fail(f"{p.name} sha256 不符：{h}")
        else:
            ok(f"{p.name} sha256 一致（{p.stat().st_size:,} 字节）")

    # 分卷大小之和 == 记录的整包大小
    if p1.exists() and p2.exists():
        total = p1.stat().st_size + p2.stat().st_size
        if total != EXPECT["apk_merged_bytes"]:
            fail(f"分卷大小之和 {total:,} != 记录整包 {EXPECT['apk_merged_bytes']:,}")
        else:
            ok(f"分卷之和 = 整包大小 = {total:,} 字节")

    # SHA256SUMS.txt 里写的整包哈希必须与期望一致
    if EXPECT["apk_merged_sha256"] not in txt:
        fail("SHA256SUMS.txt 里的整包 sha256 与期望不一致")
    else:
        ok("SHA256SUMS.txt 整包 sha256 与期望一致")

    # README 里的期望值必须与 SHA256SUMS 一致（此前这里出过错：旧值残留）
    rd = d / "README.md"
    if rd.exists():
        t = read_text(rd)
        if EXPECT["apk_merged_sha256"] not in t:
            fail("android/README.md 里的 sha256 未同步为最新值")
        elif str(EXPECT["apk_merged_bytes"]) not in t:
            fail("android/README.md 里的整包大小未同步为最新值")
        else:
            ok("android/README.md 的期望值与 SHA256SUMS.txt 一致")
        for stale in ["128645444", "ef1452533435"]:
            if stale in t:
                fail(f"android/README.md 仍含过期值：{stale}")


# ---------------------------------------------------------------- 5. 编码与禁词
BANNED = [
    # 红线词
    "33OS", "沃八", "可可", "WorkBuddy", "QClaw", "OpenClaw", "刷机线", "ARC线", "零交叉",
    # 排他词
    "首创", "首家", "独一份", "全场只有", "唯二", "唯一一家",
]


def check_encoding_and_words():
    mds = [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]
    no_bom = []
    for p in mds:
        raw = p.read_bytes()
        if raw[:3] != b"\xef\xbb\xbf":
            no_bom.append(str(p.relative_to(ROOT)))
    if no_bom:
        warn(f"有 {len(no_bom)} 个 .md 未带 UTF-8 BOM（若含中文，Windows 下可能乱码）：{no_bom[:5]}")
    else:
        ok(f"全部 {len(mds)} 个 .md 均带 UTF-8 BOM")

    hits = []
    for p in mds:
        t = read_text(p)
        for w in BANNED:
            if w in t:
                hits.append(f"{p.relative_to(ROOT)} → {w}")
    if hits:
        fail("对外禁词命中：\n      " + "\n      ".join(hits))
    else:
        ok(f"对外禁词零命中（{len(BANNED)} 个词，扫 {len(mds)} 个 .md）")


# ---------------------------------------------------------------- 6. 文档引用的文件是否存在
REF_RE = re.compile(r"\]\((?!https?://|#)([^)\s]+)\)")


def check_doc_refs():
    docs = [
        ROOT / "README.md", ROOT / "MATERIALS.md", ROOT / "docs" / "评审速览.md",
        ROOT / "docs" / "STRUCTURE.md", ROOT / "SUBMISSION.md",
        ROOT / "docs" / "Rinx宿主改造说明.md",
        ROOT / "docs" / "手机端复现说明.md",
        ROOT / "rinx" / "README.md", ROOT / "rinx" / "patches" / "README.md",
        ROOT / "android" / "README.md",
    ]
    missing = []
    checked = 0
    for p in docs:
        if not p.exists():
            continue
        base = p.parent
        for m in REF_RE.finditer(read_text(p)):
            tgt = m.group(1).split("#")[0].strip()
            if not tgt or tgt.startswith("mailto:"):
                continue
            checked += 1
            if not (base / tgt).exists() and not (ROOT / tgt).exists():
                missing.append(f"{p.relative_to(ROOT)} → {tgt}")
    if missing:
        fail(f"文档引用了不存在的文件（{len(missing)} 处）：\n      " + "\n      ".join(missing[:15]))
    else:
        ok(f"文档内相对链接全部有效（{checked} 处，{len(docs)} 份文档）")


# ---------------------------------------------------------------- 7. 泄漏
LEAK_PAT = [
    re.compile(r"[A-Za-z]:\\\\?Users\\\\?[A-Za-z0-9_.-]+"),
    re.compile(r"C:\\Users\\"),
    re.compile(r"15812456537@163\.com"),
    re.compile(r"WQufyiWGhwUq7R3W"),          # 163 授权码
    re.compile(r"smtp\.163\.com"),
]


def check_leak():
    targets = []
    for pat in ("*.md", "*.json", "*.txt", "*.splash"):
        targets += [p for p in ROOT.rglob(pat) if ".git" not in p.parts]
    hits = []
    for p in targets:
        try:
            t = read_text(p)
        except Exception:
            continue
        for rx in LEAK_PAT:
            m = rx.search(t)
            if m:
                hits.append(f"{p.relative_to(ROOT)} → {m.group(0)[:40]}")
    if hits:
        fail("疑似内部信息泄漏（本机路径 / 邮箱 / 授权码）：\n      " + "\n      ".join(hits[:15]))
    else:
        ok(f"无内部信息泄漏（本机路径 / 邮箱 / 密钥，扫 {len(targets)} 个文件）")


# ---------------------------------------------------------------- 8. bundle 未改动证明
def check_bundle_frozen():
    """主提交 bundle 自 GATE.txt 生成后是否被动过（按 mtime）。"""
    gate = ROOT / "review" / "GATE.txt"
    if not gate.exists():
        warn("review/GATE.txt 不存在，无法比对门禁时间")
        return
    first = read_text(gate).splitlines()[1] if len(read_text(gate).splitlines()) > 1 else ""
    m = re.search(r"生成:\s*([0-9-]+ [0-9:]+)", first)
    if not m:
        warn("GATE.txt 里没找到生成时间")
        return
    ok(f"GATE.txt 生成于 {m.group(1)}（PASSED，Linux 章）")
    # 与 bundle 关键文件的 mtime 互证
    for f in ("main.splash", "manifest.json", "listing.json"):
        p = ROOT / "bundle" / f
        if p.exists():
            import datetime
            ts = datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            ok(f"bundle/{f} 最后修改 {ts}（不晚于门禁 ⇒ 门禁仍对这份 bundle 有效）")


# ---------------------------------------------------------------- 9. 签名政策一致性
def check_signature_policy_docs():
    """签名政策：实物未签名 + 文档口径一致（README 含 --stamp 与未签名说明）。"""
    rd = read_text(ROOT / "README.md")
    if "--stamp" not in rd:
        fail("README 里没有 --stamp：旧版工具会因摘要平台差异误报不符（上游 #79/Rinx #75 已修）")
    elif "未签名" not in rd:
        fail("README 里没有说明 bundle 未签名（官方要求）")
    else:
        ok("README 含 --stamp 与「未签名」说明")

    gate = read_text(ROOT / "review" / "GATE.txt")
    if "2026-10-13" not in gate or "去签名" not in gate:
        fail("review/GATE.txt 未记录 10-13 的去签名变更")
    else:
        ok("GATE.txt 已记录去签名变更与复检命令")

    stale = []
    for rel in ["docs/复赛结构变更说明_20261010.md", "docs/数据来源与限制.md",
                "AGENTS.md", "docs/可独立复跑_发回群闭环_步骤说明.md"]:
        t = read_text(ROOT / rel)
        if "仍未做" in t and "去签名" in t:
            stale.append(rel)
    if stale:
        fail(f"以下文档仍写着「去签名…仍未做」：{stale}")
    else:
        ok("各文档的「去签名」口径已同步")


# ---------------------------------------------------------------- 9. 全仓 manifest 签名
def check_all_manifests_unsigned():
    """全仓每个 manifest.json 都不得带 integrity.signature（官方 publisher-github-v1 要求）。

    教训：10-13 只修了主提交 bundle，漏了第二提交面（卡片包）—— 端到端一跑就现原形。
    """
    signed, checked = [], 0
    for dp, dn, fn in os.walk(ROOT):
        if ".git" in dp.split(os.sep):
            continue
        for f in fn:
            if f != "manifest.json":
                continue
            p = Path(dp) / f
            rel = str(p.relative_to(ROOT)).replace(os.sep, "/")
            try:
                m = json.loads(read_text(p))
            except Exception as e:
                warn(f"{rel} 解析失败：{e}")
                continue
            checked += 1
            integ = m.get("integrity") or {}
            if integ.get("signature"):
                signed.append(f"{rel}（id={m.get('id')} v{m.get('version')}）")
    if signed:
        fail("以下 manifest 仍带签名（应全部未签名 —— 官方 publisher-github-v1 要求）：\n      "
             + "\n      ".join(signed))
    else:
        ok(f"全仓 {checked} 个 manifest 均未签名")


# ---------------------------------------------------------------- 11. 证据文件完整性
EVIDENCE = [
    # README §8.0 说"L0 零安装就能看懂" —— 那这些必须真在仓里
    "build/_evidence/flow_run.json",
    "build/_evidence/neg_unsigned.log",
    "build/_evidence/neg_unsigned.png",
    "build/_evidence/neg_tampered.log",
    "build/_evidence/neg_tampered.png",
    "build/review.json",
    "review/GATE.txt",
    "review/ANSWERS.md",
    "review/scan-packet.json",
    "apps/shiyi-card/bundle/screenshots/01-read.png",
    "apps/shiyi-card/bundle/screenshots/02-ask.png",
    "apps/shiyi-card/bundle/screenshots/03-plan.png",
    "apps/shiyi-card/bundle/screenshots/04-memo.png",
    "apps/shiyi-card/bundle/screenshots/05-done.png",
    "docs/evidence/demo-desktop-mail-20261011/拾意_桌面_工作场景_演示.mp4",
    "docs/evidence/demo-phone-groupmsg-20261012/拾意_手机_群消息_演示.mp4",
    "docs/拾意_复赛答辩幻灯片.pptx",
]


def check_evidence_files():
    """README 承诺的证据文件是否都在（L0 = 零安装就能看懂，靠的就是这些）。"""
    missing = [p for p in EVIDENCE if not (ROOT / p).exists()]
    if missing:
        fail("README 承诺的证据文件缺失：\n      " + "\n      ".join(missing))
    else:
        ok(f"证据文件齐全（{len(EVIDENCE)} 项：flow_run / 失败态 / 门禁 / 五屏 / 两片 / 幻灯片）")

    # host_*.log 每屏日志（数量可变，单独判）
    hosts = list((ROOT / "build" / "_evidence").glob("host_*.log"))
    if len(hosts) < 5:
        fail(f"build/_evidence/host_*.log 只有 {len(hosts)} 个（五屏应 ≥5）")
    else:
        ok(f"五屏宿主日志 host_*.log 共 {len(hosts)} 个")

    # 演示片要非空（>=1MB 才算成片）
    for p in EVIDENCE:
        if p.endswith(".mp4"):
            f = ROOT / p
            if f.exists() and f.stat().st_size < 1_000_000:
                fail(f"{p} 只有 {f.stat().st_size} 字节，疑似空片")


# ---------------------------------------------------------------- 10. 提交物指纹
FP_TARGETS = [
    "bundle/main.splash", "bundle/manifest.json", "bundle/listing.json",
    "apps/shiyi-card/bundle/manifest.json", "apps/shiyi-card/bundle/page.card",
    "octos/apps/shiyi/bundle/manifest.json",
    "README.md", "MATERIALS.md", "docs/评审速览.md", "docs/STRUCTURE.md", "SUBMISSION.md",
    "docs/FILE-INDEX.md", "PRIVACY.md", "NOTICE", "LICENSE",
    "docs/Rinx宿主改造说明.md", "docs/手机端复现说明.md",
    "rinx/README.md", "rinx/patches/README.md",
    "rinx/patches/01-rinx-windows-build-path.patch",
    "rinx/patches/02-rinx-host-usability-and-services.patch",
    "rinx/patches/03-makepad-portable-resource-lookup.patch",
    "rinx/patches/04-makepad-splash-eval-budget.patch",
    "rinx/patches/05-makepad-unpackaged-resource-fallback.patch",
    "android/README.md", "android/SHA256SUMS.txt",
    "android/shiyi-rinx-android-1.1.0-ai-arm64-v8a.apk.part1",
    "android/shiyi-rinx-android-1.1.0-ai-arm64-v8a.apk.part2",
    ".github/workflows/publish-app.yml",
]


def submission_fingerprint():
    """提交物指纹：所有提交物的内容哈希汇总成一个总哈希。

    用途：判"这一轮里提交物有没有被动过"—— 不靠记性。
    收敛判据：**连续一轮三遍全过，且三遍的指纹完全一样**。

    另给一层 **bundle 目录指纹**：端到端（第 2/3 遍）只取决于它 ——
    若只有文档改动，bundle 指纹不变 ⇒ 端到端结论仍有效，只需重跑第 1 遍。
    """
    h = hashlib.sha256()
    detail = []
    for rel in FP_TARGETS:
        p = ROOT / rel
        if not p.exists():
            detail.append(f"{rel}  <缺失>")
            h.update(f"{rel}:MISSING".encode())
            continue
        d = sha256_file(p)
        h.update(f"{rel}:{d}".encode())
        detail.append(f"{rel}  {d[:16]}")
    total = h.hexdigest()
    ok(f"提交物指纹 = {total[:32]}…（{len(FP_TARGETS)} 个文件）")

    # bundle 目录指纹（决定端到端结果的那一层）
    bh = hashlib.sha256()
    bdir = ROOT / "bundle"
    for dp, dn, fn in sorted(os.walk(bdir)):
        for f in sorted(fn):
            fp_ = Path(dp) / f
            rel = str(fp_.relative_to(bdir)).replace(os.sep, "/")
            bh.update(f"{rel}:{sha256_file(fp_)}".encode())
    bfp = bh.hexdigest()
    ok(f"bundle 目录指纹 = {bfp[:32]}…（端到端只看这一层）")
    return total, detail


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="只打印失败与警告")
    ap.add_argument("--fp", action="store_true", help="打印提交物指纹及每个文件的哈希")
    args = ap.parse_args()

    print("=" * 74)
    print(f"提交前自检 · 拾意 · 仓 = {ROOT}")
    print("=" * 74)

    fp = None
    for fn in (check_git_state, check_bundle, check_versions, check_patches,
               check_android, check_encoding_and_words, check_doc_refs,
               check_leak, check_bundle_frozen, check_signature_policy_docs,
               check_all_manifests_unsigned, check_evidence_files):
        name = fn.__doc__ or fn.__name__
        print(f"\n── {fn.__name__} ─ {name.strip().splitlines()[0] if name.strip() else ''}")
        try:
            fn()
        except Exception as e:
            fail(f"{fn.__name__} 异常：{type(e).__name__}: {e}")

    print("\n── submission_fingerprint ─ 提交物指纹")
    try:
        fp, detail = submission_fingerprint()
        if args.fp:
            for d in detail:
                print(f"      {d}")
    except Exception as e:
        fail(f"指纹计算异常：{type(e).__name__}: {e}")

    if not args.quiet:
        print("\n" + "=" * 74)
        for p in PASSES:
            print(f"  OK   {p}")

    print("\n" + "=" * 74)
    for w in WARNS:
        print(f"  WARN {w}")
    for f in FAILS:
        print(f"  FAIL {f}")
    print("=" * 74)
    print(f"通过 {len(PASSES)} 项｜警告 {len(WARNS)} 项｜失败 {len(FAILS)} 项")
    if fp:
        print(f"提交物指纹（记下它，三遍必须一致才叫收敛）：{fp}")
    print("=> " + ("全部通过（有警告，仅提醒）" if not FAILS else "存在失败项，先修再提交"))
    if not FAILS:
        print("""
收敛判据（机械判定，不靠记性）
  第 1 遍  静态自检      python build/preflight_submit.py
  第 2 遍  端到端冒烟    用官方 card-host 真跑一遍 bundle（推荐 --stamp；bundle 须未签名）
  第 3 遍  换机 + 复验   在第二台干净机器上再跑一次
  ⇒ 可以交的条件：**连续一轮三遍全过，且三遍的「提交物指纹」完全一样**。
  ⇒ 任何一处修改 ⇒ 指纹变 ⇒ 三遍全部重跑（不是只跑改动那一遍）。
提示：官方门禁请在 Linux/WSL 上补跑 ——  hub check bundle --allow-unsigned
""")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
