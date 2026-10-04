#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拾意 · 字体子集生成 —— 让字体跟着**内容**走。

踩过的坑（2026-10-04）：生成器产出的卡用了新文字，却复用了主 bundle 里那份
"按固定字符集做的字体子集"。缺的字（尤其是全角标点 `，（）:`）渲染不出来 —
宿主日志里就是一行行 `font miss`，画面上就是乱码/方框。

所以：**每产出一批卡，就按这批卡真正用到的字符重做一次子集**。
源字体是 makepad 自带、和 Inter.ttf 同一目录的中文楷体（19MB），子集后几十 KB。

    python build/make_font.py --bundle <bundle_dir> [--scan <dir_or_file> ...]

默认扫 bundle 的**父目录整棵树**（含同级的 cards/），把用到的汉字+全角标点
收集起来，用 WSL 里的 hb-subset 生成 <bundle>/kit/native/light/fonts/shiyi.ttf。
"""

import argparse
import os
import re
import subprocess
import sys

WSL = ["wsl.exe", "-d", "Ubuntu-24.04", "-e", "bash", "-lc"]
SRC_FONT = "$HOME/gosim_check/makepad/widgets/resources/LXGWWenKaiRegular.ttf"
CJK = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\u0020-\u007e]")
ASCII_ALL = "".join(chr(c) for c in range(0x20, 0x7F))   # 可打印 ASCII 全带上


def _to_mnt(path):
    p = os.path.abspath(path).replace("\\", "/")
    return "/mnt/%s%s" % (p[0].lower(), p[2:])


def collect(paths, extra_text=""):
    chars = set(extra_text)
    for base in paths:
        for root, _dirs, files in os.walk(base):
            for fn in files:
                if not fn.endswith((".card", ".json")):
                    continue
                try:
                    t = open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read()
                except OSError:
                    continue
                if fn.endswith(".card"):                       # 去掉注释再扫
                    t = "\n".join(l.split("#", 1)[0] for l in t.splitlines())
                chars |= set(CJK.findall(t))
    return chars


FULLWIDTH_FALLBACK = "，。、；：？！（）【】《》“”‘’—…·"


def build(bundle, scans=None, text=""):
    """按 bundle（含 scans 里的字符）重做字体子集。返回 (ok, message)。"""
    bundle = os.path.abspath(bundle)
    scans = scans or [os.path.dirname(bundle)]
    chars = collect(scans, text) | set(FULLWIDTH_FALLBACK) | set(ASCII_ALL)
    if len(chars) < 5:
        return False, "收集到的字符太少（%d），疑似没扫对目录" % len(chars)

    cf = os.path.join(os.path.dirname(bundle), "_font_chars.txt")
    with open(cf, "w", encoding="utf-8") as fh:
        fh.write("".join(sorted(chars)))

    out = os.path.join(bundle, "kit", "native", "light", "fonts", "shiyi.ttf")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = ("hb-subset %s --text-file=%s --output-file=%s" %
           (SRC_FONT, _to_mnt(cf), _to_mnt(out)))
    r = subprocess.run(WSL + [cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0 or not os.path.isfile(out):
        return False, "hb-subset 失败：%s %s" % (r.stdout, r.stderr)
    chk = subprocess.run(WSL + ["python3 -c \"from fontTools.ttLib import TTFont as T;"
                                "print(len(T('%s').getBestCmap()))\"" % _to_mnt(out)],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    covered = (chk.stdout or "?").strip()
    return True, "字符 %d 个 -> 子集字体 %d 字节（覆盖 %s 个码点）" % (
        len(chars), os.path.getsize(out), covered)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True, help="字体放这里的 kit/...")
    ap.add_argument("--scan", nargs="*", help="要收集字符的目录/文件；缺省= bundle 父目录")
    ap.add_argument("--text", default="", help="额外强制包含的字符")
    args = ap.parse_args()
    ok, msg = build(args.bundle, args.scan, args.text)
    print(msg)
    return 0 if ok else (2 if "太少" in msg else 1)


if __name__ == "__main__":
    sys.exit(main())
