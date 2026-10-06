#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本机 model 宿主替身 —— 按官方 `model.complete` 契约接本机可用的模型。

官方现状（`OctoScript-App-Design-Flow/docs/AI-SERVICES.zh-CN.md`）：
现在**没有任何 Shell 提供 `model` 服务**，应用侧调用一律返回
`no service answers "model" on this device`。所以在真机上，应用的「模型路」是关的。

这个文件是**开发期**的一座桥：它扮演「宿主」，用本机可用的模型（自有 provider，
读 `~/.workbuddy/models.json` 或环境变量 `SHIYI_MODEL_KEY`）把这个空格填上，
好让生成器能演示并验证「助手可用 → 走模型」那条路。

**它守的还是官方那份契约**（否则这次演示就没有意义）：

  · 单次调用：无工具、无记忆、无历史；
  · 回复必须符合应用给的 schema —— 由调用方 `ModelHost.complete` 校验，
    不合规/含 URL/超长一律判为不可用；
  · 应用侧看不到提供方、模型、密钥 —— 这座桥在**宿主侧**决定用谁；
  · 失败就是 `(False, "一句话")`，调用方照官方要求**回退规则**，不重试、不崩。

安全：密钥只从本机配置 / 环境变量读，**绝不写进仓库**，也绝不打印。

运行（自测）：

    python src/host_local.py            # 用本机 key 走一遍"助手可用"路径
    python src/host_local.py --no-key   # 演示"没有 key"时如何判为不可用
"""

import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from intent_model import SCHEMA, TASK, ModelHost  # noqa: E402


def _read_key():
    """按「账号1 优先」取本机自有 key。返回 (key, 来源说明)；没有则 (None, "none")。"""
    k = os.environ.get("SHIYI_MODEL_KEY")
    if k:
        return k, "env:SHIYI_MODEL_KEY"
    p = os.path.expanduser("~/.workbuddy/models.json")
    if not os.path.exists(p):
        return None, "none"
    try:
        arr = json.load(open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None, "none"
    if not isinstance(arr, list):
        return None, "none"
    # 取配置里第一个形状对的 key（本地 models.json 的先后即优先级）；
    # 不写死任何账号，环境变量 SHIYI_MODEL_KEY 可整段覆盖。
    for m in arr:
        k = m.get("apiKey") or ""
        if k.startswith("sk-"):
            return k, "models.json:%s" % (m.get("provider") or m.get("name") or "?")
    return None, "none"


class LocalModelHost(ModelHost):
    """把本机模型当「宿主提供的 model 服务」。应用侧接口与官方一致。"""

    def __init__(self, endpoint="https://api.deepseek.com/chat/completions",
                 model="deepseek-chat", key=None, timeout=40):
        self.endpoint = endpoint
        self.model = model
        self.timeout = timeout
        if key:
            self._key, self._src = key, "arg"
        else:
            self._key, self._src = _read_key()
        super().__init__(responder=self._respond)

    def describe(self):
        """只报「哪个宿主在服务」，不报密钥 —— 与官方一致：应用看不到提供方。"""
        return "local provider (%s)" % (self._src if self._key else "no key")

    def _respond(self, task, input, schema, cls):   # noqa: A002 - 参数名照官方
        if not self._key:
            return {"$error": "no_provider: no local model key is configured"}
        system = task + "\nReply with JSON matching this schema exactly:\n" + \
            json.dumps(schema, ensure_ascii=False)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(input, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_tokens": 220,
        }
        req = urllib.request.Request(self.endpoint, data=json.dumps(payload).encode("utf-8"),
                                     method="POST")
        req.add_header("Authorization", "Bearer " + self._key)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                d = json.loads(r.read().decode())
            content = d["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            return {"$error": "provider: HTTP %s" % e.code}
        except Exception as e:  # noqa: BLE001 - 提供方出错即视为不可用
            return {"$error": "provider: %s" % type(e).__name__}
        try:
            return json.loads(content)
        except Exception:  # noqa: BLE001
            return {"$error": "invalid_output: reply is not JSON"}


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    no_key = "--no-key" in sys.argv
    host = ModelHost() if no_key else LocalModelHost()
    print("host:", host.describe(), "| available:", host.available())
    for text in ("下周三我得去趟深圳，顺便把合同签了",
                 "明天下午三点跟老王在杭州碰一下"):
        ok, out = host.complete(TASK, {"text": text, "room": "家庭群",
                                       "at": "2026-10-05T10:40:00"}, SCHEMA, "fast")
        print("  %-22s ok=%s -> %s" % (text[:20], ok,
              json.dumps(out, ensure_ascii=False)[:110]))
