#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""l0-bindings-lint — 在宿主里跑之前，先拦下会整卡崩掉的 L0 卡。

为什么需要它（全部为实测结论，出处见 OctoSense-org/OctoScript-App-Design-Flow#150）：

  1. `bindings.json` 的每个 `target` 必须在 `page.data.json` 里有**同名顶层键**。
     卡片在任何调用返回之前就先被 lower 一遍；此时路径落在不存在的名字上会
     让**整张卡** lower 失败（`unresolved or unsupported kit property`），不是少一行。

  2. 调用失败时宿主写 `{"is_ok": false, "error": "…"}`（**没有 `data`**）。
     所以读 `X.data.*` 的节点必须包在裸布尔 guard 里（`when X.is_ok { … }`），
     否则一次失败（无 provider / 拒权 / 网络错）就**整卡** lower 失败。

  3. `bindings.json` 里每个 `service` 必须已在 `manifest.capabilities` 里声明；
     且 `on_open` 里任一调用失败会让**整个应用打不开**（停在导入界面、无报错）。

用法：
    python3 l0_bindings_lint.py <bundle_dir>

退出码：
    0 = 通过（可能有 WARN）；1 = 有 ERROR（这张卡会在宿主里打不开/渲不出）。

只读、无依赖、不改任何文件。JSON 之外的一切都按纯文本扫，不 require 一个 L0 解析器。
"""

import json
import os
import re
import sys

MAX_BINDINGS = {"on_open": 8, "events": 64}
TARGET_RE = re.compile(r"^[A-Za-z0-9_]+$")
# `X.data.<field>` / `X.data[` — 一个对服务结果 data 的读取
DATA_READ_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.data\b")
# `when X.is_ok { … }` —— 裸布尔 guard（L0 的 predicate 允许单条路径）
GUARD_RE = re.compile(r"\bwhen\s+([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*is_ok\b")
# `state X { … }` 声明
STATE_RE = re.compile(r"\bstate\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{")


def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[0])
        print("usage: python3 l0_bindings_lint.py <bundle_dir>")
        return 2

    root = argv[1]
    errors, warns, oks = [], [], []

    def err(m):
        errors.append(m)

    def warn(m):
        warns.append(m)

    def ok(m):
        oks.append(m)

    # ---- 读三个文件；都缺 = 不是 L0 卡（脚本应用或空目录） ----
    card_p = os.path.join(root, "page.card")
    data_p = os.path.join(root, "page.data.json")
    bind_p = os.path.join(root, "bindings.json")
    man_p = os.path.join(root, "manifest.json")

    for p in (card_p, data_p, man_p):
        if not os.path.isfile(p):
            print("not an L0 card bundle: missing %s" % os.path.basename(p))
            return 2

    card = open(card_p, "r", encoding="utf-8").read()
    data = read_json(data_p)
    manifest = read_json(man_p)
    caps = manifest.get("capabilities", []) or []

    # Scan only real syntax: strip `#` comments, so prose like "page.data.json" in a
    # banner comment is not mistaken for a read of `page.data`.
    card_code = "\n".join(line.split("#", 1)[0] for line in card.splitlines())

    if not isinstance(data, dict):
        err("page.data.json must be a JSON object")
        data = {}

    # ---- 没有 bindings.json：仍是合法 L0 卡（纯静态） ----
    if not os.path.isfile(bind_p):
        ok("no bindings.json — static card, nothing to wire")
        report(oks, warns, errors)
        return 1 if errors else 0

    bindings = read_json(bind_p)
    if not isinstance(bindings, dict):
        err("bindings.json must be a JSON object")
        report(oks, warns, errors)
        return 1

    unknown = set(bindings) - set(MAX_BINDINGS)
    if unknown:
        err("bindings.json has unknown keys: %s" % ", ".join(sorted(unknown)))

    calls = []
    for name, limit in MAX_BINDINGS.items():
        section = bindings.get(name, {})
        if name == "on_open":
            if not isinstance(section, list):
                err("bindings.json: on_open must be an array")
                continue
            items = [(name, i, c) for i, c in enumerate(section)]
        else:
            if not isinstance(section, dict):
                err("bindings.json: events must be an object")
                continue
            items = [(name, k, c) for k, c in section.items()]
        if len(items) > limit:
            err("bindings.json: %s has %d entries, limit is %d" % (name, len(items), limit))
        calls.extend(items)

    if not calls:
        warn("bindings.json present but empty")

    targets = []
    for section, key, call in calls:
        where = "%s[%s]" % (section, key)
        if not isinstance(call, dict):
            err("%s must be an object" % where)
            continue
        service = call.get("service")
        target = call.get("target")
        args = call.get("args")

        if not isinstance(service, str) or not service:
            err("%s: service must be a non-empty string" % where)
        elif service not in caps:
            err("%s: service %r is not declared in manifest.capabilities" % (where, service))
        else:
            ok("%s: service %r granted" % (where, service))

        if not isinstance(target, str) or not TARGET_RE.match(target or ""):
            err("%s: target must be a top-level data name [A-Za-z0-9_]" % where)
        else:
            targets.append((where, target))

        if args is not None and not isinstance(args, dict):
            err("%s: args must be an object" % where)

    # ---- 检查 1 & 2：卡片「引用的」名字必须存在；引用 binding target 的必须有 guard ----
    #
    # 精确规则（实测校正）：崩的不是"target 未预置"，而是"卡片读了一条落到
    # 不存在名字上的路径" —— 首帧 lower 在任何调用返回之前发生，解析失败即**整卡**失败。
    # 一个从未被卡片引用的 target（如只用于建立会话的 `session`）不预置也无害：
    # 不被引用的名字根本不会被解析。
    declared_states = set(STATE_RE.findall(card_code))
    read_names = set(DATA_READ_RE.findall(card_code))   # `X.data.*` —— 明确引用
    guarded = set(GUARD_RE.findall(card_code))          # `when X.is_ok` —— 也是引用
    target_names = {t for _, t in targets}
    referenced = read_names | guarded

    for name in sorted(referenced):
        if name not in data:
            err(
                "page.card references %r but page.data.json has no such key — the first "
                "frame lowers before any reply, and a path into an absent name fails the "
                "WHOLE card ('unresolved or unsupported kit property'). Seed %r in "
                "page.data.json." % (name, name)
            )
            continue
        if name in target_names and name not in guarded:
            err(
                "page.card reads %r (a binding target) with no `when %s.is_ok { … }` guard "
                "— a failed turn writes {is_ok:false,error:…} (no `data`) and the whole "
                "card fails to lower instead of just that line." % (name, name)
            )
            continue
        ok("page.card: %r is seeded%s" % (name, " and guarded" if name in guarded else ""))

    # ---- 检查 3：binding target 未被引用也没预置 —— 今天无害，但脆 ----
    for where, target in targets:
        if target not in referenced and target not in data:
            warn(
                "%s: target %r is neither referenced by page.card nor seeded — harmless "
                "today (an unread name is never resolved), but seed it so that a later "
                "reference cannot fail the whole card." % (where, target)
            )
        elif target in data and isinstance(data[target], dict) and data[target].get("is_ok") is False:
            warn(
                "%s: target %r is seeded as is_ok:false — fine while every read of it is "
                "guarded, else the card shows nothing for it" % (where, target)
            )

    report(oks, warns, errors)
    return 1 if errors else 0


def report(oks, warns, errors):
    for m in oks:
        print("  ok   %s" % m)
    for m in warns:
        print("  warn %s" % m)
    for m in errors:
        print("  ERR  %s" % m)
    print()
    print("l0-bindings-lint: %d ok, %d warn, %d error" % (len(oks), len(warns), len(errors)))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
