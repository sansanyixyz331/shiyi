#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拾意 · 演示片旁白（TTS + 混流）

给主演示片 `build/_video/shiyi-walkthrough.mp4` 加一条中文旁白音轨。

为什么做：分组答辩时，评委看到的第一眼就是这段片。对手约 14/21 有音轨，
我方 14 个 mp4 此前**全部无声**（逐个文件扫 `audiomark=0` 佐证）。

旁白文本见 `docs/演示旁白稿.md`；本脚本只负责"念出来 + 按时间点贴上去"。

时间轴来源（不靠手调）：
    build/record_demo.py 的常量 INTRO_SEC=7 DWELL=8 LEAD=3 HOLD=5 TAIL=2
    FAIL_HOLD=22 OUTRO_SEC=8 FPS=10
    → 每屏时长 = DWELL + 控件数×(LEAD+HOLD) + TAIL
    再用实测场景切换点（7.0s / 90.3s / 128.6s）校准起点。

用法：
    python build/make_narration.py            # 只生成 8 段 mp3
    python build/make_narration.py --mux      # 生成 + 混流成 -narrated.mp4

前置：`pip install edge-tts`（联网）、`ffmpeg` 在 PATH 或设 FFMPEG_BIN。
输出：build/_video/narration/segNN.mp3、build/_video/shiyi-walkthrough-narrated.mp4
原无声版**保留不动**。

Stdlib + edge_tts。
"""

import argparse
import asyncio
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VIDEO = os.path.join(ROOT, "build", "_video", "shiyi-walkthrough.mp4")
OUTDIR = os.path.join(ROOT, "build", "_video", "narration")
OUTVID = os.path.join(ROOT, "build", "_video", "shiyi-walkthrough-narrated.mp4")

VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "-5%"          # 稍慢一点，演示片听得清

# (起始秒, 文本)  —— 起始点 = 目标区间起点 + 0.6s 缓冲
SEGS = [
    (0.6,   "拾意。从你发过的一段对话里，读出你没说出口的那个安排。"),
    (7.8,   "一条群消息。它认出时间、地点、类型，每一条都标明出处——不是它猜的，是原文里有的。它还记得你的老规矩：坐高铁，不坐飞机。"),
    (22.8,  "有两样它确实不知道，就停下来问，而且只问这两样——猜得出来就猜，猜不出来绝不装懂。"),
    (50.8,  "然后给一版方案。你的老规矩已经替你筛过一遍，所以递上来的只有高铁。"),
    (64.8,  "点「记下」，它把这次的新安排写进长期记忆——旧规矩和这次新增，分开列给你看。"),
    (79.8,  "最后是回执三行：一件真做了，两件明说没动。没做的，它绝不写成做了。"),
    (94.5,  "再看不好的情况。包没签名，宿主直接拒绝——我们一张卡都不渲染，不降级、不糊弄。包被改过一个字符，摘要对不上，同样拒绝。这两段不是演示顺利，是演示失败：宁可什么都不显示，也不显示一个不可信的结果。"),
    (130.8, "拾意。Agent 干活，人保留控制。"),
]


def ffmpeg_bin():
    return os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg") or "ffmpeg"


def ffprobe_bin():
    p = os.environ.get("FFPROBE_BIN")
    if p:
        return p
    f = ffmpeg_bin()
    cand = os.path.join(os.path.dirname(f), "ffprobe")
    if os.path.exists(cand) or os.path.exists(cand + ".exe"):
        return cand
    return shutil.which("ffprobe") or "ffprobe"


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.stderr.write((r.stdout or "") + "\n" + (r.stderr or "") + "\n")
        raise SystemExit("命令失败：%s" % " ".join(cmd[:3]))
    return r.stdout


def duration(path):
    out = run([ffprobe_bin(), "-v", "error", "-show_entries", "format=duration",
               "-of", "csv=p=0", path])
    return float(out.strip())


async def tts_all():
    import edge_tts
    os.makedirs(OUTDIR, exist_ok=True)
    made = []
    for i, (_start, text) in enumerate(SEGS, 1):
        dst = os.path.join(OUTDIR, "seg%02d.mp3" % i)
        c = edge_tts.Communicate(text, VOICE, rate=RATE)
        await c.save(dst)
        d = duration(dst)
        made.append((i, dst, d))
        print("  seg%02d  %5.2fs  %s" % (i, d, text[:24]))
    return made


def mux(made):
    if not os.path.exists(VIDEO):
        raise SystemExit("找不到原片：%s" % VIDEO)
    vdur = duration(VIDEO)
    print("\n原片时长 %.2fs；旁白合计 %.2fs" % (vdur, sum(d for _, _, d in made)))
    # 检查是否有旁白超出片长（超出会串到下一屏）
    for (start, _t), (i, _p, d) in zip(SEGS, made):
        if start + d > vdur:
            print("  ⚠️ seg%02d 结束于 %.2fs，超出片长 %.2fs" % (i, start + d, vdur))

    inputs = [VIDEO] + [p for _n, p, _d in made]
    fc = []
    mix_labels = []
    for idx, ((start, _t), (_n, _p, _d)) in enumerate(zip(SEGS, made), 1):
        ms = int(round(start * 1000))
        lab = "a%d" % idx
        fc.append("[%d:a]aresample=48000,adelay=%d|%d[%s]" % (idx, ms, ms, lab))
        mix_labels.append("[%s]" % lab)
    fc.append("%samix=inputs=%d:normalize=0:duration=longest,apad[aout]"
              % ("".join(mix_labels), len(mix_labels)))

    cmd = [ffmpeg_bin(), "-y", "-hide_banner"]
    for p in inputs:
        cmd += ["-i", p]
    cmd += ["-filter_complex", ";".join(fc),
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-shortest", OUTVID]
    run(cmd)
    print("✓ 已输出：%s（%.2fs）" % (OUTVID, duration(OUTVID)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mux", action="store_true", help="生成后直接混流")
    args = ap.parse_args()

    print("拾意 · 演示片旁白（%s, rate=%s）" % (VOICE, RATE))
    made = asyncio.run(tts_all())
    if args.mux:
        mux(made)
    else:
        print("\n（加 --mux 可混流成 %s）" % os.path.basename(OUTVID))


if __name__ == "__main__":
    main()
