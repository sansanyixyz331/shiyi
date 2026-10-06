#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成器干活录屏 —— 从一句话到出卡（真跑真录，不是动画）。

屏幕上出现的每一行输出、每一张卡，都是**这一次真跑出来的**：

  1. `gen_l0.py --model` 真跑一遍，抓它**真实的 stdout** 当画面；
  2. 产出的卡用宿主**真抓一帧**（shot_bundle）；
  3. 同一条消息再用**规则路**跑一遍，做「规则 vs 模型」对照；
  4. 所有画面按顺序拼成 mp4。

依赖：标准库 + ffmpeg（本机 winget 装的 Gyan.FFmpeg）。

    python build/record_generator.py
"""

import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "_gen_video")
FRAMES = os.path.join(OUT, "frames")
RUN = os.path.join(OUT, "run")
MP4 = os.path.join(OUT, "generator-at-work.mp4")
FPS = 10
W, H = 515, 1115
FONT_SRC = r"C:\Windows\Fonts\msyh.ttc"
FONT_DST = os.path.join(OUT, "msyh.ttc")
BG = "0x0E1418"
TEXT = "下个月初得去趟慕尼黑看展会"


def find_ffmpeg():
    for pat in (r"C:\Users\adves\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg*\**\bin\ffmpeg.exe",):
        hits = glob.glob(pat, recursive=True)
        if hits:
            return sorted(hits)[-1]
    return shutil.which("ffmpeg")


def esc(s):
    """ffmpeg filter 内的转义（撇号换排版撇号，避开单引号串的坑）。"""
    return (s.replace("\\", "\\\\")
             .replace("'", "\u2019")
             .replace(":", "\\:")
             .replace(",", "\\,")
             .replace("%", "\\%"))


_ff = None


def frame(dst, lines, bg=BG, align="left", x=42, y0=120, dy=40):
    """生成一张 PNG 画面。lines = [text | (text, size, color)]，按行排。"""
    global _ff
    _ff = _ff or find_ffmpeg()
    if not _ff:
        raise RuntimeError("找不到 ffmpeg")
    shutil.copy2(FONT_SRC, FONT_DST)
    parts = []
    y = y0
    for ln in lines:
        if isinstance(ln, str):
            text, size, color = ln, 26, "white"
        else:
            text, size, color = ln
        pos = "(w-text_w)/2" if align == "center" else str(x)
        if text:
            parts.append("drawtext=fontfile=msyh.ttc:text='%s':fontsize=%d:fontcolor=%s"
                         ":x=%s:y=%d" % (esc(text), size, color, pos, y))
        y += dy if align != "center" else max(dy, size + 14)
    cmd = [_ff, "-y", "-f", "lavfi", "-i", "color=c=%s:s=%dx%d" % (bg, W, H),
           "-frames:v", "1", "-vf", ",".join(parts) if parts else "null", dst]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=OUT)
    if r.returncode != 0:
        raise RuntimeError("画面渲染失败：\n%s" % (r.stderr or "")[-400:])


def emit(n, src_png, seconds):
    for _ in range(n, n + max(1, int(round(seconds * FPS)))):
        shutil.copy2(src_png, os.path.join(FRAMES, "%05d.png" % _))
    return n + max(1, int(round(seconds * FPS)))


def run_gen(text, outdir, model):
    cmd = [sys.executable, os.path.join(HERE, "gen_l0.py"), "--text", text, "--out", outdir]
    if model:
        cmd.append("--model")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return ((r.stdout or "") + (r.stderr or "")).strip()


def shot(bundle):
    subprocess.run([sys.executable, os.path.join(HERE, "shot_bundle.py"), bundle],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
    p = os.path.join(bundle, "screenshots", "01.png")
    return p if os.path.isfile(p) else None


def main():
    for d in (OUT, FRAMES, RUN):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)

    tmp = os.path.join(RUN, "tmp")
    os.makedirs(tmp, exist_ok=True)

    # 同一句话，两条识别路（模型 / 规则）—— 真跑
    print("[1/3] 一句话 → 一张卡（真跑 · 模型路）…")
    out_mdl = run_gen(TEXT, os.path.join(tmp, "mdl"), model=True)
    print(out_mdl)
    out_rule = run_gen(TEXT, os.path.join(tmp, "rule"), model=False)
    face_mdl = shot(os.path.join(tmp, "mdl", "card", "bundle"))
    face_rule = shot(os.path.join(tmp, "rule", "card", "bundle"))

    # 五种场景 → 五张形态不同的卡（真跑真抓）
    print("[2/3] 五种场景 → 五种卡型（真跑真抓）…")
    kinds = [("出行", "下周三我得去趟深圳"),
             ("会面", "明天下午三点跟老王在杭州碰一下"),
             ("代办", "帮我把那个快递寄到上海"),
             ("采买", "周末去买台新显示器"),
             ("提醒", "下周二记得交房租")]
    faces = []
    for label, msg in kinds:
        d = os.path.join(tmp, "k_" + label)
        run_gen(msg, d, model=False)
        p = shot(os.path.join(d, "card", "bundle"))
        if p:
            faces.append((label, msg, p))
        print("    %-4s %s" % (label, msg))

    print("[3/3] 拼帧 …")
    buf = 0
    intro = os.path.join(OUT, "_intro.png")
    frame(intro, [("造 App 的机器", 46, "white"),
                  ("一条消息  →  一张卡", 24, "0x7FD1B9"),
                  ("（真跑：识别 → 生成 → 自评 → 渲染 → 官方门禁）", 17, "0x9AA5B1")],
          align="center", y0=430, dy=76)
    buf = emit(buf, intro, 5.0)

    inp = os.path.join(OUT, "_input.png")
    frame(inp, [("消息", 20, "0x9AA5B1"), ("「%s」" % TEXT, 30, "white")],
          align="center", y0=470, dy=70)
    buf = emit(buf, inp, 4.0)

    term = os.path.join(OUT, "_term.png")
    lines = [("$ python build/gen_l0.py --model", 20, "0x7FD1B9")]
    for ln in out_mdl.splitlines():
        lines.append((ln, 20, "white" if ln.startswith("[PASS]") else "0xC9D1D9"))
    frame(term, lines, y0=300, dy=44)
    buf = emit(buf, term, 4.0 + 0.9 * len(lines))

    if face_mdl:
        buf = emit(buf, face_mdl, 7.0)

    if face_rule:
        cap = os.path.join(OUT, "_cmp.png")
        frame(cap, [("同一条消息 · 规则路（对照）", 22, "0x9AA5B1"),
                    ("它认不出地点与时间 → 卡上缺行、还要反问", 18, "0xC9D1D9")],
              align="center", y0=430, dy=60)
        buf = emit(buf, cap, 3.5)
        buf = emit(buf, face_rule, 7.0)

    # 换场景 → 换卡型
    cap2 = os.path.join(OUT, "_cap_kinds.png")
    frame(cap2, [("换个场景，换张卡", 30, "white"),
                 ("出行 / 会面 / 代办 / 采买 / 提醒 —— 各长各的样", 18, "0x9AA5B1"),
                 ("题头、行标签、动作，都随场景走", 16, "0x7FD1B9")],
          align="center", y0=452, dy=66)
    buf = emit(buf, cap2, 4.5)
    for label, msg, p in faces:
        ttl = os.path.join(OUT, "_k_%s.png" % label)
        frame(ttl, [("「%s」" % msg, 22, "0xC9D1D9"), ("→ %s卡" % label, 26, "0x7FD1B9")],
              align="center", y0=470, dy=58)
        buf = emit(buf, ttl, 2.0)
        buf = emit(buf, p, 5.0)

    gate = os.path.join(OUT, "_gate.png")
    frame(gate, [("官方门禁", 20, "0x9AA5B1"),
                 ("hub check  →  PASSED", 40, "0x7FD1B9"),
                 ("shiyi-gen 0.2.0 — PASSED", 18, "white")],
          align="center", y0=440, dy=72)
    buf = emit(buf, gate, 5.0)

    outro = os.path.join(OUT, "_outro.png")
    frame(outro, [("对手在写卡。", 28, "white"),
                  ("我们造一台造卡的机器。", 28, "0x7FD1B9")],
          align="center", y0=500, dy=70)
    buf = emit(buf, outro, 5.0)

    print("帧数：%d（%.1f 秒）" % (buf, buf / float(FPS)))
    ff = find_ffmpeg()
    r = subprocess.run([ff, "-y", "-framerate", str(FPS), "-i",
                        os.path.join(FRAMES, "%05d.png"),
                        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                        "-movflags", "+faststart", MP4],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("合成失败：\n%s" % (r.stderr or "")[-600:])
    print("成片：%s（%d bytes）" % (MP4, os.path.getsize(MP4)))


if __name__ == "__main__":
    sys.exit(main())
