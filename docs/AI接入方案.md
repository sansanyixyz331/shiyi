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
消息（聊天 / 邮件）
     │
     ▼
Agent 层（识别）  ── 设备助手可用 → 宿主提供的模型服务
     │              └─ 不可用      → 本地规则（src/intent_card.py 的解析器）
     ▼
卡片（只显示，不调用）
```

对应代码：`src/intent_model.py`（两条路的可运行实现，含"不可用"处理）。

## 3. 我们按官方契约声明了什么

**提交版 `bundle/`（`shiyi-live` · 0.8.6）**在清单里声明：

```json
"capabilities": ["storage", "model", "octos.session.history",
                 "matrix.read_messages", "matrix.profile", "matrix.send_message"]
```

| 声明 | 为什么是这个 |
|---|---|
| `storage` | 长期记忆写在应用自己的存储里（`.local-state/memory.json`） |
| **`model`** | 一次性模型调用：**无工具、无记忆、无历史**，回复按我们给的 schema 校验；**应用永远看不到提供方、模型或密钥** |
| `octos.session.history` | 读设备助手与用户的会话，进记忆盒 |
| `matrix.read_messages` / `matrix.profile` / `matrix.send_message` | 读绑定房间消息 → 点一条造卡；标出「（你）」；**确认后真发回群** |

> **关于"应用自带 Agent"那套契约**（`AGENT.md` / `tools.json`，官方 ADR 0002 方向）：
> 契约件**已备好**（见 `ai/`），但**当前提交版未随 `bundle/` 提交**——提交版走的是**宿主提供的模型服务**这条线（已跑通，见 §4）。
> 两者不冲突：一个是**借宿主的模型**，一个是**带自己的 Agent**；宿主普遍支持后者后可合入。

## 4. 现在能不能跑

**能 —— 已在 OctoSense 宿主上真跑通（桌面 + 手机双端）。**

| 项 | 实况 |
|---|---|
| 提交版声明 | 根 `bundle/`（`shiyi-live` **0.8.6**）声明 `model`；`hub check` **PASSED** |
| 桌面端 | 识别真走宿主模型服务；卡上标「识别来源 · **设备助手**」 |
| 手机端（小米13 真机） | 同样跑通：读群 → 出卡 → 确认 → 发回群；内核日志 `calling LLM` → `LLM response received`（`input 15243 / output 211`） |
| 证据 | `docs/evidence/phone-live-20261011/`、`ai/证据/` |

**降级照旧**：宿主**不提供**该服务、或调用失败 → **一次不成就退本机规则**，卡上改标「识别来源 · 本地规则」，五屏照走。

> ⚠️ **换宿主要注意服务名**：不同宿主暴露的模型服务名不一样 —— **OctoSense** 宿主是 `model`（`model.complete`）；
> **Rinx** 宿主走的是 `octos.turn.start` 这条路。**照搬一个宿主的能力名去调不对应的服务，会被拒绝**，
> 所以我们两条线各按宿主写。拿不准的宿主：**走降级路径**（规则兜底），不会卡住。

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
| 商店说明里如实写模型用途 | `listing` 与本文件如实说明：**AI 只做识别**，不可用时退规则、照常可用 | 本文 + `bundle/listing.json` |

## 6. 怎么核（评审可复跑）

```sh
# 逻辑层：四条路都真跑一遍
python src/intent_model.py

# 单条：
python src/intent_model.py "下周三我得去趟深圳"              # 规则兜底
python src/intent_model.py --with-model "下周三我得去趟深圳"  # 替身宿主：助手可用那条路

# 门禁层（提交版 bundle）
"$HUB_BIN" check bundle --allow-unsigned     # → PASSED
```

`src/intent_model.py` 的自测覆盖：
① 无 `model` 服务 → 规则兜底；
② 替身宿主（不联网）→ 走模型；
③ 助手在但拒绝（`no_provider`）→ 退规则，原因如实带回；
④ 模型回了含 URL 的不合规结果 → 判为不可用，**不采用**。

## 7. 当前状态

| 项 | 状态 |
|---|---|
| 识别层两条路（模型优先 / 规则兜底） | ✅ 可运行，4 条自测通过 |
| 卡片标注"识别来源" | ✅ 已上识别卡 |
| **提交版声明 `model` 并真跑通** | ✅ **桌面 + 手机双端**（见 §4） |
| `hub check` 门禁 | ✅ **PASSED** |
| "应用自带 Agent"契约（`AGENT.md` / `tools.json`） | ✅ 已备（`ai/`）；宿主普遍支持后合入 |
