#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拾意 · 演示短片（A4）

按官方要求重做：**时长够（2–3 分钟）+ 失败态入镜**。

在官方参考宿主 `card-host` 里真实跑一遍五屏流程并**逐帧录下宿主窗口本身**
（走宿主自带的 instrument 路由 `/g?raw=1`），再用 ffmpeg 合成 mp4；
片头/片尾是合成的标题卡，两个失败态是**真起宿主、真被拒绝**后录到的空窗口
（画面上叠官方原话，不遮不骗）。

为什么这么录，而不是手机录屏（详见 00_docs/大白话_…md 与 README）：
  · 官方《作品提交与 AppHub 规范》第 6 条要的是「运行截图、日志或视频及对应
    复现步骤」—— 视频只是**证据形态之一**；且原文写明「演示材料不能代替可运行
    的开源作品」。
  · 我方作品形态 = **Hub 卡片包**，官方给的交付是「预检结果 + 实际运行证据」。
  · 手机端要等官方「支持设备／运行包」公布（官网："将在赛前公布"），且官方把
    桌面那条 HTTP 自动化通道在 Android 上编译掉了；我们交付的是卡片包、不是独立
    APK，所以桌面宿主录制是最硬、也最合理的一份运行证据。

脚本做的事：
    片头卡 → [五屏：起宿主 → 等本屏真画出来 → 开始逐帧采样 → /snap 证实控件在
    → /click 点它正中心 → 停几秒让这一下被录到 → 读该屏 service-actions.json
    声明的事件名推进下一屏] → [失败态①未签名 / ②摘要不符：真起宿主 → 录到
    拒绝后的空窗口 → 叠官方原话] → 片尾卡 → ffmpeg 合成 mp4

踩过的坑（都已修）：
  · 抓帧计数器必须**全局共享**，否则每屏各自从 00001 起 → 后一屏覆盖前一屏。
  · ffmpeg 的 fontfile 不能带 Windows 的 `C:/`（冒号要转义、反斜杠是转义符），
    → 把字体复制到输出目录、只传裸文件名、并把 ffmpeg 的 cwd 设成输出目录。
  · 字幕**不能画在画面上**（会盖住主按钮）→ 先 pad 在底部加一条字幕带再画进去。
  · 失败态窗口是**空白**的，直接播看不出信息 → 叠一层深色说明卡（含宿主原话）。

用法：
    python build/record_demo.py                # 全片（正流程 + 失败态 + 片头尾）
    python build/record_demo.py --no-caption   # 不要字幕
    python build/record_demo.py --from-frames  # 只重编码，不重录

产物：
    build/_video/shiyi-walkthrough.mp4         演示短片（2–3 分钟）
    build/_video/frames/                       原始帧（可按需复合成别的码率）
    build/_video/marks.json                    字幕/说明卡时间轴

依赖：标准库 + ffmpeg（本机 winget 装的 Gyan.FFmpeg 8.1.2）。
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import verify_flow as VF  # noqa: E402  复用「组包/盖章/起宿主/控件定位」的逻辑

OUT = os.path.join(ROOT, "build", "_video")
FRAMES = os.path.join(OUT, "frames")
MP4 = os.path.join(OUT, "shiyi-walkthrough.mp4")
MARKS_JSON = os.path.join(OUT, "marks.json")
FPS = 10
W, H = 515, 1115                                  # 与宿主抓帧同尺寸
FONT_SRC = r"C:\Windows\Fonts\msyh.ttc"
FONT_DST = os.path.join(OUT, "msyh.ttc")
INTRO_PNG = os.path.join(OUT, "_intro.png")
OUTRO_PNG = os.path.join(OUT, "_outro.png")

# ── 节奏（秒）—— 目标总时长 2–3 分钟 ──────────────────────────────────────
INTRO_SEC = 7.0        # 片头卡
DWELL = 8.0            # 每屏静置读卡
LEAD = 3.0             # 点击前先说一下
HOLD = 5.0             # 点击后停留，让这一下被看清
TAIL = 2.0             # 每屏收尾
FAIL_HOLD = 22.0       # 每个失败态画面停留
OUTRO_SEC = 8.0        # 片尾卡

# 屏 → 中文题头（取自卡内 eyebrow 文案，不是编的）
SCREEN_CN = {
    "shiyi-01-read": "第一步 · 识别",
    "shiyi-02-ask": "第二步 · 追问",
    "shiyi-03-plan": "第三步 · 方案",
    "shiyi-04-memo": "第四步 · 记忆",
    "shiyi-05-done": "第五步 · 完成",
}

# 控件 → 卡内真实按钮文案（从 page.card 的 copy 里逐字取的）
CTRL_CN = {
    ("shiyi-01-read", "action_yes"): "对，就是这件事",
    ("shiyi-02-ask", "opt_a1"): "周三一早",
    ("shiyi-02-ask", "opt_b1"): "从家里",
    ("shiyi-02-ask", "action_go"): "就按这个查",
    ("shiyi-03-plan", "action_take"): "就要第一班",
    ("shiyi-04-memo", "action_keep"): "记下",
    ("shiyi-05-done", "action_open"): "看行程",
}

INTRO_LINES = [
    ("拾意 · Pickup", 54, "white", 360),
    ("从一段对话，读出一个安排", 30, "0xB9F6CA", 452),
    ("GOSIM Agentic App 2026", 22, "0x81C784", 546),
    ("OctoSense · 即时消息", 20, "0x81C784", 584),
    ("真实运行 · 在官方参考宿主 card-host 中录制", 17, "0xA5D6A7", 668),
]

OUTRO_LINES = [
    ("拾意 · Pickup", 40, "white", 320),
    ("开源仓库", 20, "0x81C784", 416),
    ("github.com/sansanyixyz331/shiyi", 20, "white", 448),
    ("Apache-2.0 · 固定提交号见仓库", 17, "0xA5D6A7", 494),
    ("一键复现", 20, "0x81C784", 574),
    ("python build/verify_flow.py", 17, "white", 606),
    ("python build/record_demo.py", 17, "white", 638),
]


def log(msg):
    print(msg, flush=True)


def find_ffmpeg():
    for c in glob.glob(
            r"C:\Users\adves\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg*\**\bin\ffmpeg.exe",
            recursive=True):
        if os.path.exists(c):
            return c
    return shutil.which("ffmpeg")


class Counter:
    """全局帧序号（跨段共享，保证文件名连续、不互相覆盖）。"""

    def __init__(self):
        self.n = 0
        self.lock = threading.Lock()

    def next(self):
        with self.lock:
            self.n += 1
            return self.n


class Grabber(threading.Thread):
    """后台按 FPS 采样宿主窗口（PNG）。"""

    def __init__(self, port, outdir, counter, fps=FPS):
        super().__init__(daemon=True)
        self.port, self.outdir, self.counter, self.fps = port, outdir, counter, fps
        self.stop_flag = threading.Event()
        self.saved = 0

    def run(self):
        interval = 1.0 / self.fps
        while not self.stop_flag.is_set():
            t0 = time.time()
            try:
                d = VF.fetch(self.port, "/g?raw=1", timeout=10, retries=1)
                if d[:8] == b"\x89PNG\r\n\x1a\n":
                    i = self.counter.next()
                    with open(os.path.join(self.outdir, "%05d.png" % i), "wb") as f:
                        f.write(d)
                    self.saved += 1
            except Exception:  # noqa: BLE001 - 换屏/起停瞬间抓不到是正常的
                pass
            dt = interval - (time.time() - t0)
            if dt > 0:
                time.sleep(dt)

    def stop(self):
        self.stop_flag.set()
        self.join(timeout=10)


class Caps:
    """底部字幕时间轴：按帧号切段，合成时转成秒。"""

    def __init__(self):
        self.items = []  # [start_frame, end_frame|None, text]

    def switch(self, frame, text):
        self._close(frame)
        self.items.append([frame, None, text])

    def _close(self, frame):
        if self.items and self.items[-1][1] is None:
            self.items[-1][1] = frame

    def close(self, frame):
        self._close(frame)

    def marks(self, fps):
        out = []
        for s, e, t in self.items:
            if e is None:
                e = s + 1
            if e - s < 3:          # 太短的段给个下限，否则字幕一闪而过
                e = s + 3
            out.append((s / float(fps), (e + 1) / float(fps), t))
        return out


class Overlays:
    """失败态全屏说明卡（盖住空白窗口，画宿主的真实原话）。"""

    def __init__(self):
        self.items = []  # [start_frame, end_frame|None, [ (text,size,color,dy), ... ]]

    def open(self, frame, lines):
        self.items.append([frame, None, lines])

    def close(self, frame):
        if self.items and self.items[-1][1] is None:
            self.items[-1][1] = frame

    def marks(self, fps):
        out = []
        for s, e, lines in self.items:
            if e is None:
                e = s + 3
            out.append([s / float(fps), (e + 1) / float(fps), lines])
        return out


def esc(s):
    """ffmpeg filter 内的转义。

    注意：ffmpeg 的**单引号串里不能用反斜杠转义撇号**（`\\'` 会把引号关掉，
    后面的内容被当成新滤镜名 → `No such filter: '80.60'` 这类怪错）。所以
    ASCII 撇号统一换成排版撇号 U+2019（非特殊字符），从根上避开。
    """
    return (s.replace("\\", "\\\\")
             .replace("'", "\u2019")
             .replace(":", "\\:")
             .replace(",", "\\,"))


def render_card(dst, lines, bg="0x0F1B17"):
    """用 ffmpeg 生成一张标题卡 PNG（尺寸与宿主抓帧一致）。"""
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("找不到 ffmpeg（片头/片尾卡需要）")
    shutil.copy2(FONT_SRC, FONT_DST)          # 裸文件名 + cwd，避开 C:\ 的转义地狱
    parts = []
    for text, size, color, y in lines:
        parts.append(
            "drawtext=fontfile=msyh.ttc:text='%s':fontsize=%d:fontcolor=%s"
            ":x=(w-text_w)/2:y=%d" % (esc(text), size, color, y))
    cmd = [ff, "-y", "-f", "lavfi", "-i", "color=c=%s:s=%dx%d" % (bg, W, H),
           "-frames:v", "1", "-vf", ",".join(parts), dst]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=OUT)
    if r.returncode != 0:
        raise RuntimeError("标题卡渲染失败：\n%s" % (r.stderr or "")[-500:])


def emit(counter, src_png, seconds):
    """把一张 PNG 复制成 seconds 秒的帧，接在序列后面。"""
    n = max(1, int(round(seconds * FPS)))
    for _ in range(n):
        i = counter.next()
        shutil.copy2(src_png, os.path.join(FRAMES, "%05d.png" % i))
    return n


def read_log(path, tail=6000):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()[-tail:]
    except Exception:  # noqa: BLE001
        return ""


def shorten(msg):
    """长哈希压成 前8…后6，免得占掉半屏。"""
    return re.sub(r"\b([0-9a-f]{16,})\b",
                  lambda m: m.group(1)[:8] + "\u2026" + m.group(1)[-6:], msg)


def fail_lines(idx, raw_msg):
    """失败态说明卡的文字（含宿主原话，逐字不编，只把长哈希压短）。"""
    wrap = textwrap.wrap(shorten(raw_msg), width=34) or [raw_msg]
    lines = [
        ("失败态 %s" % idx, 38, "white", 300),
        ("（画面 = 宿主拒绝后留下的空窗口）", 17, "0xA5D6A7", 372),
        ("宿主原话", 20, "0x81C784", 452),
    ]
    y = 496
    for ln in wrap:
        lines.append((ln, 19, "white", y))
        y += 30
    lines.append(("结果", 20, "0x81C784", y + 40))
    lines.append(("一张卡都没画 —— fail-closed", 24, "0xFF8A65", y + 74))
    return lines


# ── 录制 ──────────────────────────────────────────────────────────────────

def record():
    from shiyi_flow import Flow  # noqa: PLC0415

    if os.path.isdir(FRAMES):
        shutil.rmtree(FRAMES)
    os.makedirs(FRAMES, exist_ok=True)

    counter = Counter()
    caps = Caps()
    ov = Overlays()
    fl = Flow(VF.MESSAGE, room=VF.ROOM)
    log("=" * 74)
    log("拾意 · 演示录制（官方参考宿主 card-host，逐帧采样 %d fps）" % FPS)
    log("消息：[%s] %s" % (VF.ROOM, VF.MESSAGE))
    log("=" * 74)

    # ① 片头卡
    render_card(INTRO_PNG, INTRO_LINES)
    caps.switch(counter.n, "拾意 · Pickup ｜ 从一段对话，读出一个安排")
    emit(counter, INTRO_PNG, INTRO_SEC)
    log("▌ 片头卡 %d 帧" % int(INTRO_SEC * FPS))

    # ② 正流程五屏
    grouped = []
    for screen, ctl in VF.SCRIPT:
        if grouped and grouped[-1][0] == screen:
            grouped[-1][1].append(ctl)
        else:
            grouped.append((screen, [ctl]))

    for screen, ctls in grouped:
        title = SCREEN_CN.get(screen, screen)
        log("")
        log("▌ %s（%s）" % (screen, title))
        b = VF.make_bundle(screen)
        digest = VF.stamp(b)
        log("   摘要 %s" % digest[:16])
        logf = os.path.join(VF.EVID, "host_%s.log" % screen)
        state = os.path.join(VF.RUN, screen, "state")
        with VF.Host(b, logf, state, extra=["--allow-unsigned"]) as h:
            png = h.frame()
            log("   宿主 127.0.0.1:%d 已画出本屏（%d 字节）" % (h.port, len(png)))
            g = Grabber(h.port, FRAMES, counter)
            g.start()
            caps.switch(counter.n, "拾意　｜　" + title)
            time.sleep(DWELL)                     # 本屏先稳稳显示，让人读
            for ctl in ctls:
                label = CTRL_CN.get((screen, ctl), ctl)
                caps.switch(counter.n, "拾意　｜　准备点「%s」" % label)
                time.sleep(LEAD)
                x, y = VF.center_of(screen, ctl)
                h.snap(ctl)                        # 证实控件真的在
                ans = h.click(x, y)
                ev = VF.controls_of(screen).get(ctl, {}).get("event")
                log("   点 %-12s (%3d,%3d)  应答=%s  文案=「%s」→ %s"
                    % (ctl, x, y, ans, label, ev))
                caps.switch(counter.n, "拾意　｜　点「%s」→ %s" % (label, ev or "（终点）"))
                time.sleep(HOLD)                   # 这一下要留在画面里
                if ev:
                    fl.handle(ev)
                caps.switch(counter.n, "拾意　｜　" + title)
            time.sleep(TAIL)
            g.stop()
            caps.close(counter.n)
            log("   本屏采样 %d 帧（累计 %d）" % (g.saved, counter.n))

    # ③ 失败态（真起宿主、真被拒）
    for idx, case, title in (
            ("①", "unsigned", "失败态 ① ｜ 卡片包未签名"),
            ("②", "tampered", "失败态 ② ｜ 包被改过一个字符")):
        log("")
        log("▨ %s" % title)
        if case == "unsigned":
            b = VF.make_bundle("shiyi-01-read", dest=os.path.join(VF.RUN, "neg_unsigned"))
            VF.stamp(b)
            extra = ()
        else:
            b = VF.make_bundle("shiyi-01-read", dest=os.path.join(VF.RUN, "neg_tampered"))
            VF.stamp(b)
            p = os.path.join(b, "page.data.json")
            with open(p, encoding="utf-8") as f:
                raw = f.read()
            with open(p, "w", encoding="utf-8") as f:
                f.write(raw.replace("拾意", "拾意 ", 1))
            extra = ("--allow-unsigned",)
        logf = os.path.join(VF.EVID, "neg_%s.log" % case)
        state = os.path.join(VF.RUN, "neg_%s" % case, "state")
        with VF.Host(b, logf, state, extra=extra) as h:
            time.sleep(2.5)                        # 等它把拒绝原因写进日志
            txt = read_log(logf)
            m = re.search(r"card-host: refused: .*", txt)
            raw_msg = m.group(0).split("refused:", 1)[-1].strip() if m else "（未捕获到拒绝原因）"
            rendered = "[SPLASH] eval" in txt
            log("   宿主 127.0.0.1:%d" % h.port)
            log("   拒绝原因：refused: %s" % raw_msg)
            log("   是否渲染了卡片：%s" % ("是（不该）" if rendered else "否 —— fail-closed ✓"))
            caps.switch(counter.n, "拾意　｜　" + title)
            ov.open(counter.n, fail_lines(idx, raw_msg))
            g = Grabber(h.port, FRAMES, counter)
            g.start()
            time.sleep(FAIL_HOLD)
            g.stop()
            ov.close(counter.n)
            caps.close(counter.n)
            log("   录到 %d 帧（画面为空窗口，已叠说明卡）" % g.saved)

    # ④ 片尾卡
    render_card(OUTRO_PNG, OUTRO_LINES)
    caps.switch(counter.n, "拾意 · Pickup ｜ 开源仓库 github.com/sansanyixyz331/shiyi")
    emit(counter, OUTRO_PNG, OUTRO_SEC)
    log("▌ 片尾卡 %d 帧" % int(OUTRO_SEC * FPS))

    log("")
    log("-" * 74)
    log("录制完成：共 %d 帧 / 约 %.1f 秒；决定链：%s"
        % (counter.n, counter.n / float(FPS), " → ".join(fl.decisions)))
    log("结束屏：%s" % fl.stage)
    return caps.marks(FPS), ov.marks(FPS), counter.n


# ── 合成 ──────────────────────────────────────────────────────────────────

def overlay_filter(overlays):
    parts = []
    for t0, t1, lines in overlays:
        parts.append(
            "drawbox=x=0:y=0:w=iw:h=ih:color=0x0B1512@0.96:t=fill"
            ":enable='between(t,%.2f,%.2f)'" % (t0, t1))
        for text, size, color, y in lines:
            parts.append(
                "drawtext=fontfile=msyh.ttc:text='%s':fontsize=%d:fontcolor=%s"
                ":x=(w-text_w)/2:y=%d:enable='between(t,%.2f,%.2f)'"
                % (esc(text), size, color, y, t0, t1))
    return parts


def caption_filter(marks):
    # 先在底部加一条字幕带（不遮卡片），再把字幕画进那条带子里
    fits = ["scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "pad=iw:ih+72:0:0:color=0x141414"]
    for t0, t1, text in marks:
        fits.append(
            "drawtext=fontfile=msyh.ttc:text='%s':x=(w-text_w)/2:y=h-50"
            ":fontsize=20:fontcolor=white:box=1:boxcolor=0x1f6f5c@0.95"
            ":boxborderw=9:enable='between(t,%.2f,%.2f)'"
            % (esc(text), t0, t1))
    return fits


def assemble(marks, overlays, total, caption=True):
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("找不到 ffmpeg")
    log("")
    log("ffmpeg：%s" % ff)

    has_font = caption and os.path.exists(FONT_SRC)
    if has_font:
        shutil.copy2(FONT_SRC, FONT_DST)          # 裸文件名 + cwd，避开 C:\ 的转义地狱

    def run(tag, vf):
        cmd = [ff, "-y", "-framerate", str(FPS),
               "-i", os.path.join(FRAMES, "%05d.png"),
               "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "21",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", MP4]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=OUT)
        if r.returncode != 0:
            tail = "\n".join((r.stderr or "").strip().splitlines()[-10:])
            log("！%s 合成失败：\n%s" % (tag, tail))
            return False
        return True

    base = overlay_filter(overlays) + caption_filter(marks)
    ok = run("带字幕", ",".join(base)) if has_font else run("无字幕/无说明卡", ",".join(base))
    if not ok and has_font:
        run("去字幕重试", ",".join(overlay_filter(overlays)
                                + ["scale=trunc(iw/2)*2:trunc(ih/2)*2",
                                   "pad=iw:ih+72:0:0:color=0x141414"]))

    size = os.path.getsize(MP4)
    log("已生成：%s（%.2f MB，%d 帧 / %.1f 秒 @%dfps）"
        % (MP4, size / 1048576.0, total, total / float(FPS), FPS))
    return MP4


def main():
    os.makedirs(OUT, exist_ok=True)

    if "--from-frames" in sys.argv:               # 只重编码，不重录
        with open(MARKS_JSON, encoding="utf-8") as f:
            d = json.load(f)
        total = len([n for n in os.listdir(FRAMES) if n.endswith(".png")])
        log("从已有帧重编码：%d 帧" % total)
        assemble(d["marks"], d.get("overlays", []), total,
                 caption="--no-caption" not in sys.argv)
        return 0

    marks, overlays, total = record()
    if total < 600:
        raise RuntimeError("只采到 %d 帧，太少（全片应 ≳1200 帧），检查采样是否被覆盖" % total)
    with open(MARKS_JSON, "w", encoding="utf-8") as f:
        json.dump({"marks": marks, "overlays": overlays, "total": total},
                  f, ensure_ascii=False, indent=1)
    assemble(marks, overlays, total, caption="--no-caption" not in sys.argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
