#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render every card in cards/ through the official reference host.

For each screen this script:

  1. assembles a throw-away bundle under build/_run/<screen>/bundle/ —
     the shared kit, the screen's page.card and page.data.json, and the
     app's identity files copied from the published bundle;
  2. stamps it with the official `hub` binary;
  3. launches `card-host` (the Hub's own reference host) on it;
  4. finds the port the host opened for its instrument, waits for a frame,
     and captures the app's own drawable;
  5. crops the host's title bar off and stores the result in
     cards/<screen>/screenshots/01.png.

Stdlib only. No third-party packages. Nothing here touches the published
bundle: build/_run/ is scratch.

Usage:
    python build/render_cards.py                # all screens, in order
    python build/render_cards.py shiyi-02-ask   # one screen
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE = os.path.join(ROOT, "bundle")
CARDS = os.path.join(ROOT, "cards")
BUILD = os.path.join(ROOT, "build")
RUN = os.path.join(BUILD, "_run")
SHOTS = os.path.join(BUILD, "shots")

HUB_EXE = "F:/gosim_build/cache/target/debug/hub.exe"
CARD_HOST_EXE = "F:/gosim_build/cache/target/debug/card-host.exe"
HUB_REPO = "F:/gosim_build/octosense-org/OctoSense-App-Hub"

TITLE_BAR = 42  # the host draws its own bar above the card

SCREENS = [
    "shiyi-01-read",
    "shiyi-02-ask",
    "shiyi-03-plan",
    "shiyi-04-memo",
    "shiyi-05-done",
]


def log(msg):
    print(msg, flush=True)


def make_run_bundle(screen):
    """Assemble build/_run/<screen>/bundle from the shared kit + one card."""
    dst = os.path.join(RUN, screen)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    b = os.path.join(dst, "bundle")
    os.makedirs(b)

    for name in ("manifest.json", "listing.json"):
        shutil.copy2(os.path.join(BUNDLE, name), os.path.join(b, name))
    # The published manifest is signed; card-host verifies no publisher keys, so
    # a signed manifest is refused even with --allow-unsigned. The scratch copy
    # is re-stamped and run unsigned; clear the signature here only.
    mp = os.path.join(b, "manifest.json")
    m = json.load(open(mp, encoding="utf-8"))
    m["integrity"]["signature"] = None
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    shutil.copytree(os.path.join(BUNDLE, "kit"), os.path.join(b, "kit"))
    if os.path.isdir(os.path.join(BUNDLE, "assets")):
        shutil.copytree(os.path.join(BUNDLE, "assets"), os.path.join(b, "assets"))

    src = os.path.join(CARDS, screen)
    for name in ("page.card", "page.data.json"):
        shutil.copy2(os.path.join(src, name), os.path.join(b, name))
    os.makedirs(os.path.join(b, "screenshots"), exist_ok=True)
    return b


# Windows consoles hand back OEM-encoded bytes; we only ever read ASCII
# (ports, PIDs, digests) so decode leniently rather than crash.
TEXT = {"capture_output": True, "text": True, "encoding": "utf-8",
        "errors": "replace"}


def _run(cmd, **kw):
    opts = dict(TEXT)
    opts.update(kw)
    return subprocess.run(cmd, **opts)


def stamp(bundle):
    r = _run([HUB_EXE, "stamp", bundle], cwd=HUB_REPO)
    if r.returncode != 0:
        raise RuntimeError("stamp failed: " + ((r.stdout or "") + (r.stderr or "")).strip())
    return (r.stdout or "").strip()


def listening_ports(pid):
    """Ports the process is listening on, via netstat. Buffer-proof."""
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
    """The host answers GET / with its protocol description."""
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


def render(screen):
    log("── %s ──" % screen)
    bundle = make_run_bundle(screen)
    log("   stamped: %s" % (stamp(bundle) or "ok"))

    logf = open(os.path.join(RUN, screen, "host.log"), "wb")
    state = os.path.join(RUN, screen, "state")
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
                raise RuntimeError("host exited early (rc=%s); see %s/host.log"
                                   % (proc.returncode, os.path.join(RUN, screen)))
            for p in listening_ports(proc.pid):
                if is_instrument(p):
                    port = p
                    break
            if port:
                break
            time.sleep(0.4)
        if not port:
            raise RuntimeError("no instrument port found within 40s")

        log("   host up on 127.0.0.1:%d (pid %d)" % (port, proc.pid))

        # Wait for a rendered frame: keep asking for a capture until the bytes
        # are a real PNG of plausible size.
        shot = os.path.join(SHOTS, screen + ".png")
        os.makedirs(SHOTS, exist_ok=True)
        got = 0
        last = None
        for attempt in range(25):
            try:
                data = fetch(port, "/g?raw=1", out=shot, timeout=20)
                if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) > 5000:
                    got = len(data)
                    break
                last = "small or not a png (%d bytes)" % len(data)
            except Exception as e:  # noqa: BLE001 - report and retry
                last = str(e)
            time.sleep(1.0)
        if not got:
            raise RuntimeError("no usable capture: %s" % last)
        log("   captured %d bytes -> %s" % (got, shot))

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

    # Crop the host's own title bar off; the card is what we keep.
    dst_dir = os.path.join(CARDS, screen, "screenshots")
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, "01.png")
    crop = _run(
        [sys.executable, os.path.join(BUILD, "crop_png.py"),
         os.path.join(SHOTS, screen + ".png"), dst, str(TITLE_BAR)])
    if crop.returncode != 0:
        raise RuntimeError("crop failed: " + ((crop.stdout or "") + (crop.stderr or "")).strip())
    tail = (crop.stdout or "").strip().splitlines()
    log("   %s" % (tail[-1] if tail else dst))
    return dst


def main():
    wanted = sys.argv[1:] or SCREENS
    done, failed = [], []
    for s in wanted:
        try:
            done.append(render(s))
        except Exception as e:  # noqa: BLE001 - one screen failing is not fatal
            log("   FAILED: %s" % e)
            failed.append((s, str(e)))
    log("")
    log("done: %d" % len(done))
    for d in done:
        log("  ok  %s" % d)
    for s, e in failed:
        log("  ERR %s — %s" % (s, e))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
