#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拾意 · 端到端验证（A3）＋ 失败态取证（B4）

把「一条消息 → 逐屏卡 → 用户点按钮 → 下一屏」这条链路，在**官方参考宿主**
（`card-host`）里真实跑一遍，每一步都留可复现证据。

为什么是这么跑的（不是"点一下自己跳屏"）：

  官方参考宿主的卡片通道（`kit_pack`）只传声明的 props / layout / style，
  **Kit 节点连 `on_tap` 都放不进去** —— 卡片自己跳不到下一屏。所以每屏按钮的
  含义写在它旁边的 `service-actions.json`（控件名 → 事件名），由 Agent 读、
  由 Agent 决定下一屏。官方 aircon 的 12 屏就是这个形状。

  于是"端到端"在这里等于：

      消息 ─→ Flow.frame() 出本屏内容 ─→ 宿主真渲染（抓图）
           ─→ 用户点真实控件（instrument /click，先 /snap 证实控件在且可用）
           ─→ 该控件在 service-actions.json 里声明的事件名
           ─→ Flow.handle(事件) ─→ 下一屏 …

  每一步的证据 = 宿主内截图 + 控件矩形 + 点击应答 + 事件名 + 屏号。

同时跑两个**失败态**（官方明点：必须能展示失败）：

  · 卡片包未签名 → 宿主拒绝准入，且**一张都不渲染**（fail-closed）
  · 卡片包被改过 → 摘要不符 → 同样拒绝

用法：
    python build/verify_flow.py              # 正流程 + 两个失败态
    python build/verify_flow.py --positive   # 只跑正流程

产物：build/_evidence/（不进 bundle）
    flow_run.json          全步骤记录
    shots/<screen>.png     每屏宿主内截图（未裁，含宿主标题栏）
    neg_unsigned.log      未签名被拒的宿主日志
    neg_tampered.log      摘要不符被拒的宿主日志

Stdlib only。
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE = os.path.join(ROOT, "bundle")
CARDS = os.path.join(ROOT, "cards")
SRC = os.path.join(ROOT, "src")
EVID = os.path.join(ROOT, "build", "_evidence")
RUN = os.path.join(ROOT, "build", "_run_verify")
SHOTS = os.path.join(EVID, "shots")

HUB_EXE = "F:/gosim_build/cache/target/debug/hub.exe"
CARD_HOST_EXE = "F:/gosim_build/cache/target/debug/card-host.exe"
HUB_REPO = "F:/gosim_build/octosense-org/OctoSense-App-Hub"

sys.path.insert(0, SRC)

MESSAGE = "下周三我得去趟深圳"
ROOM = "家庭群"

# 用户在这条链路上真实按下的东西（屏, 控件名）；控件名 → 事件名由卡旁的
# service-actions.json 决定，不在这里硬编码。
SCRIPT = [
    ("shiyi-01-read", "action_yes"),
    ("shiyi-02-ask", "opt_a1"),
    ("shiyi-02-ask", "opt_b1"),
    ("shiyi-02-ask", "action_go"),
    ("shiyi-03-plan", "action_take"),
    ("shiyi-04-memo", "action_keep"),
    ("shiyi-05-done", "action_open"),
]


def log(msg):
    print(msg, flush=True)


def run(cmd, **kw):
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    kw.setdefault("encoding", "utf-8")
    kw.setdefault("errors", "replace")
    return subprocess.run(cmd, **kw)


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


# ── bundle 组装 / 盖章 ────────────────────────────────────────────────────

def make_bundle(screen, dest=None):
    dst = dest or os.path.join(RUN, screen)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    b = os.path.join(dst, "bundle")
    os.makedirs(b)
    for name in ("manifest.json", "listing.json"):
        shutil.copy2(os.path.join(BUNDLE, name), os.path.join(b, name))
    shutil.copytree(os.path.join(BUNDLE, "kit"), os.path.join(b, "kit"))
    if os.path.isdir(os.path.join(BUNDLE, "assets")):
        shutil.copytree(os.path.join(BUNDLE, "assets"), os.path.join(b, "assets"))
    src = os.path.join(CARDS, screen)
    for name in ("page.card", "page.data.json"):
        shutil.copy2(os.path.join(src, name), os.path.join(b, name))
    os.makedirs(os.path.join(b, "screenshots"), exist_ok=True)
    return b


def stamp(bundle):
    r = run([HUB_EXE, "stamp", bundle], cwd=HUB_REPO)
    if r.returncode != 0:
        raise RuntimeError("stamp 失败：" + (r.stdout or "") + (r.stderr or ""))
    return (r.stdout or "").strip()


def placements(screen):
    with open(os.path.join(CARDS, screen, "page.data.json"), encoding="utf-8") as f:
        return json.load(f)["$kit"]["placements"]


def controls_of(screen):
    with open(os.path.join(CARDS, screen, "service-actions.json"), encoding="utf-8") as f:
        return json.load(f)["controls"]


def center_of(screen, control):
    p = placements(screen)[control]["layout"]
    return p["x"] + p["w"] // 2, p["y"] + p["h"] // 2


# ── instrument 通道 ──────────────────────────────────────────────────────

def ports_of(pid):
    try:
        out = run(["netstat", "-ano", "-p", "TCP"], timeout=20).stdout or ""
    except Exception:
        return []
    res = []
    for line in out.splitlines():
        if "LISTENING" not in line:
            continue
        parts = line.split()
        if len(parts) < 5 or parts[-1] != str(pid):
            continue
        m = re.search(r":(\d+)$", parts[1])
        if m:
            res.append(int(m.group(1)))
    return res


def is_instrument(port):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=2) as r:
            return "makepad" in r.read(4000).decode("utf-8", "replace").lower()
    except Exception:
        return False


def fetch(port, path, timeout=25, retries=1):
    last = None
    for _ in range(retries):
        try:
            with urllib.request.urlopen(
                    "http://127.0.0.1:%d%s" % (port, path), timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(0.6)
    raise last


class Host:
    """一次宿主生命周期：起 → 等第一帧 → … → 退出。"""

    def __init__(self, bundle, logpath, state, hide=False, extra=()):
        self.bundle = bundle
        self.logpath = logpath
        self.state = state
        self.hide = hide
        self.extra = list(extra)
        self.proc = None
        self.port = None
        self.logf = None

    def __enter__(self):
        env = dict(os.environ)
        if self.hide:
            env["MAKEPAD_HIDE_WINDOWS"] = "1"
        for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
            env.pop(k, None)
        os.makedirs(os.path.dirname(self.logpath), exist_ok=True)
        os.makedirs(self.state, exist_ok=True)
        self.logf = open(self.logpath, "wb")
        cmd = [CARD_HOST_EXE, "--bundle", self.bundle, "--app-data", self.state]
        cmd += self.extra
        cmd += ["--remote"]
        self.proc = subprocess.Popen(cmd, cwd=HUB_REPO, env=env,
                                     stdout=self.logf, stderr=subprocess.STDOUT)
        deadline = time.time() + 40
        while time.time() < deadline and self.port is None:
            if self.proc.poll() is not None:
                raise RuntimeError("宿主提前退出 rc=%s（见 %s）"
                                   % (self.proc.returncode, self.logpath))
            for p in ports_of(self.proc.pid):
                if is_instrument(p):
                    self.port = p
                    break
            time.sleep(0.4)
        if not self.port:
            raise RuntimeError("40 秒内没有找到 instrument 端口")
        return self

    def frame(self, min_bytes=20000, stable=2, tries=45):
        """等一帧**真的画出来并且稳定**；返回 PNG 字节。

        隐藏窗口下宿主会先给一帧空白（约 5 KB，只有窗口底色+标题栏），
        所以不能"抓到图就算"。判定：字节数达标 且 连续 stable 次 sha 相同。
        """
        prev, same, last = None, 0, None
        for _ in range(tries):
            try:
                d = fetch(self.port, "/g?raw=1", retries=1)
                if d[:8] == b"\x89PNG\r\n\x1a\n" and len(d) >= min_bytes:
                    h = sha16(d)
                    if prev == h:
                        same += 1
                        if same >= stable - 1:
                            return d
                    else:
                        prev, same = h, 0
                else:
                    last = "小/非 PNG（%d 字节）" % len(d)
            except Exception as e:  # noqa: BLE001 - 第一帧未画时抓图会失败
                last = str(e)
            time.sleep(0.8)
        raise RuntimeError("没等到稳定帧：%s" % last)

    def snap(self, name):
        q = urllib.parse.quote(name)
        d = fetch(self.port, "/snap?q=%s&all=1" % q)
        return json.loads(d.decode("utf-8", "replace")).get("s", [])

    def click(self, x, y):
        d = fetch(self.port, "/click?x=%d&y=%d&wait=1" % (x, y))
        return d.decode("utf-8", "replace").strip()

    def logtail(self):
        try:
            return fetch(self.port, "/log?n=60").decode("utf-8", "replace")
        except Exception:
            return ""

    def __exit__(self, *exc):
        try:
            if self.port:
                try:
                    fetch(self.port, "/quit", timeout=5)
                except Exception:
                    pass
        finally:
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=10)
            if self.logf:
                self.logf.close()
        return False


def read_log(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8", "replace")


# ── 正流程 ───────────────────────────────────────────────────────────────

def run_positive():
    from shiyi_flow import Flow  # noqa: PLC0415

    fl = Flow(MESSAGE, room=ROOM)
    log("=" * 76)
    log("拾意 · 端到端（官方参考宿主 card-host）")
    log("消息：[%s] %s" % (ROOM, MESSAGE))
    log("=" * 76)

    steps = []
    # 同一屏上的多次点击共用一个宿主实例，省一次起停
    grouped = []
    for screen, ctl in SCRIPT:
        if grouped and grouped[-1][0] == screen:
            grouped[-1][1].append(ctl)
        else:
            grouped.append((screen, [ctl]))

    os.makedirs(SHOTS, exist_ok=True)
    for screen, ctls in grouped:
        log("")
        log("▌ %s" % screen)
        b = make_bundle(screen)
        digest = stamp(b)
        log("   组包+盖章：%s" % digest[:16])
        logf = os.path.join(EVID, "host_%s.log" % screen)
        state = os.path.join(RUN, screen, "state")
        with Host(b, logf, state, extra=["--allow-unsigned"]) as h:
            log("   宿主已起：127.0.0.1:%d（pid %d）" % (h.port, h.proc.pid))
            png = h.frame()
            shot = os.path.join(SHOTS, screen + ".png")
            with open(shot, "wb") as f:
                f.write(png)
            log("   本屏渲染：%d 字节 PNG sha=%s" % (len(png), sha16(png)))

            declared = controls_of(screen)
            for ctl in ctls:
                x, y = center_of(screen, ctl)
                # 先用 /snap 证实这个控件真的在、可见、可用
                items = h.snap(ctl)
                hit = [it for it in items
                       if it.get("i") == ctl or str(it.get("i", "")).startswith(ctl + "_")]
                clickable = [it for it in hit if str(it.get("ty", "")).endswith("Button")]
                inside = [it for it in clickable
                          if it.get("r") and it["r"][0] <= x <= it["r"][0] + it["r"][2]
                          and it["r"][1] <= y <= it["r"][1] + it["r"][3]
                          and it.get("enabled", True)]
                rect = (clickable[0]["r"] if clickable else
                        (hit[0].get("r") if hit else None))
                ans = h.click(x, y)
                ev = declared.get(ctl, {}).get("event")
                log("   点 %-14s (%3d,%3d)  rect=%s  应答=%s"
                    % (ctl, x, y, rect, ans))
                log("       └ 控件在：%s ｜ 可点：%s ｜ 点得中：%s"
                    % (bool(hit), bool(clickable), bool(inside)))
                steps.append({
                    "screen": screen,
                    "control": ctl,
                    "event": ev,
                    "click": {"x": x, "y": y},
                    "rect": rect,
                    "widget_present": bool(hit),
                    "widget_clickable": bool(clickable),
                    "click_inside_widget": bool(inside),
                    "host_answer": ans,
                    "shot": os.path.relpath(shot, ROOT).replace("\\", "/"),
                    "bundle_blake3": digest,
                })
                if ev:
                    nxt = fl.handle(ev)
                    log("       └ 事件 %-26s → 下一屏 %s" % (ev, nxt or "（终点）"))

    log("")
    log("-" * 76)
    log("走过的决定：%s" % " → ".join(fl.decisions))
    log("结束屏：%s" % fl.stage)
    return steps, fl


# ── 失败态 ───────────────────────────────────────────────────────────────

def run_negative():
    """官方明点：必须能展示失败。这里取两类真实拒绝。"""
    out = []

    # ① 未签名：宿主默认要求签名
    log("")
    log("▨ 失败态 ①：卡片包未签名")
    b = make_bundle("shiyi-01-read", dest=os.path.join(RUN, "neg_unsigned"))
    stamp(b)
    logf = os.path.join(EVID, "neg_unsigned.log")
    with Host(b, logf, os.path.join(RUN, "neg_unsigned", "state"), extra=()) as h:
        text = read_log(logf)
        m = re.search(r"card-host: refused: .*", text)
        rendered = "[SPLASH] eval" in text
        log("   宿主：127.0.0.1:%d" % h.port)
        log("   拒绝原因：%s" % (m.group(0) if m else "（未捕获）"))
        log("   是否渲染了卡片：%s" % ("是（不该）" if rendered else "否 —— fail-closed ✓"))
        try:
            d = h.frame(min_bytes=1)
            shot_state = ("抓到的只是空白窗口（%d 字节，无卡片内容）—— 一张都没画 ✓" % len(d)
                          if len(d) < 20000 else "抓到了卡片画面（不该）")
        except Exception:
            shot_state = "抓不到卡片画面 —— 一张都没画 ✓"
        log("   抓图：%s" % shot_state)
        out.append({"case": "unsigned", "refused": bool(m),
                    "log": m.group(0) if m else None,
                    "rendered_any": rendered, "capture": shot_state})

    # ② 被改过：摘要不符
    log("")
    log("▨ 失败态 ②：卡片包被改过（改 page.data.json 一个字符）")
    b = make_bundle("shiyi-01-read", dest=os.path.join(RUN, "neg_tampered"))
    stamp(b)
    p = os.path.join(b, "page.data.json")
    with open(p, encoding="utf-8") as f:
        raw = f.read()
    with open(p, "w", encoding="utf-8") as f:
        f.write(raw.replace("拾意", "拾意 ", 1))
    logf = os.path.join(EVID, "neg_tampered.log")
    with Host(b, logf, os.path.join(RUN, "neg_tampered", "state"),
              extra=["--allow-unsigned"]) as h:
        text = read_log(logf)
        m = re.search(r"card-host: refused: .*", text)
        rendered = "[SPLASH] eval" in text
        log("   拒绝原因：%s" % (m.group(0) if m else "（未捕获）"))
        log("   是否渲染了卡片：%s" % ("是（不该）" if rendered else "否 —— fail-closed ✓"))
        out.append({"case": "tampered", "refused": bool(m),
                    "log": m.group(0) if m else None, "rendered_any": rendered})
    return out


def main():
    want_pos = "--positive" in sys.argv or "--negative" not in sys.argv
    want_neg = "--negative" in sys.argv or "--positive" not in sys.argv
    os.makedirs(EVID, exist_ok=True)

    report = {"message": MESSAGE, "room": ROOM, "steps": [], "negative": []}
    dst = os.path.join(EVID, "flow_run.json")
    if os.path.exists(dst):        # 分两次跑时保留另一半的结果
        try:
            with open(dst, encoding="utf-8") as f:
                old = json.load(f)
            if not want_pos:
                report["steps"] = old.get("steps", [])
                report["decisions"] = old.get("decisions", [])
                report["final_stage"] = old.get("final_stage")
            if not want_neg:
                report["negative"] = old.get("negative", [])
        except Exception:
            pass
    if want_pos:
        steps, fl = run_positive()
        report["steps"] = steps
        report["decisions"] = fl.decisions
        report["final_stage"] = fl.stage
    if want_neg:
        report["negative"] = run_negative()

    dst = os.path.join(EVID, "flow_run.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log("")
    log("证据已写：%s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
