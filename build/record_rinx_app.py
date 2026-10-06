"""Drive the shiyi-live app inside the real Rinx window and record it, frame by
frame. Usage: python build/record_rinx_app.py [out.mp4]

It only touches the Rinx main window: force it to the front, click the example
chips, capture a frame per step. Every frame is a real PrintWindow capture of
the running host, so the result is the app as it actually draws - not a mock-up.

Requires Rinx to be running with the app already imported and opened (Mini apps
-> Import -> Run). The chip coordinates below are for the 1600x1000 window this
was measured on; adjust if the window is a different size.
"""
import ctypes
import os
import shutil
import subprocess
import sys
import time
from ctypes import wintypes

OUT_MP4 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    "build", "_gen_video", "live-app-in-rinx.mp4")
FRAMES = os.path.join("build", "_gen_video", "_rinx_frames")
FPS = 2
# Measured on the 1600x1000 Rinx window (chip centres come from the OCR boxes of
# the chip labels; the primary button from the accent-coloured block, which the
# window draws right-aligned at x 1386..1462, y 889..925).
CHIP_Y = 581
CHIP_TRIP = 100                # 「下周三去深圳」
CHIP_PREF = 570                # 「我不坐飞机」
GAP = 92                       # centre-to-centre: primary button -> the one after it

u = ctypes.windll.user32
g = ctypes.windll.gdi32
kk = ctypes.windll.kernel32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass


def find_rinx():
    found = []
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def cb(h, _):
        if u.IsWindowVisible(h):
            c = ctypes.create_unicode_buffer(256)
            u.GetClassNameW(h, c, 256)
            if "makepad" in c.value.lower():
                n = u.GetWindowTextLengthW(h)
                b = ctypes.create_unicode_buffer(n + 1)
                u.GetWindowTextW(h, b, n + 1)
                if b.value.strip() == "Rinx":
                    r = wintypes.RECT()
                    u.GetWindowRect(h, ctypes.byref(r))
                    if r.right - r.left > 300:
                        found.append((h, r.left))
        return True
    u.EnumWindows(CB(cb), 0)
    found.sort(key=lambda x: x[1])
    return found[0][0] if found else None


def force_front(h):
    """SetForegroundWindow alone is silently refused when the caller is not the
    foreground process; attaching input threads lifts that restriction."""
    u.ShowWindow(h, 9)
    fg = u.GetForegroundWindow()
    ft = u.GetWindowThreadProcessId(fg, None)
    ct = kk.GetCurrentThreadId()
    u.AttachThreadInput(ct, ft, True)
    u.SetForegroundWindow(h)
    u.BringWindowToTop(h)
    u.SetFocus(h)
    u.AttachThreadInput(ct, ft, False)
    time.sleep(0.35)


class BIH(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


def capture(hwnd, path):
    from PIL import Image
    r = wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc = u.GetWindowDC(hwnd)
    mdc = g.CreateCompatibleDC(hdc)
    bmp = g.CreateCompatibleBitmap(hdc, w, h)
    g.SelectObject(mdc, bmp)
    if not u.PrintWindow(hwnd, mdc, 2):        # PW_RENDERFULLCONTENT
        u.PrintWindow(hwnd, mdc, 0)
    bi = BIH()
    bi.biSize = ctypes.sizeof(BIH)
    bi.biWidth = w
    bi.biHeight = -h
    bi.biPlanes = 1
    bi.biBitCount = 32
    bi.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    g.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB").save(path)
    g.DeleteObject(bmp)
    g.DeleteDC(mdc)
    u.ReleaseDC(hwnd, hdc)


def click(hwnd, lx, ly):
    r = wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    x, y = int(r.left + lx), int(r.top + ly)
    u.SetCursorPos(x, y)
    time.sleep(0.2)
    u.mouse_event(2, 0, 0, 0, 0)   # left down
    time.sleep(0.08)
    u.mouse_event(4, 0, 0, 0, 0)   # left up


def find_primary(hwnd):
    """Locate the filled action button by colour instead of by a hard-coded y.

    The card's height depends on what it found (a trip has two fact lines, an
    errand one), so a fixed row misses. The primary button is the only solid
    accent-coloured block below the chips row; scan for a wide green run.
    """
    from PIL import Image
    tmp = os.path.join(FRAMES, "_probe.png")
    capture(hwnd, tmp)
    im = Image.open(tmp).convert("RGB")
    W, H = im.size
    px = im.load()
    box = None
    for y in range(H // 2 + 200, H):     # 下界抬高：胶囊行在 y≈615，别把它当成按钮
        xs = [x for x in range(W)
              if px[x, y][1] - px[x, y][0] > 35 and px[x, y][1] - px[x, y][2] > 18
              and px[x, y][1] > 110]
        if len(xs) >= 60:
            box = (min(xs), max(xs), y) if box is None else (
                min(box[0], min(xs)), max(box[1], max(xs)), y)
    if box is None:
        return None
    return (box[0] + box[1]) // 2, box[2]


def wheel(hwnd, notches):
    """Scroll the app: put the cursor inside the window, then one wheel event.

    A card with two fact lines plus memory lines is tall enough that its action
    row falls below a 1000px-tall window; the page scrolls, so scroll to it
    rather than declaring the button missing.
    """
    r = wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    u.SetCursorPos((r.left + r.right) // 2, (r.top + r.bottom) // 2)
    time.sleep(0.25)
    delta = (-120 * notches) & 0xFFFFFFFF          # negative = scroll down
    u.mouse_event(0x0800, 0, 0, delta, 0)          # MOUSEEVENTF_WHEEL


def find_ffmpeg():
    for p in ("ffmpeg",):
        if shutil.which(p):
            return p
    root = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages")
    for dirpath, _, files in os.walk(root):
        if "ffmpeg.exe" in files:
            return os.path.join(dirpath, "ffmpeg.exe")
    raise SystemExit("ffmpeg not found")


def main():
    hwnd = find_rinx()
    if not hwnd:
        raise SystemExit("no Rinx window found - is it running with the app open?")
    shutil.rmtree(FRAMES, ignore_errors=True)
    os.makedirs(FRAMES, exist_ok=True)
    os.makedirs(os.path.dirname(OUT_MP4), exist_ok=True)

    state = {"n": 0}

    def emit(hold):
        for _ in range(hold):
            force_front(hwnd)
            state["n"] += 1
            capture(hwnd, os.path.join(FRAMES, "%05d.png" % state["n"]))

    emit(3)                                  # default state (empty memory)
    # 1) 说一句习惯 -> 习惯卡 -> 确认（写进长期记忆）
    click(hwnd, CHIP_PREF, CHIP_Y)
    time.sleep(0.7)
    emit(1)
    emit(2)
    force_front(hwnd)
    spot = find_primary(hwnd)
    print("primary button at %s" % (spot,))
    if spot:
        click(hwnd, spot[0], spot[1])
        time.sleep(0.7)
        emit(3)                              # 已记下 + 记忆条更新（你：不坐飞机）
    # 2) 再说一件事 -> 出行卡（带"记忆行"）-> 确认
    click(hwnd, CHIP_TRIP, CHIP_Y)
    time.sleep(0.7)
    emit(1)
    emit(2)
    force_front(hwnd)
    spot2 = find_primary(hwnd)
    if not spot2:                            # 卡片高，按钮可能在窗口外 —— 滚一下
        print("primary not visible; scrolling")
        wheel(hwnd, 3)
        time.sleep(0.7)
        emit(1)
        force_front(hwnd)
        spot2 = find_primary(hwnd)
    print("primary button at %s" % (spot2,))
    if spot2:
        click(hwnd, spot2[0], spot2[1])
        time.sleep(0.7)
        emit(3)                              # 记住 2 张卡
    n = state["n"]
    print("frames: %d (%.1fs)" % (n, n / float(FPS)))

    ff = find_ffmpeg()
    r = subprocess.run(
        [ff, "-y", "-framerate", str(FPS), "-i", os.path.join(FRAMES, "%05d.png"),
         "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
         "-movflags", "+faststart", OUT_MP4],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit("ffmpeg failed:\n" + (r.stderr or "")[-500:])
    print("wrote %s (%d bytes)" % (OUT_MP4, os.path.getsize(OUT_MP4)))


if __name__ == "__main__":
    main()
