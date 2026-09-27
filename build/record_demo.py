#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拾意 · 演示短视频（A4）

在官方参考宿主 `card-host` 里真实跑一遍五屏流程，**逐帧录下宿主窗口本身**
（走宿主自带的 instrument 路由 `/g?raw=1`），再用 ffmpeg 合成 mp4。

为什么这么录，而不是手机录屏：

  · 官方《作品提交与 AppHub 规范》第 6 条要的是「运行截图、日志或视频及对应
    复现步骤」—— 视频只是**证据形态之一**，不是必须形态；而且原文写明
    「演示材料不能代替可运行的开源作品」。
  · 我方作品形态 = **Hub 卡片包**，官方给的交付是「预检结果 + 实际运行证据」。
    宿主就是官方参考宿主，所以这段视频录的是**真实运行**，不是做动画。
  · 手机端要等官方「支持设备／运行包」公布；官方明说桌面那条 HTTP 自动化
    通道在 Android 上被编译掉，手机端另有一套（真机触摸注入 + GPU 回读），
    是「几小时级」的活，且我们交付的是卡片包、不是独立 APK。

脚本做的事：

    起宿主（可见窗口）→ 等本屏真画出来 → 开始逐帧采样
      → 用 /snap 证实控件在 → /click 点它正中心 → 停 1.5 秒（让这一下被录到）
      → 读该屏 service-actions.json 声明的事件名 → 推进下一屏
    …五屏跑完 → ffmpeg 合成 mp4（字幕用卡内真实文案）

两个踩过的坑（已修）：
  · 抓帧计数器必须**全局共享**，否则每屏各自从 00001 起 → 后一屏覆盖前一屏。
  · ffmpeg 的 fontfile 不能带 Windows 的 `C:/` 形式（冒号要转义、反斜杠是转义符），
    → 把字体复制到输出目录、只传裸文件名、并把 ffmpeg 的 cwd 设成输出目录。
  · 字幕**不能画在画面上**（会盖住主按钮）→ 先用 pad 在底部加一条字幕带，再画进去。

用法：
    python build/record_demo.py                # 录五屏正流程
    python build/record_demo.py --no-caption   # 不要字幕

产物：
    build/_video/shiyi-walkthrough.mp4         演示短片
    build/_video/frames/                       原始帧（可按需复合成别的码率）

依赖：标准库 + ffmpeg（本机 winget 装的 Gyan.FFmpeg 8.1.2）。
"""

import glob
import json
import os
import shutil
import subprocess
import sys
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
FONT_SRC = r"C:\Windows\Fonts\msyh.ttc"
FONT_DST = os.path.join(OUT, "msyh.ttc")

# 屏 → 中文题头（取自卡内 eyebrow 文案，不是我编的）
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
    """全局帧序号（跨屏共享，保证文件名连续、不互相覆盖）。"""

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
    """字幕时间轴：按帧号切段，合成时转成秒。"""

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


def esc(s):
    """ffmpeg filter 内的转义。"""
    return (s.replace("\\", "\\\\").replace(":", "\\:")
             .replace("'", "\\'").replace(",", "\\,"))


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
    return ",".join(fits)


def record():
    from shiyi_flow import Flow  # noqa: PLC0415

    if os.path.isdir(FRAMES):
        shutil.rmtree(FRAMES)
    os.makedirs(FRAMES, exist_ok=True)

    counter = Counter()
    caps = Caps()
    fl = Flow(VF.MESSAGE, room=VF.ROOM)
    log("=" * 74)
    log("拾意 · 演示录制（官方参考宿主 card-host，逐帧采样 %d fps）" % FPS)
    log("消息：[%s] %s" % (VF.ROOM, VF.MESSAGE))
    log("=" * 74)

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
        logf = os.path.join(VF.EVID, "host_%s.log" % screen)
        state = os.path.join(VF.RUN, screen, "state")
        with VF.Host(b, logf, state, extra=["--allow-unsigned"]) as h:
            png = h.frame()
            log("   宿主 127.0.0.1:%d 已画出本屏（%d 字节）" % (h.port, len(png)))
            g = Grabber(h.port, FRAMES, counter)
            g.start()
            caps.switch(counter.n, "拾意　｜　" + title)   # 先上字幕，免得开头有段空带
            time.sleep(1.0)                       # 本屏先稳稳显示 1 秒
            for ctl in ctls:
                x, y = VF.center_of(screen, ctl)
                h.snap(ctl)                        # 证实控件真的在
                ans = h.click(x, y)
                ev = VF.controls_of(screen).get(ctl, {}).get("event")
                label = CTRL_CN.get((screen, ctl), ctl)
                log("   点 %-12s (%3d,%3d)  应答=%s  文案=「%s」→ %s"
                    % (ctl, x, y, ans, label, ev))
                caps.switch(counter.n, "拾意　｜　点「%s」" % label)
                time.sleep(1.5)                    # 这一下要留在画面里
                if ev:
                    fl.handle(ev)
                caps.switch(counter.n, "拾意　｜　" + title)
            time.sleep(0.8)
            g.stop()
            caps.close(counter.n)
            log("   本屏采样 %d 帧（累计 %d）" % (g.saved, counter.n))

    log("")
    log("-" * 74)
    log("五屏跑完，共 %d 帧 / 约 %.1f 秒；决定链：%s"
        % (counter.n, counter.n / float(FPS), " → ".join(fl.decisions)))
    log("结束屏：%s" % fl.stage)
    return caps.marks(FPS), counter.n


def assemble(marks, total, caption=True):
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("找不到 ffmpeg")
    log("")
    log("ffmpeg：%s" % ff)

    has_font = caption and os.path.exists(FONT_SRC)
    if has_font:
        shutil.copy2(FONT_SRC, FONT_DST)          # 裸文件名 + cwd，避开 C:\ 的转义地狱
    elif caption:
        log("！字体不存在，改为无字幕：%s" % FONT_SRC)

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

    if has_font and not run("带字幕", caption_filter(marks)):
        run("无字幕", caption_filter([]))
    elif not has_font:
        run("无字幕", caption_filter([]))

    size = os.path.getsize(MP4)
    log("已生成：%s（%.2f MB，%d 帧 / %.1f 秒 @%dfps）"
        % (MP4, size / 1048576.0, total, total / float(FPS), FPS))
    return MP4


def main():
    os.makedirs(OUT, exist_ok=True)

    if "--from-frames" in sys.argv:               # 只重编码，不重录
        with open(MARKS_JSON, encoding="utf-8") as f:
            marks = json.load(f)["marks"]
        total = len([n for n in os.listdir(FRAMES) if n.endswith(".png")])
        log("从已有帧重编码：%d 帧" % total)
        assemble(marks, total, caption="--no-caption" not in sys.argv)
        return 0

    marks, total = record()
    if total < 60:
        raise RuntimeError("只采到 %d 帧，太少（五屏应 ≳120 帧），检查采样是否被覆盖" % total)
    with open(MARKS_JSON, "w", encoding="utf-8") as f:
        json.dump({"marks": marks, "total": total}, f, ensure_ascii=False, indent=1)
    assemble(marks, total, caption="--no-caption" not in sys.argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
