# 提交材料对照表 · 拾意 Pickup

> GOSIM **Agentic App 黑客松 2026「意图即应用」** · 赛道一（OctoSense / AppCard）
> 本文件把官方要求的每一件材料，逐条对应到本仓库里的**具体文件、链接与复现命令**，
> 供评委核查、也供提交前收口。**每一项都能当场点开看。**

---

## ✅ 提交前 checklist（照官方要求逐项打勾 · 10/6 23:59 前）

| # | 官方要求 | 状态 | 位置 |
|---|---|---|---|
| 1 | **只收 OctoScript 应用** | ✅ | `bundle/page.card`（`# level: L0`） |
| 2 | 代码仓库（**公开 + Apache-2.0**） | ✅ | <https://github.com/sansanyixyz331/shiyi> · `LICENSE` |
| 3 | **必须有 README** | ✅ | `README.md`（含顶部 30 秒版）+ `评审速览.md` |
| 4 | 简短需求 | ✅ | `README.md` §1–§2 |
| 5 | 可运行最小原型 + **启动说明** | ✅ | 便携包（**Release 直链** <https://github.com/sansanyixyz331/shiyi/releases/download/v0.3.3/shiyi-portable-demo-v0.3.3.zip>，41 MB，双击 `一键运行.cmd` 即跑）+ `README.md` §5 |
| 6 | **固定版本源码或包** | ✅ | tag `v0.3.3` · `bundle/manifest.json` 内容寻址摘要 |
| 7 | **2–3 分钟演示** | ✅ | `build/_video/shiyi-walkthrough.mp4`（**2 分 15 秒**，五屏正流程 + 两个失败态） |
| 8 | **两张关键截图** | ✅ | `bundle/screenshots/01-read.png`、`03-plan.png`（另附 5 张） |
| 9 | 数据来源与限制 | ✅ | `docs/数据来源与限制.md` |
| 10 | 已报名成员名单 | ✅ | 官方 issue #5 报名评论（队伍 `三三Claw`） |
| 11 | 至少一次**可核对的操作** | ✅ | `build/verify_flow.py` 宿主内真点击 → `build/_evidence/flow_run.json` |
| 12 | 一个**失败或空状态** | ✅ | 未签名被拒 / 摘要不符被拒（视频 ③ 段 + `_evidence` 抓图） |
| 13 | **App Hub 提交** | ✅ **已提** | `OctoSense-App-Hub` issue **#76**（**Submit shiyi 0.7.3**；**一个 issue 覆盖两形态**：主 = L0 卡片包 `bundle/` 0.3.3〔Linux 章〕，附 = 脚本应用 `apps/shiyi-live/` 0.7.3〔Windows 宿主〕）· `hub check` PASSED（逐字输出见 issue） |
| 14 | 官方评分口径**逐条对齐**（加分） | ✅ | [`docs/对标官方场景与评审口径.md`](docs/对标官方场景与评审口径.md)（12 场景 / 三硬点 / AI 总线 / 两形态） |

**⇒ 结论：初赛材料已齐，可提交。**

---

## 🔬 三种交付面（同一件作品，三副面孔）

官方赛道一承认**两种交付形态**（进程应用 / App Card）。「拾意」把两种都做了，并在
**OctoSense 本体（系统 app）**上把能力做到最深 —— 覆盖官方问答里"不要静态概念稿"的正面回答：

| 形态 | 位置 | 能力 | 实证 |
|---|---|---|---|
| **① L0 卡片包**（主提交） | `bundle/`（`page.card` + `bindings.json`） | 打开即渲染五屏 + 三条**总线调用**（`octos.session.history` 读助手记忆 · `octos.turn.start` 问助手 · `matrix.send_message` 真发消息） | `hub check PASSED`（Linux） · [`rinx/证据/`](rinx/证据/) |
| **② 脚本应用 · 现场造卡** | `apps/shiyi-live/bundle/`（`main.splash`，**0.7.3**） | **六个能力**（两个"读"开、模型关）：`matrix.read_messages` 读**绑定房间**的消息 → 点一条 → 当场造卡；**`matrix.send_message` 确认后把结论真发回群**（"记下了"→"办成了"）；`matrix.profile` 读你的名字 → 标出「（你）」；`octos.session.history` 读助手会话；`storage` 长期记忆；`model`（服务名 `model.complete`）代码就位、出厂关 | **Rinx 真机全链路**：导入（绑房间）→Review 列出 **6 个服务**→Run→读到 4 条真消息→点一条→造卡→**确认 → 群里真多一条回执**（记忆 0→1）（[`docs/evidence/act/`](docs/evidence/act/) + `chat-read/` + `profile/`） |
| **③ OctoSense 系统 app · 助手原地改卡** | `octos/`（系统 app 源码 + 宿主扩展） | 拾意做成 OctoSense **原生 system app**（`os.shiyi`），卡钉在**快览屏（glance）**；给它挂官方预留扩展点工具 **`shiyi.repin`**（`tools.json` 声明 `implemented_by:"host-service"` + 宿主注册同名服务）⇒ 助手在**卡的对话**里调它 → 同 `card_id` 重发 = **原地改卡**。**未碰 octos 内核一行** | **桌面（Windows）+ 小米13 双端已跑通**：模型自己发 `shiyi_repin` tool_call → 工具真返回 `{"replaced":true}` → 卡标题真的变了；工具审计 `risk:"act" / outcome:"ok"`（[`docs/evidence/repin/`](docs/evidence/repin/)，[`octos/README.md`](octos/README.md)） |
| **④ 真机连续录屏 · 端到端** | [`docs/evidence/live-run/rinx-live-end-to-end.mp4`](docs/evidence/live-run/rinx-live-end-to-end.mp4)（**20.7 秒 / 1316×1436 / H.264**，**一段连续真实录屏，非帧拼**）：导入 → Review（5 服务）→ Run → 读房间消息 → 点一条 → 造卡 → **确认行程** → 长期记忆 **0→1**。全程由宿主自带的 `MAKEPAD_REMOTE` 遥控口驱动，无人手介入；复现见 [`docs/evidence/live-run/README.md`](docs/evidence/live-run/README.md) |
| **⑤ 真机连续录屏 · 「确认 = 办事」（0.7.3）** | [`docs/evidence/act/rinx-act-end-to-end.mp4`](docs/evidence/act/rinx-act-end-to-end.mp4)（**27 秒 / 2200×1440 / H.264**，一段连续真实录屏、非帧拼）：导入（绑房间）→ Review 列出 **6 个服务** → Run → 读到房间 **4 条真消息** → 点一条 → 造卡 → **确认 → 群里真多一条回执**（长期记忆 0→1）。逐步 5 帧截图见 [`docs/evidence/act/`](docs/evidence/act/)，复现见其 `README.md` |

> **摘要分平台**：形态一交 **Linux 评测** ⇒ 留 Linux digest；形态二跑在 **Windows 宿主（Rinx）**
> ⇒ 留 Windows digest（**谁运行它，就用谁那一侧的 hub 盖章**）。形态三跑在 **OctoSense 本体**，
> 系统 app 的 bundle 摘要由构建期 `pack_system_app` **自动盖章**（无需手动签名）。
> **【定性】形态三不走 App Hub 提交** —— 官方 App Hub 只收进程应用 / App Card 两类，`os.*` 系统应用
> 提交即被拒（赛制如此，非我方缺项）。故形态三只作**「技术深度证据」**、与官方两大交付形态**并列陈述**，
> **不作「上架作品」计**；也不占本仓 App Hub 提交位。本仓真正"上架"的是形态一与形态二。
> 逐条对官方评分口径见 [`docs/对标官方场景与评审口径.md`](docs/对标官方场景与评审口径.md)。

---

| 作品标识 | 值 |
|---|---|
| app id | `shiyi` |
| 名称 | 拾意 Pickup |
| 版本 | `0.3.3`（`manifest.json`） |
| 发布版本 | **tag `v0.3.3`**（初赛冻结版；与本仓 `main` HEAD 同源。`v0.3.1` 为前一版冻结，`v0.2.2` 更早一版） |
| 固定提交号 | 本仓库 `main` 分支 HEAD（提交入口 = 官方 issue #13，已提交仓库地址） |
| 许可证 | **Apache-2.0**（`LICENSE`） |
| 公开仓库 | <https://github.com/sansanyixyz331/shiyi> |
| 作品形态 | **三形态**：① Hub 卡片包（`bundle/`）② 脚本应用（`apps/shiyi-live/bundle/`）③ OctoSense 系统 app（`octos/`，助手原地改卡） |
| 支持方式 | <https://github.com/sansanyixyz331/shiyi/issues> |

---

## A. 初赛提交物（官方赛程「初赛：需求成立、作品能跑」，**截止 10/6 23:59**〔原定 10/4，官方群公告顺延两天〕）

> 官方原话：*10/4 23:59 前提交**简短需求、可运行最小原型及启动说明、固定版本源码或包、
> 2–3 分钟演示、两张关键截图、数据来源与限制、已报名成员名单**。至少展示一次操作及可核对的
> 结果，以及一个失败或空状态。静态概念稿本身不满足原型要求。*

| # | 官方要求 | 我方对应 | 状态 |
|---|---|---|---|
| 1 | **简短需求** | `README.md` §1–§2（一句话 + 赛题对应，≤300 字） | ✅ |
| 2 | **可运行最小原型及启动说明** | 原型 = `bundle/`（卡片包）+ `cards/`（五屏）+ `src/`（流程）；启动说明 = `README.md` §5 | ✅ |
| 3 | **固定版本源码或包** | 源码 = 本仓库；包 = `bundle/`（`manifest.bundle_blake3` 内容寻址）；版本 = tag `v0.3.3` | ✅ |
| 4 | **2–3 分钟演示** | `build/_video/shiyi-walkthrough.mp4`（**2 分 15 秒**，含五屏正流程 + 两个失败态） | ✅ |
| 5 | **两张关键截图** | ① `bundle/screenshots/01-read.png`（识别：从消息读出时间/地点/类型 + 来源）② `bundle/screenshots/03-plan.png`（记忆命中"坐高铁不坐飞机"→ 只给高铁方案） | ✅ |
| 6 | **数据来源与限制** | `docs/数据来源与限制.md`（逐字段来源 + **限制：车次为演示样例**） | ✅ |
| 7 | **已报名成员名单** | 官方 issue 报名凭证：<https://github.com/gosimfoundation/hackathon-agenticapp26/issues/5#issuecomment-5852150142>（队伍 `三三Claw` / 成员 id `三三Claw-ljh`） | ✅ |
| — | **至少一次可核对的操作** | `build/verify_flow.py` 在宿主内五屏真点击（证据 `build/_evidence/flow_run.json`） | ✅ |
| — | **可核验的长期记忆（真读写）** | 点「记下」→ `.local-state/memory.json` 真被写；再跑一遍读得到；点「这次别记」sha 不变 —— 三条断言进 `flow_run.json` 的 `memory` 段 | ✅ |
| — | **一个失败或空状态** | 两个失败态：未签名被拒 / 摘要不符被拒（`_evidence` 抓图 + 宿主日志；视频 ③ 段） | ✅ |

## B. 通用材料（官方《作品提交与 App Hub》「所有作品需要的材料」6 项）

| # | 官方要求 | 我方对应 | 状态 |
|---|---|---|---|
| 1 | 公开源码仓库、**固定提交号或发布版本**、**Apache-2.0** | 仓库公开；tag `v0.3.3`；`LICENSE` = Apache-2.0 | ✅ |
| 2 | 应用**目标、适用场景、图标、运行截图、作者与支持方式** | 目标/场景 = `README.md` §1–2；图标 = `bundle/assets/icon.svg`；截图 = `bundle/screenshots/`×5；作者/支持 = `listing.json` publisher + 本文件顶部 | ✅ |
| 3 | **宿主版本、支持平台、依赖与启动说明**（让评审复现同一版本） | 见下方 §C「复现」——含宿主修订、平台、依赖、逐步命令 | ✅ |
| 4 | **数据来源、申请权限、隐私处理，以及用户授权、拒绝和失败时的行为** | `docs/数据来源与限制.md`（来源+限制+**权限=3 项，逐项列用途与不可用时行为**）+ `PRIVACY.md`（隐私）+ 该文件的「授权 / 拒绝 / 失败」三表 + §5.4 长期记忆的存储位置与写入行为 | ✅ |
| 5 | **Agent 任务演示**：输入是什么、Agent 实际完成哪些步骤、如何核验结果、哪些环节需人工确认 | `docs/Agent任务演示.md`（四问逐条）+ `src/shiyi_flow.py`（步骤真源） | ✅ |
| 6 | 运行截图、日志或视频**及对应复现步骤** | 见下方 §C 与 §D：每条证据都配一条可执行命令 | ✅ |

## C. Hub 卡片包形态交付（官方「按作品形态交付」）

| 官方要的 | 我方位置 | 状态 |
|---|---|---|
| `manifest.json` | `bundle/manifest.json` | ✅ |
| `listing.json` | `bundle/listing.json` | ✅ |
| `page.card` | `bundle/page.card`（首屏） | ✅ |
| `kit/` | `bundle/kit/native/light/kit.json`（16 组件 / 12 token） | ✅ |
| 图标 `assets/` | `bundle/assets/icon.svg` | ✅ |
| 截图 `screenshots/`（≥1 张 PNG） | `bundle/screenshots/01..05-*.png`（5 张） | ✅ |
| **预检结果** | `build/review.json`（`hub scan` 产物）+ `hub check` **PASSED**（v0.3.3 **签名版、无告警**；`grants: capabilities {matrix.send_message, octos.session.open, octos.turn.start}`） | ✅ |
| **实际运行证据** | `build/_evidence/`（`flow_run.json`〔含 `memory` 记忆取证段〕+ 5 张宿主内截图 + 宿主日志） | ✅ |

## D. 复现（评审照这个走，能拿到同一版本）

**宿主版本**：官方 OctoSense App Hub 参考实现，本作品在本地 checkout 修订
`e014fa9`（2026-10-04，含结构化准入门禁）上做发布前门禁复核——**该修订比官方文档页脚钉定的核查依据
`97c2a1fd`（2026-09-20）更新**，故不与官方核查版本冲突；早期端到端验证在 `e86d43f5`（09-23）上完成。
`hub` 与 `card-host` 自 2026-09-26 起在本地从源码构建（释放前另于 WSL/Linux 重建同版本复核门禁）。

**支持平台**：卡片包**与平台无关**（纯 manifest + card + kit 数据）。
本作品在 **Windows 桌面官方参考宿主 `card-host`** 上完成端到端验证，发布前门禁在 **Linux** 复核通过；
**目标设备平台尚未验证**（官方"支持设备/运行包"未公布），故 `listing.platforms` 只如实声明 `["windows"]`。

**端到端环境（Windows）**：本作品把设备助手 `octos.*` **真接线、真跑通**，整条链（宿主 → 内核 →
模型 → 回复上卡）在 **Windows** 上走完。为在 Windows 跑通，我们遇到并填掉了两个坑：① Rinx 用
`packaging/octos.lock.json` 把 octos 钉在精确 commit `fe08d8e6…`（官方预编译按 release tag 出，
对不上）⇒ 只能从源码编；② 官方 `hub` 门禁在 Windows 上有 `walk()` 反斜杠 bug（已报 **#75**）⇒ 在
WSL/Linux 另编同版本 `hub` 跑门禁。实测：Rinx（Windows）+ 自编 octos + DeepSeek，首屏助手行 **4 轮
回复各不相同**；确认消息真发进 `matrix.rinx.chat`。详见 `README.md §4d`。

**依赖**：Rust 工具链 + 官方共享 Makepad/Octoscript checkout（见官方 `NATIVE-WORKSPACE.md`）。
本机已备隔离环境 `F:\gosim_build\`，入口 `source F:/gosim_build/env.sh`。

**一键复现（端到端 + 失败态）**：

```sh
# 1) 门禁自检（未签名告警为开发期正常，官方原话）
"$HUB_BIN" check "$APP_REPO/bundle" --allow-unsigned        # → PASSED

# 2) 五屏端到端 + 失败态 + 长期记忆真读写断言
python build/verify_flow.py                                  # → build/_evidence/

# 2b) 只看记忆层（可选）：播种 → 写入 → 覆盖 → 落盘，全流程可看
python src/memory_store.py

# 3) 演示短片（可选：重录）
python build/record_demo.py                                  # → build/_video/*.mp4
```

逐步命令（手工路径）见 `README.md` §5。

## E. 证据索引

| 证据 | 文件 | 说明 |
|---|---|---|
| 五屏真实截图 | `bundle/screenshots/01-read.png` … `05-done.png` | 515×1073，裁掉宿主标题栏 |
| 端到端全步骤 | `build/_evidence/flow_run.json` | 每屏：控件是否在/可点/点得中 + 宿主应答 + 事件 |
| 宿主内逐屏抓图 | `build/_evidence/shots/*.png` | 五个末帧，字节各不相同（非同一张） |
| 宿主运行日志 | `build/_evidence/host_*.log` | 含 `admitted` / `[SPLASH] eval` |
| 失败态抓图 | `build/_evidence/neg_*.png` | 拒绝后**零渲染**（空白窗） |
| 演示短片 | `build/_video/shiyi-walkthrough.mp4` | 2 分 15 秒，四段 |
| **长期记忆文件** | `.local-state/memory.json` | 运行期生成（`.gitignore` 排除）；`flow_run.json` 的 `memory` 段有三条断言的实测值 |
| 门禁 / 审查包 | `build/review.json` | `hub scan` 7 问 |
| **「确认 = 办事」真机取证（0.7.3）** | `docs/evidence/act/` | Review 列出 6 服务 / 造卡 / 确认已发回群 / 群里新回执 + **27s 连续录屏** + 复现 README |
| **助手「原地改卡」双端取证（OctoSense 本体）** | `docs/evidence/repin/` + `octos/` | 桌面 + 小米13：模型自发 `shiyi_repin` tool_call / 工具真返回 `{"replaced":true}` / 工具审计 `outcome:"ok"` / 改卡前后截图 / **两端各一段端到端录屏**（`desktop_repin_end_to_end.mp4` 52s、`phone_repin_end_to_end.mp4` 150s）；宿主扩展源码（`tools.json` + `shiyi.rs` + 两处注册）/ 复现 README |
| **快览屏（glance）底层实证** | `docs/evidence/glance/` | 拾意作为**官方同级 system app**（`os.shiyi`）把卡钉进系统**快览屏**：注册日志 / 3 卡常驻 / 落盘 `picks.json` / 重启后读回 / **同 id 重钉 = 原地替换**（宿主回执 `replaced`）/ **桌面录屏 53s + 手机录屏 26s** / 3 帧 + 手机 3 帧 / 诚实边界 |
| **便携演示包（解压即跑）** | Release 资产 | `shiyi-portable-demo-v0.3.3.zip`（41 MB）<https://github.com/sansanyixyz331/shiyi/releases/download/v0.3.3/shiyi-portable-demo-v0.3.3.zip> —— 内含官方宿主 `card-host.exe` + 内嵌 Python，**双击 `一键运行.cmd` 即跑出五屏 + 两失败态 + 记忆取证**（我方已在干净目录解压后实测 `Exit code = 0`） |

## F. 已知限制（诚实声明）

- **车次数据为演示样例**（`source: sample`）：`src/shiyi_flow.py` 的 S3 三个班次
  是**示例**，接真实票务服务前**不当作事实**（见 `docs/数据来源与限制.md`）。
- **长期记忆存在本机文件里**：`.local-state/memory.json`（纯本地文件、不联网）；**首次运行用内建初始值播种**并如实标注来源。点「记下」真写、点「这次别记」不写 —— 三条断言见 `flow_run.json` 的 `memory` 段。**注意：记忆不改变“车次为演示样例”这条限制**。
- **签名**：`bundle/` **已做发布者签名**（`key_id: sansanyixyz331`，见 `bundle/manifest.json`
  的 `integrity.signature`）；`hub check` 带公钥复检 **PASSED、无告警**。未签名包仅用于开发期本地预检
  （`--allow-unsigned`）。
- **演示在桌面参考宿主**：手机端官方运行包未公布，故演示记录自桌面官方参考宿主。
