# 仓库结构（一页速查）

> 2026-10-10 复赛结构改制后定稿。**变更原因与逐条对照见 [`docs/复赛结构变更说明_20261010.md`](docs/复赛结构变更说明_20261010.md)**，本页只做"当前长什么样"的速查。

## 一、为什么根 `bundle/` 是脚本应用

官方复赛改进建议：**「把 `bundle/` 放到仓库根，一仓一应用」**；
配套：官方新推的**自动发布流程**（`.github/workflows/publish-app.yml`，GitHub provenance + Sigstore 自动签名）**只从仓库根 `bundle/` 取应用**。
⇒ 所以把**要发布的那个主应用**摆到根。

**顺带的好处**（不是主因，但很重要）：脚本应用是本仓**唯一带 `model`（AI）能力**的 App Hub 形态 ——
官方评分里"没有真实模型调用 ⇒ 需求与任务价值封顶 13/25"，站根 bundle/ 正好躲开这条。

## 二、四个位置

| # | 位置 | 是什么 | 官方桶 | `model` | 提交单元 |
|---|---|---|---|---|---|
| ① | **`bundle/`**（根） | 脚本应用「拾意 · 现场造卡」`main.splash` | App Hub · 进程应用 | ✅ | ✅ **主提交** |
| ② | **`apps/shiyi-card/bundle/`** | L0 卡片包 `page.card` + `bindings.json` + `kit/` | App Hub · App Card | —（走总线调用） | ✅ 第二提交面 |
| ③ | **`octos/`** | OctoSense 系统 app `os.shiyi` + 宿主语音扩展 | 原生宿主扩展 | ✅ | ❌ 技术深度证据<br>（`os.*` 官方 App Hub 不收） |
| ④ | `apps/shiyi-live/` | 形态①的详细说明文档（bundle 已移到根） | — | — | ❌ 仅文档 |

## 三、当前版本现状（2026-10-10 22:3x 核实）

| 位置 | 当前版本 | 状态 |
|---|---|---|
| ① 根 `bundle/` | 脚本应用 **0.8.0** | ✅ **已落位**：助手当决策核心（title / remind / remind_text / why / kind=none 主动不造卡）；已重盖章 + `hub check` **PASSED**（`bundle_blake3` = `c633cb04…`） |
| ② 卡片包 | **0.3.3** | ✅ 最新（与 10-06 快照同值） |
| ③ `octos/` | **0.3.10** | ✅ 最新（含 `model` + 时间/地点解析治本 + **群消息改卡召回修复**） |

> ①的 0.8.0 与 0.7.4 的差别：多出「助手给**人话标题** / 判**要不要提醒、提前多久** / 写**提醒时那句话** / 给**依据**」，
> 且纯寒暄（`kind=none`）**主动不造卡**；不接助手时规则路径**照常造卡**并如实标注降级。本地两条路径都真跑过（`shiyi_lab/A2_决策对照/`）。

### 待办（跑官方发布流程时处理，出自变更说明 §五）

- [ ] 根 `bundle/` **去签名**（官方流程要求未签名包，由 Sigstore 负责签）
- [ ] 打新 `v*` tag（官方工作流由 tag 触发）
- [ ] 官方 release 出来后**提复赛新 issue**（release ≠ 提交）

## 四、自检三条

```bash
cat bundle/manifest.json | grep -o '"model"'                    # ① 主提交是不是有 AI 那份（应打印 model）
ls apps/shiyi-card/bundle/                                       # ② 卡片包（应有 page.card、不该有 main.splash）
grep '"version"' octos/apps/shiyi/bundle/manifest.json           # ③ 系统 app 版本
```

---

*初赛版（tag `gosim-semifinal-submission` = `185d43c`）一字节未动；本页描述的是复赛版结构。*
