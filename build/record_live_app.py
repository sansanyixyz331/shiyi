#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""录「现场造卡」应用干活 —— 抓真渲染帧，合成为 mp4。

不驱动 UI、不模拟点击：让应用自己按节拍换场景（demo 版 bundle），
宿主每一帧都是**真渲染**出来的，脚本只是把它们抓下来拼成视频。

    python build/record_live_app.py <bundle_dir> [out.mp4]
"""

import glob
import os
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "_live_video")
FRAMES = os.path.join(OUT, "frames")
CARD_HOST = os.environ.get("CARD_HOST_BIN") or shutil.which("card-host") or "card-host"
STATE = os.path.join(OUT, "state")
PORT = 8977
FPS = 8
SECONDS = 22.0


def find_ffmpeg():
    """找 ffmpeg：优先 PATH，其次环境变量 FFMPEG，最后常见安装位。

    不写死任何用户名/盘符 —— 换台机器（评委、队外试用）也能跑。
    """
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    env = os.environ.get("FFMPEG")
    if env and os.path.exists(env):
        return env
    pats = (
        os.path.join(os.environ.get("LOCALAPPDATA", ""),
                     "Microsoft", "WinGet", "Packages",
                     "Gyan.FFmpeg*", "**", "bin", "ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
    )
    for pat in pats:
        hits = sorted(glob.glob(pat, recursive=True))
        for c in hits:
            if os.path.exists(c):
                return c
    return None


def grab(url):
    try:
        with urllib.request.urlopen(url, timeout=6) as r:
            return r.read()
    except Exception:  # noqa: BLE001
        return None


def main():
    bundle = os.path.abspath(sys.argv[1])
    mp4 = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, "live-app.mp4")
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(FRAMES, exist_ok=True)
    os.makedirs(STATE, exist_ok=True)

    env = dict(os.environ, NO_PROXY="*")
    proc = subprocess.Popen(
        [CARD_HOST, "--bundle", bundle, "--app-data", STATE,
         "--allow-unsigned", "--remote", str(PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)

    try:
        url = "http://127.0.0.1:%d/g?raw=1" % PORT
        base = None
        for _ in range(60):                       # 等宿主起来
            base = grab(url)
            if base:
                break
            time.sleep(0.5)
        if not base:
            raise RuntimeError("宿主没起来（抓不到帧）")

        n = 0
        t0 = time.time()
        while time.time() - t0 < SECONDS:
            data = grab(url)
            if data:
                with open(os.path.join(FRAMES, "%05d.png" % n), "wb") as f:
                    f.write(data)
                n += 1
            time.sleep(1.0 / FPS)
        print("抓到 %d 帧（%.1f 秒）" % (n, time.time() - t0))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            proc.kill()

    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("找不到 ffmpeg：装到 PATH，或用 FFMPEG 环境变量指定可执行文件")
    r = subprocess.run([ff, "-y", "-framerate", str(FPS), "-i",
                        os.path.join(FRAMES, "%05d.png"),
                        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22",
                        "-movflags", "+faststart", mp4],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("合成失败：\n%s" % (r.stderr or "")[-500:])
    print("成片：%s（%d bytes）" % (mp4, os.path.getsize(mp4)))


if __name__ == "__main__":
    sys.exit(main())
