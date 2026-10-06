# ai/ — 拾意接入设备助手（AI）的准备件

这一目录**不进提交**（它不在 `bundle/` 里）。它装的是「拾意」接官方 AI 契约所需的东西，
**为什么现在还不动 `bundle/`** 的说明，以及 **2026-10-04 本地已跑通的实证**。

---

## 0. ✅ 本地已跑通（2026-10-04）

**这不再是设想。** 在本机实测打通了完整链路：

```
拾意 bundle（capabilities: octos.session.open / octos.turn.start）
   → Rinx 宿主 → 本地 octos 助手内核（自公开源码编译）→ DeepSeek API → 回复写回
```

**连续 4 轮成功、零失败，4 次回复各不相同**（真模型输出）。实证与配方见
[`本地跑通_20261004.md`](本地跑通_20261004.md)，原始证据在 [`证据/`](证据/)。

> 注意区分两套 AI 接入面：**OctoSense Shell** 走 `model` 能力（§1 的 `manifest.ai.json`）；
> **Rinx** 走 `octos.*` 服务（上面这条已跑通）。两者是不同宿主的两种接口，不要混为一谈。

---

## 1. 这里面是什么

| 文件 | 是什么 | 官方依据 |
|---|---|---|
| `AGENT.md` | 应用自己的 Agent 契约：角色、输入、每屏做什么、验收标准、记忆规则、**降级规则** | ADR 0002；App Hub `AGENT.md` 契约 |
| `tools.json` | 应用自己的三个工具：`shiyi.intent.read` / `shiyi.memo.read` / `shiyi.memo.save` | App Hub `tools.json` 契约（App-Hub#18） |
| `manifest.ai.json` | **AI 版 `manifest.json`**：在现行清单上加 `capabilities: ["storage","model"]` 和 `agent` 块 | App Hub `main` 的 `KNOWN_CAPABILITIES` / `AgentSpec` |

识别层对应的**可运行实现**在 `../src/intent_model.py`（模型优先、规则兜底）。

## 2. 为什么先放这儿，不直接进 bundle/

三条**核实过**的事实（来源：官方 `OctoScript-App-Design-Flow/docs/AI-SERVICES.zh-CN.md`、
App Hub 源码）：

1. **当前所有 OctoSense Shell 会拒收带 `model` / `agent` 新字段的 manifest。**
   Shell 仍锁定旧 App Hub，它不认识 `model` 权限和新的 `agent` 字段
   （`model` / `background` / `triggers` / `instructions` / `skills`）。manifest 拒绝未知字段，
   所以这样的包能过 `hub check`，**却装不进现在的 Shell**。官方原话：
   「想现在就在 OctoSense 中打开的应用包，请不要使用它们。」
2. **`model` 服务本身还没合并**（OctoSense#95 仍是草稿）。
   即使装进去，`model.complete` 现在也一律返回
   `no service answers "model" on this device`。
3. **本机工具链是 2026-09-23 的旧版**（App-Hub `e86d43f`）：
   `KNOWN_CAPABILITIES` 只有 7 项，**连 `model` 名字都不认识**；`AgentSpec` 也只有极简字段。
   → **在本机无法验证 AI 版能过 `hub check`**。

结论：**AI 版能过 App Hub `main` 的门禁，但会与"现在装得进 Shell"冲突。**
所以 `bundle/` 保持不加未知字段的形态（已 `— PASSED`，任何 Shell 都能开），
AI 契约放在这里**备好**，等确认评审/提交用 `main` 之后再合入。

## 3. 要合入 AI 版，动哪几步

```sh
# 假设仓库根为 $APP，hub/card-host 已更新到 App Hub main
cp ai/manifest.ai.json  "$APP/bundle/manifest.json"
cp ai/AGENT.md          "$APP/bundle/AGENT.md"
cp ai/tools.json        "$APP/bundle/tools.json"

"$HUB_BIN" stamp "$APP/bundle"                 # 重算 bundle_blake3
"$HUB_BIN" check "$APP/bundle" --allow-unsigned # 期望 PASSED + grants: capabilities {model, storage}, agent read-only
```

要退回保命版：把 `manifest.json` 的 `capabilities` 改回 `[]`、删掉 `agent` 块与
`AGENT.md` / `tools.json`，再 `stamp` + `check`。

> （说明：现行 `bundle/` 已声明 `octos.session.open` + `octos.turn.start` + `matrix.send_message`，`hub check` PASSED；上面是开发期替代范式的说明。）

## 4. 本机验证 AI 版的前置（尚未做）

本机 `hub` / `card-host` 是旧版，验证不了带 `model` 的包。要本地验证需：

1. 更新 `F:/gosim_build/octosense-org/OctoSense-App-Hub` 到 `main`；
2. 重新构建 `hub` 与 `card-host`；
3. 再跑第 3 节的命令。

这一步**尚未执行**（要动 F 盘编译环境，等放行）。

## 5. 设计上"接"在哪一层（重要）

L0 卡片**没有表达式、写不出任何调用**（官方 ui-profile-l0.md）——所以**"接 AI"不在卡里，
在卡旁边的 Agent 层**。这正是「拾意」现在的形状：

```
聊天消息 ──► Agent 层（识别）──► L0 卡片（只显示，不调用）
              ▲
              └─ 助手可用 → model.complete 做识别
                 助手不可用 → src/intent_card.py 的本地规则兜底
```

卡片永远只是**把 Agent 的结果显示出来**；模型帮不帮得上忙，卡片的形态不变，
变的是卡片上那行**「识别来源 · 设备助手 / 本地规则」**——如实标注，不假装。
