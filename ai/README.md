# ai/ — 拾意接入设备助手（AI）的契约备件与实证

> 本目录是**附属目录**：正式提交物是**仓库根的 `bundle/`**（脚本应用 `shiyi-live` 0.8.6，
> 已声明 `model` 并在 OctoSense 宿主上**双端跑通**，见 [`../docs/AI接入方案.md`](../docs/AI接入方案.md)）。
> 这里装的是"**应用自带 Agent**"那套契约件，以及历次跑通的实证。

---

## 1. 这里面是什么

| 文件 / 目录 | 是什么 |
|---|---|
| `AGENT.md` | 应用自带 Agent 的契约：角色、输入、每屏做什么、验收标准、记忆规则、**降级规则** |
| `tools.json` | 应用自带的三个工具：`shiyi.intent.read` / `shiyi.memo.read` / `shiyi.memo.save` |
| `manifest.ai.json` | AI 版 `manifest` 备件：在清单上加 `capabilities: ["storage","model"]` 与 `agent` 块的样例 |
| `本地跑通_20261004.md` | 2026-10-04 本机跑通实录（Rinx 宿主 → 本地 octos 内核 → DeepSeek） |
| `证据/` | 上述跑通的原始证据（截图 / 日志） |
| `templates/` | 契约模板 |

识别层的**可运行实现**在 [`../src/intent_model.py`](../src/intent_model.py)（模型优先、规则兜底）。

---

## 2. 现在跑到哪一步

| 面 | 走什么 | 状态 |
|---|---|---|
| **提交版 `bundle/`（0.8.6）** | 宿主提供的**模型服务**（OctoSense 宿主：`model` / `model.complete`） | ✅ 已声明并 **双端真跑通**（桌面 + 手机）；`hub check` PASSED |
| **"应用自带 Agent"契约**（本目录） | 官方 ADR 0002 方向，宿主侧**尚未普遍运行** | ✅ 契约**已备**；等宿主支持后合入 `bundle/` |
| Rinx 宿主那条线 | `octos.turn.start` | ✅ 2026-10-04 已跑通（见 [`本地跑通_20261004.md`](本地跑通_20261004.md)） |

> 两套面**不要混**：一套是**借宿主的模型**（提交版走的就是这条），
> 另一套是**应用带自己的 Agent**（本目录备的）。它们接口不同、互不冲突。

---

## 3. "应用自带 Agent"契约合入时怎么动

```sh
# 假设仓库根为 $APP，hub / card-host 已支持 agent 字段
cp ai/manifest.ai.json  "$APP/bundle/manifest.json"
cp ai/AGENT.md          "$APP/bundle/AGENT.md"
cp ai/tools.json        "$APP/bundle/tools.json"

"$HUB_BIN" stamp "$APP/bundle"                 # 重算 bundle_blake3
"$HUB_BIN" check "$APP/bundle" --allow-unsigned # 期望 PASSED + grants: capabilities {model, storage}, agent read-only
```

---

## 4. 设计上"接"在哪一层（重要）

L0 卡片**没有表达式、写不出任何调用**（官方 `ui-profile-l0.md`）——所以**"接 AI"不在卡里，
在卡旁边的 Agent 层**。这正是「拾意」现在的形状：

```
消息（聊天 / 邮件）──► Agent 层（识别）──► 卡片（只显示，不调用）
                        ▲
                        └─ 助手可用 → 宿主模型服务做识别
                           助手不可用 → src/intent_card.py 的本地规则兜底
```

卡片永远只是**把 Agent 的结果显示出来**；模型帮不帮得上忙，卡片的形态不变，
变的是卡片上那行**「识别来源 · 设备助手 / 本地规则」**——如实标注，不假装。
