#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给一个 L0 bundle 抓一张**真实截图**（用官方参考宿主 card-host）。

card-host 自带 instrument HTTP 端口，直接把它画出来的那一帧吐出来
（`/g?raw=1`），所以不依赖 X11 截屏 —— 宿主真正画了什么，就存下来什么。

    python build/shot_bundle.py <bundle_dir>

过程：stamp -> 起 card-host(--remote) -> 找 instrument 端口 -> 取帧 ->
裁掉宿主自己的标题栏 -> 存 <bundle>/screenshots/01.png -> 更新 listing ->
再 stamp（截图进了 bundle，digest 跟着变）。

只写这一个 bundle 目录；不改仓里任何既有文件。
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")

HUB_EXE = "F:/gosim_build/cache/target/debug/hub.exe"
CARD_HOST_EXE = "F:/gosim_build/cache/target/debug/card-host.exe"
HUB_REPO = "F:/gosim_build/octosense-org/OctoSense-App-Hub"
TITLE_BAR = 42

TEXT = {"capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace"}


def log(m):
    print(m, flush=True)


def _run(cmd, **kw):
    o = dict(TEXT)
    o.update(kw)
    return subprocess.run(cmd, **o)


def stamp(b):
    r = _run([HUB_EXE, "stamp", b], cwd=HUB_REPO)
    if r.returncode != 0:
        raise RuntimeError("stamp failed: " + ((r.stdout or "") + (r.stderr or "")).strip())
    return (r.stdout or "").strip()


def listening_ports(pid):
    try:
        out = _run(["netstat", "-ano", "-p", "TCP"], timeout=15).stdout or ""
    except Exception:
        return []
    ports = []
    for line in out.splitlines():
        if "LISTENING" not in line:
            continue
        parts = line.split()
        if len(parts) < 5 or parts[-1] != str(pid):
            continue
        m = re.search(r":(\d+)$", parts[1])
        if m:
            ports.append(int(m.group(1)))
    return ports


def is_instrument(port):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=2) as r:
            body = r.read(4000).decode("utf-8", "replace")
        return "makepad" in body.lower() or "remote" in body.lower()
    except Exception:
        return False


def fetch(port, path, out=None, timeout=30):
    url = "http://127.0.0.1:%d%s" % (port, path)
    with urllib.request.urlopen(url, timeout=timeout) as r:
        data = r.read()
    if out:
        with open(out, "wb") as f:
            f.write(data)
    return data


def shot(bundle):
    log("── %s ──" % bundle)
    stamp(bundle)

    work = os.path.dirname(bundle)
    logf = open(os.path.join(work, "host.log"), "wb")
    state = os.path.join(work, "state")
    os.makedirs(state, exist_ok=True)
    proc = subprocess.Popen(
        [CARD_HOST_EXE, "--bundle", bundle, "--app-data", state,
         "--allow-unsigned", "--remote"],
        cwd=HUB_REPO, stdout=logf, stderr=subprocess.STDOUT)

    port = None
    deadline = time.time() + 40
    try:
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError("host exited early (rc=%s); see %s/host.log" % (proc.returncode, work))
            for p in listening_ports(proc.pid):
                if is_instrument(p):
                    port = p
                    break
            if port:
                break
            time.sleep(0.4)
        if not port:
            raise RuntimeError("no instrument port within 40s")

        log("   host up on 127.0.0.1:%d (pid %d)" % (port, proc.pid))

        raw = os.path.join(work, "_raw.png")
        got = 0
        last = None
        for _ in range(25):
            try:
                data = fetch(port, "/g?raw=1", out=raw, timeout=20)
                if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) > 5000:
                    got = len(data)
                    break
                last = "small/not png (%d bytes)" % len(data)
            except Exception as e:  # noqa: BLE001
                last = str(e)
            time.sleep(1.0)
        if not got:
            raise RuntimeError("no usable capture: %s" % last)

        try:
            fetch(port, "/quit", timeout=5)
        except Exception:
            pass
    finally:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
        logf.close()

    shots = os.path.join(bundle, "screenshots")
    os.makedirs(shots, exist_ok=True)
    dst = os.path.join(shots, "01.png")
    crop = _run([sys.executable, os.path.join(BUILD, "crop_png.py"), raw, dst, str(TITLE_BAR)])
    if crop.returncode != 0:
        raise RuntimeError("crop failed: " + ((crop.stdout or "") + (crop.stderr or "")).strip())
    log("   captured %d bytes -> %s" % (got, dst))

    lp = os.path.join(bundle, "listing.json")
    listing = json.load(open(lp, encoding="utf-8"))
    listing["screenshots"] = ["screenshots/01.png"]
    with open(lp, "w", encoding="utf-8") as f:
        json.dump(listing, f, ensure_ascii=False, indent=2)
        f.write("\n")
    stamp(bundle)
    return dst


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[3])
        sys.exit(2)
    try:
        shot(os.path.abspath(sys.argv[1]))
    except Exception as e:  # noqa: BLE001
        log("FAILED: %s" % e)
        sys.exit(1)
