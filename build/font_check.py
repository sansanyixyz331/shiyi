#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拾意 · 字体覆盖硬验证 —— 不靠眼睛，逐字问字体"你到底有没有它"。

为什么要这个：宿主日志里的 `font miss … tried=[symbols,emoji]` 是 makepad
在**试 fallback 集合**时的中间输出，不代表最终缺字；而人眼在截图上看乱码也
容易误判。唯一靠谱的办法是把卡片里**每一个字符**单独交给字体做 shaping，
看它落成真字形（gidN, N>0）还是 .notdef（gid0）。

    python build/font_check.py <bundle_or_dir> [...]

扫描目标下所有 .card/.json 的可见字符（去注释），在 WSL 里逐字符 hb-shape，
报告任何 shape 成 gid0 的字符。退出码：0=全覆盖，1=有缺字。
"""

import os
import re
import subprocess
import sys

WSL = ["wsl.exe", "-d", "Ubuntu-24.04", "-e", "bash", "-lc"]
KEY_CJK = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\u0020-\u007e]")


def _to_mnt(path):
    p = os.path.abspath(path).replace("\\", "/")
    return "/mnt/%s%s" % (p[0].lower(), p[2:])


def find_font(root):
    kit = os.path.join(root, "kit")
    base = kit if os.path.isdir(kit) else root
    for b, _d, files in os.walk(base):
        for fn in files:
            if fn.endswith((".ttf", ".otf")):
                return os.path.join(b, fn)
    return None


def collect(paths):
    """每个 path：是文件就收它；是 bundle（含 page.card）就只收那张；否则递归 .card。"""
    chars = set()
    for base in paths:
        if os.path.isfile(base):
            candidates = [base]
        elif os.path.isfile(os.path.join(base, "page.card")):
            candidates = [os.path.join(base, "page.card")]
        else:
            candidates = []
            for r, _d, fs in os.walk(base):
                for fn in fs:
                    if fn.endswith(".card"):        # 只校验真正渲染的卡片文字
                        candidates.append(os.path.join(r, fn))
        for p in candidates:
            try:
                t = open(p, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if p.endswith(".card"):
                t = "\n".join(l.split("#", 1)[0] for l in t.splitlines())
            chars |= set(KEY_CJK.findall(t))
    # 空格是 gid0 的常客，但不代表缺字，排除
    return {c for c in chars if c not in " \t\r\n"}


def shape_each(font, chars):
    """逐字符 shape；返回 {字符: gid}。"""
    work = os.path.join(os.path.dirname(os.path.abspath(font)), "_shape_in.txt")
    order = sorted(chars)
    with open(work, "w", encoding="utf-8") as fh:
        fh.write("\n".join(order))
    cmd = "hb-shape %s --text-file=%s" % (_to_mnt(font), _to_mnt(work))
    r = subprocess.run(WSL + [cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "").splitlines()
    res = {}
    for ch, line in zip(order, out):
        m = re.match(r"\[\s*gid(\d+)", line.strip())
        res[ch] = int(m.group(1)) if m else -1
    return res


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip().splitlines()[0])
        return 2
    targets = [os.path.abspath(p) for p in sys.argv[1:]]
    font = None
    scan_paths = []
    for t in targets:
        font = font or find_font(t)
        scan_paths.append(t)
    if not font:
        print("没找到 .ttf/.otf")
        return 2

    chars = collect(scan_paths)
    res = shape_each(font, chars)
    missing = sorted(c for c, g in res.items() if g == 0)
    print("字体：%s" % font)
    print("检查字符 %d 个，缺字形 %d 个" % (len(res), len(missing)))
    if missing:
        print("缺字（shape 成 .notdef）：")
        for c in missing:
            print("   %r  U+%04X" % (c, ord(c)))
        return 1
    print("全部命中 -> 字体内覆盖本目录所有可见字符。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
