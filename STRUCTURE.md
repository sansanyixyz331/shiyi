# 仓库结构（一页速查）

> 2026-10-10 复赛结构改制后定稿。本页只做"当前长什么样"的速查。

## 一、为什么根 `bundle/` 是脚本应用

官方复赛改进建议：**「把 `bundle/` 放到仓库根，一仓一应用」**；
配套：官方新推的**自动发布流程**（`.github/workflows/publish-app.yml`，GitHub provenance + Sigstore 自动签名）**只从仓库根 `bundle/` 取应用**。
⇒ 所以把**要发布的那个主应用**摆到根。

**顺带的好处**（不是主因）：脚本应用是本仓**带 `model`（真实模型调用）能力**的 App Hub 形态
（卡片包走总线调用、系统 app 属原生宿主扩展）—— 复赛要作品**真正把模型用起来**，主提交站根 `bundle/` 正好对上。

## 二、四个位置

| # | 位置 | 是什么 | 官方桶 | `model` | 提交单元 |
|---|---|---|---|---|---|
| ① | **`bundle/`**（根） | 脚本应用「拾意 · 现场造卡」`main.splash` | App Hub · 进程应用 | ✅ | ✅ **主提交** |
| ② | **`apps/shiyi-card/bundle/`** | L0 卡片包 `page.card` + `bindings.json` + `kit/` | App Hub · App Card | —（走总线调用） | ✅ 第二提交面 |
| ③ | **`octos/`** | OctoSense 系统 app `os.shiyi` + 宿主语音扩展 | 原生宿主扩展 | ✅ | ❌ 技术深度证据<br>（系统 app 形态，不占 App Hub 提交位） |
| ④ | `apps/shiyi-live/` | 形态①的详细说明文档（bundle 已移到根） | — | — | ❌ 仅文档 |

> **另附（复核用）**：**`android/`** —— **能直接装上试的安卓包**（宿主 APK **分卷**，含 AI 内核；另附拾意应用包）。
> 为方便不想编译的人复核手机端能力而附；**不参与 App Hub 提交**。安装 / 验收 / 坑清单见 [`android/README.md`](android/README.md)。

## 三、当前版本现状（2026-10-12 复核）

| 位置 | 当前版本 | 状态 |
|---|---|---|
| ① 根 `bundle/` | 脚本应用 **0.8.6** | ✅ **已落位**：助手当决策核心（title / remind / remind_text / why / kind=none 主动不造卡）＋ **自动读群消息**（群里来新消息它自己读到就造卡，与桌面「自动读邮件」同构；首启只登记基线、自己发回的结论不重复造卡）；已重盖章 + `hub check` **PASSED**（`bundle_blake3` = `50404a65…`） |
| ② 卡片包 | **0.3.3** | ✅ 最新（与 10-06 快照同值） |
| ③ `octos/` | **0.3.11** | ✅ 最新（含 `model` + 时间/地点解析治本 + 群消息改卡召回修复 + **桌面真收邮件**：`mail` 能力 · 自动读来信出常驻卡 · 到点提醒念出来） |

> **①的 0.8.6 相对 0.8.0**：多出**自动读群消息**（`chat_poll` + 每 6 秒心跳；只处理「最后一条变了」的，首启登记基线）；这份 `main.splash` 与手机线适配版**逐字节相同**，两份 manifest 的区别只在**能力声明**——主提交版只声明官方宿主具备的 6 项（`rinx.*` 在 Rinx 里另有声明，不写进主提交，免得被官方宿主拒收）。
>
> ①的 0.8.0 与 0.7.4 的差别：多出「助手给**人话标题** / 判**要不要提醒、提前多久** / 写**提醒时那句话** / 给**依据**」，
> 且纯寒暄（`kind=none`）**主动不造卡**；不接助手时规则路径**照常造卡**并如实标注降级。本地两条路径都真跑过（对照记录留在本地试验台，不随仓）。

## 四、自检三条

```bash
cat bundle/manifest.json | grep -o '"model"'                    # ① 主提交是不是有 AI 那份（应打印 model）
ls apps/shiyi-card/bundle/                                       # ② 卡片包（应有 page.card、不该有 main.splash）
grep '"version"' octos/apps/shiyi/bundle/manifest.json           # ③ 系统 app 版本
```

---

## 五、主要文档与材料

| 顺序 | 文件 | 作用 |
|---|---|---|
| 1 | [`MATERIALS.md`](MATERIALS.md) | 提交材料清单（按类别列出全部材料） |
| 1b | [`FILE-INDEX.md`](FILE-INDEX.md) | 文件索引（到文件级，按目录逐条列出会提交的全部文件） |
| 2 | [`README.md`](README.md) | 作品说明（§30 秒版 + §8 复现 + §9 证据索引） |
| 3 | [`评审速览.md`](评审速览.md) | 速览 + 逐条对官方评分口径 |
| 4 | [`SUBMISSION.md`](SUBMISSION.md) | 按"官方要什么"逐项对照（含复现命令） |
| 5 | [`review/ANSWERS.md`](review/ANSWERS.md) | 官方门禁 scan 七问逐条回答（带源码行号） |
| 6 | [`review/GATE.txt`](review/GATE.txt) | 门禁报告（`hub check` 输出，含 grants 行） |
| 7 | [`docs/数据来源与限制.md`](docs/数据来源与限制.md) | 数据来源 / 已知限制 |
| 8 | [`docs/Rinx宿主改造说明.md`](docs/Rinx宿主改造说明.md) | 宿主可用性改造（逐条改了什么 / 为什么 / 许可与归属） |

---

*（`gosim-semifinal-submission` 现指向结构改制前的快照 `185d43c`；本页描述的是复赛版结构，发布前会重打该 tag。）*
