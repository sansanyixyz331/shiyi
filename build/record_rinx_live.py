#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真机连续录屏 —— Rinx 遥控口驱动（MAKEPAD_REMOTE），录一条"应用干活"。

与 `record_rinx_app.py`（抓窗口逐帧、需鼠标注入）不同，本脚本走 Rinx **自带的 HTTP 遥控口**：
坐标一律取 `/snap` 给的 layout 点，不缓存；用 `ffmpeg -f gdigrab` 录**连续视频**（不是帧拼）。

    MAKEPAD_REMOTE=8799 rinx.exe          # 先起宿主（别用 taskkill 收尾，用 /gq）
    python build/record_rinx_live.py [out.mp4]

红线：**只驱动到「造卡」为止，不点「确认」** —— 确认会向绑定的房间真实发消息（动线上账号）。
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request as ur

B = "http://127.0.0.1:8799"
BUNDLE = "C:/gosim_agentic/05_app/shiyi/apps/shiyi-live/bundle"
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "_gen_video", "live-app-in-rinx.mp4")
FPS = 15

# DPI 感知必须在进程早期设定，否则首次 EnumWindows 拿不到真实窗口坐标
try:
    import ctypes as _ct
    _ct.windll.shcore.SetProcessDpiAwareness(2)
except Exception:  # noqa: BLE001
    pass


def find_ffmpeg():
    hits = glob.glob(
        r"C:\Users\adves\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg*\**\bin\ffmpeg.exe",
        recursive=True)
    if hits:
        return sorted(hits)[-1]
    return shutil.which("ffmpeg")


def get(u, t=12):
    try:
        return ur.urlopen(B + u, timeout=t).read()
    except Exception:  # noqa: BLE001
        return b""


def snap():
    try:
        return json.loads(get("/snap").decode())["s"]
    except Exception:  # noqa: BLE001
        return []


def win_rect():
    """找 Rinx 主窗口矩形。注意：EnumWindows 回调类型必须挂在模块级并保持强引用，
    否则进程内首次枚举会静默失败（后续调用才成功）。"""
    import ctypes
    from ctypes import wintypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    u = ctypes.windll.user32
    out = []

    def cb(h, _):
        if u.IsWindowVisible(h):
            c = ctypes.create_unicode_buffer(256)
            u.GetClassNameW(h, c, 256)
            if "makepad" in c.value.lower():
                n = u.GetWindowTextLengthW(h)
                b = ctypes.create_unicode_buffer(n + 1)
                u.GetWindowTextW(h, b, n + 1)
                if b.value.strip().startswith("Rinx"):
                    r = wintypes.RECT()
                    u.GetWindowRect(h, ctypes.byref(r))
                    if r.right - r.left > 300:
                        out.append((h, r))
        return True

    _CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(cb)
    u.EnumWindows(_CB, 0)
    if out:
        return out[0][1]
    # 兜底：首次枚举可能拿不到，短暂重试
    for _ in range(6):
        time.sleep(0.4)
        out.clear()
        u.EnumWindows(_CB, 0)
        if out:
            return out[0][1]
    return None


def force_front():
    """把 Rinx 抢到前台（gdigrab 抓屏需要它不被遮挡）。"""
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    k = ctypes.windll.kernel32
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    out = []

    def cb(h, _):
        if u.IsWindowVisible(h):
            c = ctypes.create_unicode_buffer(256)
            u.GetClassNameW(h, c, 256)
            if "makepad" in c.value.lower():
                n = u.GetWindowTextLengthW(h)
                b = ctypes.create_unicode_buffer(n + 1)
                u.GetWindowTextW(h, b, n + 1)
                if b.value.strip().startswith("Rinx"):
                    rr = wintypes.RECT()
                    u.GetWindowRect(h, ctypes.byref(rr))
                    if rr.right - rr.left > 300:
                        out.append((h, rr.left))
        return True

    _CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(cb)
    u.EnumWindows(_CB, 0)
    if not out:
        time.sleep(0.4)
        u.EnumWindows(_CB, 0)
    if not out:
        return
    out.sort(key=lambda x: x[1])
    h = out[0][0]
    u.ShowWindow(h, 9)
    fg = u.GetForegroundWindow()
    ft = u.GetWindowThreadProcessId(fg, None)
    ct = k.GetCurrentThreadId()
    u.AttachThreadInput(ct, ft, True)
    u.SetForegroundWindow(h)
    u.BringWindowToTop(h)
    u.SetFocus(h)
    u.AttachThreadInput(ct, ft, False)
    time.sleep(0.4)


def center(r):
    return int(r[0] + r[2] / 2), int(r[1] + r[3] / 2)


def click(r, wait=1.2):
    x, y = center(r)
    get("/m?k=move&x=%d&y=%d" % (x, y)); time.sleep(0.15)
    get("/m?k=down&x=%d&y=%d" % (x, y)); time.sleep(0.2)
    get("/m?k=up&x=%d&y=%d" % (x, y)); time.sleep(wait)


def key(name):
    """敲一个键（makepad 遥控口语法：k=down&c=KeyName）。"""
    get("/k?k=down&c=" + name)
    get("/k?k=up&c=" + name)
    time.sleep(0.02)


def clear_field(w, n=180):
    """把输入框清空：先点最右端把光标放到末尾，再连发退格。"""
    r = w["r"]
    click([r[0] + r[2] - 6, r[1], 6, r[3]], 0.5)
    for _ in range(n):
        key("Backspace")


def by_id(k):
    return next((w for w in snap() if str(w.get("i", "")) == k), None)


def by_text(sub, ty=None):
    for w in snap():
        if ty and w.get("ty") != ty:
            continue
        if sub in str(w.get("t", "")):
            return w
    return None


def wait_for(pred, timeout=15):
    t0 = time.time()
    while time.time() - t0 < timeout:
        x = pred()
        if x:
            return x
        time.sleep(0.4)
    return None


def main():
    ff = find_ffmpeg()
    r = win_rect()
    if not r:
        raise SystemExit("Rinx 窗口未找到（先 MAKEPAD_REMOTE=8799 rinx.exe）")
    w, h = r.right - r.left, r.bottom - r.top
    w -= w % 2
    h -= h % 2
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    print("窗口 %dx%d @ (%d,%d)；录制 → %s" % (w, h, r.left, r.top, OUT))

    rec = subprocess.Popen(
        [ff, "-y", "-f", "gdigrab", "-framerate", str(FPS),
         "-offset_x", str(r.left), "-offset_y", str(r.top),
         "-video_size", "%dx%d" % (w, h), "-i", "desktop",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    force_front()
    time.sleep(1.5)

    try:
        # 若已有 app 在跑（面板里是 app_content 而非导入页），先点 Back 回到导入页
        if by_id("app_content") and not by_id("path"):
            bk = wait_for(lambda: by_text("Back", "Button"), 4)
            if bk:
                click(bk["r"], 1.5)
                print("点 Back 回到导入页")
        # 先进 apps 面板（若已在导入页则跳过）
        if not by_id("path"):
            ab = wait_for(lambda: by_id("octoscript_apps_button"), 8)
            if ab:
                click(ab["r"], 1.5)
                print("进 apps 面板")
        # 目录页 → 导入页
        if not by_id("path"):
            ia = wait_for(lambda: by_id("import_app"), 6)
            if ia:
                click(ia["r"], 1.5)
                print("进导入页")
        # 导入页：填路径 → Review → Run（房间留空，避免误绑线上房间）
        p = wait_for(lambda: by_id("path"), 8)
        if p:
            # 先清空（上次可能残留），再填正确路径
            clear_field(p)
            time.sleep(0.4)
            get("/k?t=" + urllib.parse.quote(BUNDLE))
            time.sleep(0.8)
            cur = by_id("path")
            print("填路径 OK -> %r" % (cur.get("t") if cur else None))
        # Review
        rv = wait_for(lambda: by_id("review"), 5)
        if rv:
            click(rv["r"], 3.5)
            nt = by_id("notice")
            print("Review 完成 -> %r" % (str(nt.get("t"))[:60] if nt else None))
        # Run
        rn = wait_for(lambda: by_id("run"), 5)
        if rn:
            click(rn["r"], 6.0)
            print("Run 完成")
        # 等 app 起来（出现「造卡」按钮）
        mk = wait_for(lambda: by_text("造卡", "Button"), 20)
        if mk:
            print("app 已起，找到造卡")
        time.sleep(2.0)
        # 直接在输入框写一句话（比点例子稳定）
        inp = wait_for(lambda: by_id("inp"), 6)
        if inp:
            click(inp["r"], 0.5)
            get("/k?t=" + urllib.parse.quote("下周三去深圳"))
            time.sleep(1.2)
            print("写入一句话")
        mk = by_text("造卡", "Button")
        if mk:
            click(mk["r"], 3.0)
            print("造卡完成（不点确认）")
        time.sleep(3.0)
    finally:
        try:
            rec.stdin.write(b"q")
            rec.stdin.flush()
        except Exception:  # noqa: BLE001
            pass
        rec.wait(timeout=20)
    print("成片：%s（%d bytes）" % (OUT, os.path.getsize(OUT)))


if __name__ == "__main__":
    sys.exit(main())
