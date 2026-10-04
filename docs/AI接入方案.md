# 拾意 · 接入设备助手（AI）说明

> 本文说明「拾意 Pickup」**怎么用官方 AI 契约**、**AI 接在哪一层**、
> **现在能不能跑**，以及**助手不可用时怎么办**。给评委看的四问
> （输入是什么 / Agent 做什么 / 怎么核验 / 哪一步要人确认）见
> [`Agent任务演示.md`](Agent任务演示.md)；本文只讲 AI 这一条线。

---

## 1. 一句话

**AI 不接在卡片里，接在卡片旁边的 Agent 层。** 卡片只显示结果；
识别这一步**模型可用就交给设备助手，不可用就交给本地规则**——
**两条路的输出是同一个结构，卡片上如实写出这次是谁做的**。

## 2. 为什么不是"在卡里调 AI"

官方的 L0 卡片规范（`OctoScript/docs/ui-profile-l0.md`）写得很清楚：

> **L0 = 只有 UI 声明**：数据来自宿主解析的、已登记的 `sys.*` 数据源，
> **没有表达式，没有调用**。

所以 L0 卡片**写不出 `host.request(...)`**。官方 `AI-SERVICES` 文档也确认：
"卡片应用「接 AI」的位置**不在卡里**，而在卡旁边的服务 / Agent 层。"
——「拾意」现在就是这个形状：

```
聊 天 消 息
     │
     ▼
Agent 层（识别）  ── 设备助手可用 → model.complete（class: fast，按 JSON Schema 校验）
     │              └─ 不可用      → 本地规则（src/intent_card.py 的解析器）
     ▼
L0 卡片（只显示，不调用）
```

对应代码：`src/intent_model.py`（两条路的可运行实现，含"不可用"处理）。

## 3. 我们按官方契约声明了什么

AI 版的应用包（`ai/` 里备好，见 `ai/README.md`）在 `manifest.json` 上加两块：

```json
"capabilities": ["storage", "model"],
"agent": {
  "profile": "read-only",
  "tools": [],
  "max_iterations": 6,
  "token_budget": 60000,
  "model": { "needs": ["structured_output", "multilingual"], "tier": "standard" },
  "background": false,
  "instructions": "AGENT.md",
  "skills": []
}
```

| 声明 | 为什么是这个 |
|---|---|
| `storage` | 长期记忆写在应用自己的存储里（现为 `.local-state/memory.json`） |
| `model` | 一次性模型调用 `model.complete`：**无工具、无记忆、无历史**，回复按我们给的 schema 校验；**应用永远看不到提供方、模型或密钥** |
| `agent.profile: read-only` | 它只读消息、产出卡片，不改宿主里任何东西 |
| `agent.model.needs` | 要 `structured_output`（必须回 JSON）+ `multilingual`（中文）——**只说需求，不说用哪个模型**，由宿主从用户自己的提供方里挑 |
| `agent.background: false` | 不后台跑；人在看着屏幕时它才动 |
| `agent.tools: []` | 不用通用宿主工具；它要的东西在应用自己的 `tools.json` 里 |

`AGENT.md` 是它的契约（角色 / 输入 / 每屏做什么 / **验收标准** / 记忆规则 / **降级规则**）；
`tools.json` 是它自己的三个工具：`shiyi.intent.read`、`shiyi.memo.read`、`shiyi.memo.save`。

## 4. 现在能不能跑（如实说）

**不能。** 三条事实：

1. **没有任何 OctoSense Shell 提供 `model` 服务。**
   `model` 权限在 App Hub 已合（App-Hub#24），但服务本身还在草稿
   （OctoSense#95）；现在调用一律返回
   `no service answers "model" on this device`。
2. **应用自己的 Agent 目前没有任何 Shell 运行它**（ADR 0002 待实施）。
   声明在 App Hub 能被接受，运行时还没有。
3. **当前 Shell 锁定旧 App Hub，会拒收带 `model` / `agent` 新字段的 manifest。**
   官方原话：「想现在就在 OctoSense 中打开的应用包，请不要使用它们。」

所以**提交进 `bundle/` 的那一份，暂不加 AI 字段**——保证它在**现在任何 Shell 里都能打开**。
AI 契约备在 `ai/`，由官方进度决定何时合入。**这是有意的取舍，不是遗漏。**

## 5. 助手不可用时怎么办（官方硬要求，我们照做）

官方对隔离应用接 AI 的要求，逐条对照：

| 官方要求 | 「拾意」怎么做 | 代码 / 证据 |
|---|---|---|
| 一定处理 `r.is_ok == false` | `ModelHost.complete()` 返回 `(ok, data\|error)`，两条路都走通 | `src/intent_model.py` §ModelHost |
| 把"不可用"当**正常状态**，用一句话说明 | 卡片印「识别来源 · 本地规则」，不报错、不弹窗 | `cards/shiyi-01-read/page.card` 的 `copy.f_src` |
| **不循环重试** | 一次不成就退规则，不重试 | `recognize()` |
| **不依赖助手也完整可用** | 助手不在，五屏照走，只是识别换规则 | `recognize()` 的 `_from_rules` |
| 绝不向用户索要密钥 / 提供方 | 全程不出现任何密钥输入；那属于宿主的 AI providers 面板 | 无相关 UI |
| 回复不合 schema / 含 URL / 超限 → 拒绝 | `_validate()` 逐条判，不合格判为不可用、退规则 | `src/intent_model.py` §_validate |
| 在商店说明与报告里写明"现在不起作用" | 本文件第 4 节 + `listing.description` | 本文 |

## 6. 怎么核（评审可复跑）

```sh
# 逻辑层：四条路都真跑一遍
python src/intent_model.py

# 单条：
python src/intent_model.py "下周三我得去趟深圳"          # 规则兜底（现状）
python src/intent_model.py --with-model "下周三我得去趟深圳"  # 替身宿主：助手可用那条路

# 门禁层（保命版 bundle）
"$HUB_BIN" check bundle --allow-unsigned     # → PASSED，grants: capabilities {}
```

`src/intent_model.py` 的自测覆盖：
① 现状（无 `model` 服务）→ 规则兜底；
② 替身宿主（不联网）→ 走模型；
③ 助手在但拒绝（`no_provider`）→ 退规则，原因如实带回；
④ 模型回了含 URL 的不合规结果 → 判为不可用，**不采用**。

## 7. 还差什么

| 项 | 状态 |
|---|---|
| AI 契约（`AGENT.md` / `tools.json` / `manifest.ai.json`） | ✅ 备好，见 `ai/` |
| 识别层两条路（模型优先 / 规则兜底） | ✅ 可运行，4 条自测通过 |
| 卡片标注"识别来源" | ✅ 已上识别卡 |
| **本机验证 AI 版过 `hub check`** | ⏳ 需先把本机 App Hub 更新到 `main` 并重建 `hub`（本机现为 2026-09-23 旧版，连 `model` 名字都不认） |
| **AI 版进最终提交** | ⏳ 待官方确认评审/提交走 App Hub `main` 之后 |
