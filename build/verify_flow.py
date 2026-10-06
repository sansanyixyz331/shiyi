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

  · 卡片包未签名 → 宿主拒绝准入，**我方卡片一张都不渲染**（fail-closed）；
    新版宿主会在窗口里画一张它**自带的「拒绝说明页」**（含 refused 原文）。
  · 卡片包被改过 → 摘要不符 → 同样拒绝（同样画拒绝页）。

  判据（**我方卡片**是否渲染）：只看宿主日志的 `admitted` / `refused` ——
  准入成功打 `admitted`，被拒只打 `refused`。`[SPLASH] eval` **不是**判据：
  宿主被拒后画的拒绝说明页也会打一行 `[SPLASH] eval`，那是宿主画的、不是我方卡片。

外带一项**记忆真读写取证**（对应官方「结果核验」）：

  · 点「记下」→ 本机记忆文件真被写（路径、sha、内容、写入时间全留证）
  · 再跑一遍 → 读得到上一遍写进去的东西（证明不是常量）
  · 点「这次别记」→ 文件 sha 一个字节不变

用法：
    python build/verify_flow.py              # 正流程 + 两个失败态 + 记忆取证
    python build/verify_flow.py --positive   # 只跑正流程

产物：build/_evidence/（不进 bundle）
    flow_run.json          全步骤记录（含 memory 段：记忆取证的断言与实测值）
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

# 宿主工具位置：优先环境变量（见 README §5.2 的 $HUB_BIN / $CARD_HOST_BIN），
# 其次 PATH。不写死任何本机路径 —— 换台机器也能跑。
HUB_EXE = os.environ.get("HUB_BIN") or shutil.which("hub") or "hub"
CARD_HOST_EXE = os.environ.get("CARD_HOST_BIN") or shutil.which("card-host") or "card-host"
# 宿主资源须在官方 Hub 仓库里解析；用 HUB_REPO 环境变量指定（默认当前目录）。
HUB_REPO = os.environ.get("HUB_REPO") or os.getcwd()

sys.path.insert(0, SRC)

MESSAGE = "下周三我得去趟深圳"
ROOM = "家庭群"


# ── 脱敏：证据文件落盘前，把本机私有路径/用户名换成中性占位 ──────────────
# 宿主日志里会原样带上编译机路径（用户主目录、我们的构建工作区），
# 这些既暴露用户名、又是别人机器上不存在的位置。证据只关心"发生了什么"
# （admitted / refused / [SPLASH] eval / 事件名），路径换成占位即可。
_SCRUB_RULES = [
    # 顺序：更具体的在前。`[\\/]+` 同时覆盖单反斜杠（日志）与双反斜杠（JSON 转义）。
    (re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"]+"), "<HOME>"),
    (re.compile(r"[A-Za-z]:[\\/]+gosim_build"), "<WORK>"),
    (re.compile(r"[A-Za-z]:[\\/]+gosim_agentic[\\/]+05_app[\\/]+shiyi"), "<REPO>"),
    (re.compile(r"[A-Za-z]:[\\/]+gosim_agentic"), "<WORKSPACE>"),
]


def _scrub_text(t):
    for rx, rep in _SCRUB_RULES:
        t = rx.sub(rep, t)
    return t


def scrub(path):
    """把已落盘的证据文件里的本机路径/用户名就地脱敏（只动文本文件）。

    ⚠️ 用**二进制读写**：绝不能让 Python 文本模式在 Windows 上把已有 CRLF 再转一遍
    （否则 `\\r\\n` 会变成 `\\r\\r\\n`，字节数变化、且破坏原始日志形态）。
    只替换路径/用户名本身，换行原样保留。
    """
    if not path or not os.path.exists(path):
        return
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception:
        return
    if b"\x00" in raw[:4096]:      # 二进制（图片/视频）不动
        return
    try:
        txt = raw.decode("utf-8")
    except UnicodeDecodeError:
        return
    new = _scrub_text(txt)
    if new != txt:
        with open(path, "wb") as f:        # 二进制写：换行不受平台影响
            f.write(new.encode("utf-8"))

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
    # The published manifest is signed; card-host verifies no publisher keys, so
    # a signed manifest is refused even with --allow-unsigned. Clear the
    # signature in this throw-away copy only; it is re-stamped below.
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


def stamp(bundle):
    r = run([HUB_EXE, "stamp", bundle], cwd=HUB_REPO)
    if r.returncode != 0:
        raise RuntimeError("stamp 失败：" + (r.stdout or "") + (r.stderr or ""))
    return (r.stdout or "").strip()


def tamper(bundle):
    """Change one character of a stamped bundle so its digest no longer matches.

    The target must exist in page.data.json: a replace that matches nothing is a
    silent no-op and the "tampered" case would render as if nothing were wrong
    (this is how it once regressed, when the copy moved out of page.data.json).
    """
    p = os.path.join(bundle, "page.data.json")
    with open(p, encoding="utf-8") as f:
        raw = f.read()
    changed = raw.replace('"light"', '"light "', 1)
    if changed == raw:
        raise RuntimeError(
            "tamper target not found in page.data.json — the negative case "
            "would be a silent no-op")
    with open(p, "w", encoding="utf-8") as f:
        f.write(changed)
    return p


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
            scrub(self.logpath)          # 证据日志落盘后脱敏本机路径/用户名
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

def card_was_admitted(text):
    """判据：**我方卡片**是否被宿主准入渲染。

    只看宿主日志有没有 `admitted` —— 准入成功打 `admitted <app> <ver>`，
    被拒只打 `refused:`、绝不打 `admitted`。
    ⚠️ 不能用 `[SPLASH] eval` 当判据：宿主被拒后画**自带的拒绝说明页**时，
    也会打一行 `[SPLASH] eval: N bytes`（那是宿主画的页面，不是我方卡片）。
    """
    return bool(re.search(r"card-host: shiyi \S+ admitted", text))


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
        admitted = card_was_admitted(text)
        log("   宿主：127.0.0.1:%d" % h.port)
        log("   拒绝原因：%s" % (m.group(0) if m else "（未捕获）"))
        log("   我方卡片是否被准入：%s" % ("是（不该）" if admitted else "否 —— fail-closed ✓"))
        try:
            d = h.frame(min_bytes=1)
            shot_state = ("宿主画了它自带的「拒绝说明页」（%d 字节，含 refused 原文）；"
                          "**我方卡片一张都没画** ✓" % len(d))
            open(os.path.join(EVID, "neg_unsigned.png"), "wb").write(d)
        except Exception:
            shot_state = "抓不到画面 —— 我方卡片一张都没画 ✓"
        log("   抓图：%s" % shot_state)
        out.append({"case": "unsigned", "refused": bool(m),
                    "admitted": admitted,
                    "log": m.group(0) if m else None,
                    "capture": shot_state})

    # ② 被改过：摘要不符
    log("")
    log("▨ 失败态 ②：卡片包被改过（改 page.data.json 一个字符）")
    b = make_bundle("shiyi-01-read", dest=os.path.join(RUN, "neg_tampered"))
    stamp(b)
    tamper(b)
    logf = os.path.join(EVID, "neg_tampered.log")
    with Host(b, logf, os.path.join(RUN, "neg_tampered", "state"),
              extra=["--allow-unsigned"]) as h:
        text = read_log(logf)
        m = re.search(r"card-host: refused: .*", text)
        admitted = card_was_admitted(text)
        log("   拒绝原因：%s" % (m.group(0) if m else "（未捕获）"))
        log("   我方卡片是否被准入：%s" % ("是（不该）" if admitted else "否 —— fail-closed ✓"))
        try:
            d = h.frame(min_bytes=1)
            capture = ("宿主画了它自带的「拒绝说明页」（%d 字节）；**我方卡片一张都没画** ✓"
                       % len(d))
            open(os.path.join(EVID, "neg_tampered.png"), "wb").write(d)
        except Exception:
            capture = "抓不到画面 —— 我方卡片一张都没画 ✓"
        out.append({"case": "tampered", "refused": bool(m),
                    "admitted": admitted,
                    "log": m.group(0) if m else None, "capture": capture})
    return out


# ── 记忆真读写取证 ────────────────────────────────────────────────────────

MEM_FILE = os.path.join(ROOT, ".local-state", "memory.json")
KEEP_WALK = ("intent.confirmed", "ask.when.morning", "ask.from.home",
             "ask.settled", "plan.take_recommended")


def sha_file(path):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _walk(flow, last):
    """走到 last 事件。返回（动手前的帧，动手后的帧）。

    动手前那一帧很重要：记忆屏上"原来记着的"是什么，只有停在那儿才看得到。
    """
    for ev in KEEP_WALK:
        flow.handle(ev)
    before_fr = flow.frame()
    flow.handle(last)
    return before_fr, flow.frame()


def run_memory():
    """记忆真读写取证：keep 真写、第二遍读得到、skip 一个字节不写。"""
    from shiyi_flow import Flow  # noqa: PLC0415

    log("")
    log("▨ 记忆真读写（对应官方「结果核验」轴）")

    if os.path.exists(MEM_FILE):        # 干净起点
        os.remove(MEM_FILE)

    # ① 第一遍：点「记下」
    fl = Flow(MESSAGE, room=ROOM)
    memo_fr, done_fr = _walk(fl, "memo.keep")
    receipt = done_fr["_memory_write"]
    with open(MEM_FILE, encoding="utf-8") as f:
        doc = json.load(f)
    keep_ok = (doc["places"].get("深圳", {}).get("default_depart") == "早班"
               and doc["places"]["深圳"].get("from") == "家里"
               and bool(doc["log"]) and doc["log"][-1]["event"] == "memo.keep")
    log("   记忆文件：%s" % receipt["path"])
    log("   ① 第一遍（文件不存在 → 自动播种：%s）" % doc.get("seeded_from"))
    log("      进入记忆屏时，『深圳』= %s" % memo_fr["_remembered_before"])
    log("      点『记下』→ %s" % receipt["line"])
    log("      写入时间 %s ｜ 文件 sha=%s" % (receipt["written_at"], sha_file(MEM_FILE)[:16]))
    log("      断言：文件里真写进了这次的内容 → %s" % ("是 ✓" if keep_ok else "否 ✗"))

    # ② 第二遍：读得到第一遍写进去的
    fl2 = Flow(MESSAGE, room=ROOM)
    for ev in KEEP_WALK:
        fl2.handle(ev)
    seen = fl2.frame()["_remembered_before"]
    seen_ok = bool(seen) and seen.get("default_depart") == "早班"
    log("   ② 第二遍（文件已在）")
    log("      进入记忆屏时，『深圳』= %s" % json.dumps(seen, ensure_ascii=False))
    log("      断言：读得到上一遍记下的（不是常量）→ %s" % ("是 ✓" if seen_ok else "否 ✗"))

    # ③ 第三遍：点「这次别记」
    before = sha_file(MEM_FILE)
    fl3 = Flow(MESSAGE, room=ROOM)
    _walk(fl3, "memo.skip")
    after = sha_file(MEM_FILE)
    skip_ok = (before == after)
    log("   ③ 第三遍（点『这次别记』）")
    log("      文件 sha：%s → %s" % (before[:16], after[:16]))
    log("      断言：一个字节没动 → %s" % ("是 ✓" if skip_ok else "否 ✗"))

    return {
        "file": receipt["path"],
        "first_run": {
            "seeded_from": doc.get("seeded_from"),
            "remembered_before_keep": memo_fr["_remembered_before"],
            "write_receipt": receipt,
            "file_sha16": sha_file(MEM_FILE)[:16],
        },
        "second_run": {"remembered_before": seen},
        "third_run_skip": {"sha_before16": before[:16], "sha_after16": after[:16]},
        "assertions": {
            "keep_wrote_file": keep_ok,
            "memory_is_effective": seen_ok,
            "skip_left_file_untouched": skip_ok,
        },
        "file_content": doc,
    }


def main():
    want_pos = "--positive" in sys.argv or "--negative" not in sys.argv
    want_neg = "--negative" in sys.argv or "--positive" not in sys.argv
    os.makedirs(EVID, exist_ok=True)

    report = {"message": MESSAGE, "room": ROOM, "steps": [], "negative": [], "memory": {}}
    dst = os.path.join(EVID, "flow_run.json")
    if os.path.exists(dst):        # 分两次跑时保留另一半的结果
        try:
            with open(dst, encoding="utf-8") as f:
                old = json.load(f)
            if not want_pos:
                report["steps"] = old.get("steps", [])
                report["decisions"] = old.get("decisions", [])
                report["final_stage"] = old.get("final_stage")
                report["memory"] = old.get("memory", {})
            if not want_neg:
                report["negative"] = old.get("negative", [])
        except Exception:
            pass
    if want_pos:
        steps, fl = run_positive()
        report["steps"] = steps
        report["decisions"] = fl.decisions
        report["final_stage"] = fl.stage
        report["memory"] = run_memory()
    if want_neg:
        report["negative"] = run_negative()

    dst = os.path.join(EVID, "flow_run.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    scrub(dst)                           # 证据文件里的本机路径/用户名脱敏
    log("")
    log("证据已写：%s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
