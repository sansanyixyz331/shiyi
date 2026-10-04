#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拾意 · 视觉自评 —— 让生成器"看"自己渲染出来的那一帧。

几何自评（gen_l0.selfcheck）是在"还没画"时算坐标；这里是在"已经画完"之后，
真去数像素：内容有没有贴到画布边上（等于被裁）、有没有挤进底部动作带、
底部该留的白留了没有。两者合起来，才是"看自己的结果并改进"。

实现：用 WSL 里的 ImageMagick 取**逐行 / 逐列灰度剖面**
（`convert P -resize 1xH! txt:-`），解析每一行/列的平均灰度，
把明显暗于背景的行判为"有内容的行"。不依赖任何第三方 Python 库。

    python build/visual_review.py <bundle_dir>      # 读 bundle/screenshots/01.png

判据（比例法，不依赖绝对像素 —— host 渲染尺寸与本机坐标并不一一对应，
所以"内容挤没挤到动作带"交给几何自评，这里只管**渲染结果本身对不对**）：
  · ink-at-bottom-edge : 画布最底几行还有内容 => 内容溢出 / 被裁
  · ink-at-right-edge  : 画布最右几列还有内容 => 右侧溢出 / 被裁
  · ink-at-left-edge   : 画布最左几列还有内容 => 左侧溢出 / 被裁
  · action-band-missing: 底部 12% 里没有任何内容块 => 动作按钮没画出来
  · too-sparse         : 内容块太少/太矮 => 画布近乎空白（渲染失败或元素丢失）
"""

import os
import re
import subprocess
import sys

WSL = ["wsl.exe", "-d", "Ubuntu-24.04", "-e", "bash", "-lc"]
INK_DROP = 25          # 灰度低于背景这么多，算"有内容"
BAND_RATIO = 0.82      # 卡内动作带顶 ≈ 740/892
BOTTOM_GAP_RATIO = 0.04


def _to_mnt(path):
    p = os.path.abspath(path).replace("\\", "/")
    return "/mnt/%s%s" % (p[0].lower(), p[2:])


def _profile(png, w, h, axis):
    """返回逐行（或逐列）的平均灰度列表。"""
    size = ("1x%d!" % h) if axis == "rows" else ("%dx1!" % w)
    cmd = "convert %s -colorspace Gray -resize %s txt:- 2>/dev/null" % (_to_mnt(png), size)
    r = subprocess.run(WSL + [cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    vals = []
    for line in (r.stdout or "").splitlines():
        m = re.match(r"\d+,\d+:\s*\(([0-9.]+)", line)
        if m:
            vals.append(float(m.group(1)))
    return vals


def _blocks(vals, bg):
    """把"有内容的行"合并成块 [(start, end), …]。"""
    ink = [v < bg - INK_DROP for v in vals]
    blocks, cur = [], None
    gap = 0
    for i, on in enumerate(ink):
        if on:
            cur = i if cur is None else cur
            gap = 0
        elif cur is not None:
            gap += 1
            if gap >= 6:                      # 空 6 行以上才断块
                blocks.append((cur, i - gap))
                cur = None
    if cur is not None:
        blocks.append((cur, len(vals) - 1))
    return [b for b in blocks if b[1] - b[0] >= 1]


def _last_cols_ink(vals, bg, n=2):
    return any(v < bg - INK_DROP for v in vals[-n:])


def _first_cols_ink(vals, bg, n=2):
    return any(v < bg - INK_DROP for v in vals[:n])


def analyze(png):
    """返回 (h, w, issues, debug)。"""
    out = subprocess.run(WSL + ["identify -format '%w %h' " + _to_mnt(png)],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    w, h = [int(x) for x in (out.stdout or "").split()[:2]]
    rows = _profile(png, w, h, "rows")
    cols = _profile(png, w, h, "cols")
    if len(rows) != h:
        rows = (rows + [255.0] * h)[:h]
    if len(cols) != w:
        cols = (cols + [255.0] * w)[:w]

    bg = max(max(rows), max(cols))
    issues = []
    if _last_cols_ink(rows, bg):
        issues.append({"kind": "ink-at-bottom-edge", "severity": "high",
                       "note": "bottom rows carry ink — content overflows or is cropped"})
    if _last_cols_ink(cols, bg):
        issues.append({"kind": "ink-at-right-edge", "severity": "high",
                       "note": "rightmost columns carry ink — cropped on the right"})
    if _first_cols_ink(cols, bg):
        issues.append({"kind": "ink-at-left-edge", "severity": "high",
                       "note": "leftmost columns carry ink — cropped on the left"})

    blk = _blocks(rows, bg)
    covered = sum(b - a + 1 for a, b in blk)
    # 底部 12% 应至少有内容块（动作按钮）
    band_y = h * 0.88
    if not any(a >= band_y for a, b in blk):
        issues.append({"kind": "action-band-missing", "severity": "high",
                       "note": "no content block in the bottom 12% — action band did not render"})
    # 近乎空白 = 渲染失败或元素丢失
    if len(blk) < 3 or covered / float(h) < 0.08:
        issues.append({"kind": "too-sparse", "severity": "medium",
                       "blocks": len(blk), "coverage": round(covered / float(h), 3),
                       "note": "very little ink — layout failed or nodes went missing"})

    debug = {"size": [w, h], "bg": bg, "blocks": blk, "n_blocks": len(blk),
             "coverage": round(covered / float(h), 3)}
    return h, w, issues, debug


def review_bundle(bundle_dir):
    png = os.path.join(bundle_dir, "screenshots", "01.png")
    if not os.path.isfile(png):
        return {"kind": "no-screenshot", "issues": [], "debug": {}}
    try:
        h, w, issues, debug = analyze(png)
    except Exception as e:  # noqa: BLE001
        return {"kind": "error", "error": str(e), "issues": [], "debug": {}}
    return {"issues": issues, "debug": debug}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python build/visual_review.py <bundle_dir>")
        sys.exit(2)
    import json
    print(json.dumps(review_bundle(os.path.abspath(sys.argv[1])), ensure_ascii=False, indent=2))
