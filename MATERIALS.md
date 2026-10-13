# 提交材料清单 · 拾意 Pickup

> GOSIM Agentic App 黑客松 2026「意图即应用」· 队伍 **三三Claw**
> 本清单按类别列出本仓提交的全部材料，每条给文件路径与一句话说明。
> **一句话根：本作品是一个「真闭环」——来源它自己读进来、结果真的发回去；两头都真，环才闭得上。**
> **到文件级的全量索引见 [`docs/FILE-INDEX.md`](docs/FILE-INDEX.md)**；全仓结构见 [`docs/STRUCTURE.md`](docs/STRUCTURE.md)；按官方要求逐项对照见 [`SUBMISSION.md`](SUBMISSION.md)；逐条问答见 [`review/ANSWERS.md`](review/ANSWERS.md)。

---

## 一、作品本体

| 形态 | 路径 | 版本 | 说明 |
|---|---|---|---|
| ① **脚本应用**（主提交） | `bundle/` | **0.8.6** | `main.splash`；一句话进去 → 出卡；含**自动读群消息**（群里来新消息它自己读到就造卡；「自动读邮件」在系统 app 形态 `octos/`）；门禁 `hub check` PASSED |
| ② L0 卡片包 | `apps/shiyi-card/bundle/` | **0.3.3** | `page.card` + `bindings.json` + `apps/shiyi-card/bundle/kit/` |
| ③ 系统 app | `octos/` | **0.3.11** | `os.shiyi` + 宿主语音扩展（技术深度证据，不占 App Hub 提交位） |
| 五屏截图 | `apps/shiyi-card/bundle/screenshots/` | — | 五屏（`01-read` … `05-done`），515×1073 |

## 一·B、宿主可用性改造（陌生用户能自己跑起来的原因）

| 材料 | 路径 | 说明 |
|---|---|---|
| 宿主可用性改造说明 | `docs/Rinx宿主改造说明.md` | 逐条列出在现成宿主上做的改造：**换机可用性**（图标 / 字体资源查找兜底、脚本评估时限 64ms→3000ms —— 不打这三条，换一台电脑会出现"整界面没图标 / 中文变方框 / 应用页整块空白"）＋ **易用性**（内置与导入分界线 / 「打开·修改·删除」三个按钮 / 房间选择挪进应用界面 / 路径自适应 / 双击后零点击直进 / 浅色主题 + 深色图标 / 中英双标）＋ **三项宿主服务** `rinx.schedule` / `rinx.notify` / `rinx.speak`；许可与归属一并说明 |
| **宿主改造补丁（可自行编译 / 可审计）** | [`rinx/patches/`](rinx/patches/) | **5 个补丁 + 说明**：01 Rinx Windows 构建路径 · 02 Rinx 可用性改造 + 三项宿主服务 + 跨平台摘要修复 + 安卓原生实现 · **03 makepad 字体查找兜底** · **04 makepad 脚本评估时限 64ms→3000ms** · **05 makepad 便携包图标查找兜底**。基线、`git apply` 命令、打完能得到什么、以及"改 makepad 后必须 `cargo clean -p` 强编"的坑都写在 [`rinx/patches/README.md`](rinx/patches/README.md) |
| 改造版宿主（便携物料） | 随作品另行提供（不入仓） | 解压即用、免注册；内含改造版宿主 + 作品 + 使用说明。**为什么不在仓里**：① 内含**演示用的聊天登录态**，公开分发不合适；② 单包约 88 MB。**不拿它也能验作品** —— 走 L0（零安装、读仓内已有证据）即可 |

## 一·C、回馈上游：提交给宿主依赖的两条修复

换机可用性那两个坑**不在我们的应用代码里**，在宿主依赖的 makepad 里（资源按"**编译时那台机器**的绝对路径"查找，换机后落空）。我们把它整理成**最小、零副作用**的补丁，提交给了上游 —— 复用上游**已有**的 `cx_native::read_file_cwd_or_exe_relative`，不动正常路径行为：

| 提交 | 仓库 | 改什么 | 规模 | 状态 |
|---|---|---|---|---|
| **#121** | `OctoSense-org/makepad` | `platform/src/script/res.rs`：unpackaged 运行时改按 `<exe>/resources/` 找脚本资源（图标等） | **+20 / −0** | [已提交](https://github.com/OctoSense-org/makepad/pull/121)，待上游处理 |
| **#122** | `OctoSense-org/makepad` | `platform/src/cx_api.rs`：字体按同一位置兜底 | **+12 / −0** | [已提交](https://github.com/OctoSense-org/makepad/pull/122)，待上游处理 |

- 同一根因的**第三条**（脚本评估时限 64ms → 慢机器应用页整块空白）：官方**已在自己开 PR 讨论**（`OctoSense-org/makepad#109`，给该时限加可覆盖开关）。我们**在其下补了真实应用场景的对照数据** —— 59.6KB 的界面脚本，2015 年的 4 核机器上超时 **12 次**、2024 年的 20 线程机器上 **0 次**。
- 提交前做了**真编译验证**：在上游 makepad 源码上应用改动后 `cargo check -p makepad-platform` 通过（退出码 0）。
- **作品不依赖这两条被合并**：仓内 [`rinx/patches/`](rinx/patches/) 的 `03` / `05` 是同一修复的**自持版本**，桌面壳与安卓包都已带上并**实机验证**。上游合了是顺手之喜，不合我们也自足。

## 二、演示材料

| 材料 | 路径 | 规格 | 说明 |
|---|---|---|---|
| 桌面「工作场景」演示片 | `docs/evidence/demo-desktop-mail-20261011/拾意_桌面_工作场景_演示.mp4` | 40.8s | 一镜到底，旁白 + 硬字幕：邮件真投一封 → 它自己读到 → 出卡 → 到点念出来 |
| 手机「日常场景」演示片 | `docs/evidence/demo-phone-groupmsg-20261012/拾意_手机_群消息_演示.mp4` | 111.9s | 一镜到底，旁白 + 硬字幕：群消息真投一条 → 它自己读到 → 确认 → 真发回群 → 到点通知 |
| **队外真人试用实录** | `docs/evidence/user-trial-20261013/拾意_队外用户试用_20261013.mp4` | 146.4s | 由**队外用户**在其自己机器上解压便携包、启动、实操的实录回传；开头出镜段已整段剪除，全片不含人脸 |
| 字幕 | 上述两目录内 `字幕.srt` | — | 与成片对应 |
| 答辩幻灯片 | `docs/拾意_复赛答辩幻灯片.pptx` | 13 页 | — |
| 2 分钟陈述稿 | `docs/作品让项目多了什么_2分钟陈述.md` | — | 可照读 |

> **在线观看（B 站，已过审，便于审查）** —— 官方要求"完整的应用演示视频"，故除仓内原件外另提供在线链接：
> - 桌面「工作场景」40.8s → <https://www.bilibili.com/video/BV1xGpq6uEeF>
> - 手机「日常场景」111.9s → <https://www.bilibili.com/video/BV1tTpq6kEfa>
>
> 两条均 ≤ 2 分钟，与上方仓内文件同名，可一一对应。

## 三、证据材料（按能力分组，每组一个目录，内含截图 / 录屏 / 日志 + README）

| 能力 | 目录 | 录时版本 | 运行载体 |
|---|---|---|---|
| 确认 = 真办事（回执落回群） | `docs/evidence/act/` | 0.7.3 | Rinx |
| 端到端连续录屏 | `docs/evidence/live-run/` | 0.7.2 | Rinx |
| 助手原地改卡 | `docs/evidence/repin/` | 0.3.x | OctoSense 本体 |
| 常驻卡（快览屏） | `docs/evidence/glance/` | 0.3.x | OctoSense 本体 |
| 到点提醒 + 发声 | `docs/evidence/speak/` | 0.3.x | 真机 |
| 手机整链闭环 | `docs/evidence/phone-live-20261011/` | 0.3.10 / 0.3.11 | 小米13 |
| 到点提醒 + 开关 | `docs/evidence/phone-notify-20261011/` | 0.3.x | 小米13 |
| 到点排程 | `docs/evidence/phone-schedule-20261011/` | 0.3.x | 小米13 |
| 群消息自动改卡（修复） | `docs/evidence/group-update/` | 0.3.10 | 小米13 |
| 规则出卡 / 模型出卡 对照 | `docs/evidence/identify/` | 0.3.x / 0.7.x | OctoSense 本体 |
| 模型调用路径与降级 | `docs/evidence/model-path/` | 0.3.x | OctoSense 本体 |
| 会话记忆 | `docs/evidence/assist-memory/` | 0.3.x | OctoSense 本体 |
| 读绑定房间消息 | `docs/evidence/chat-read/` | 0.7.1 | Rinx |
| 生成器真跑 | `docs/evidence/generator/` | — | 本地 |
| 官方最新版宿主验证（rc.6 可运行 + 摘要一致） | `docs/evidence/rc6-verify-20261013/` | — | 官方 card-host / rc.6 桌面 |
| 队外真人试用（外部用户自行跑通并实操） | `docs/evidence/user-trial-20261013/` | 便携包 v0.8.6 | 队外用户机器 |
| 手机线执行链 | `rinx/证据/` | — | Rinx |
| 五屏端到端 + 失败态 + 记忆断言 | `build/_evidence/` | 卡片包 0.3.x | 官方参考宿主 |

## 四、说明文档

| 文档 | 路径 |
|---|---|
| 作品设计 | `docs/作品设计_拾意.md` |
| 数据来源与限制 | `docs/数据来源与限制.md` |
| 失败场景与回退 | `docs/失败场景与回退_系统留证.md` |
| 对标官方场景与评审口径 | `docs/对标官方场景与评审口径.md` |
| AI 接入方案 | `docs/AI接入方案.md` |
| Agent 任务演示 | `docs/Agent任务演示.md` |
| 可独立复跑（发回群闭环） | `docs/可独立复跑_发回群闭环_步骤说明.md` |
| 回归清单 | `docs/回归清单.md` |
| 造 App 的机器 | `docs/造App的机器_一页.md` |
| 生成器 MVP | `docs/生成器MVP_意图即卡.md` |
| 小程序机制笔记 | `docs/小程序机制笔记.md` |
| 速览 | `docs/评审速览.md` |

## 五、复现材料

| 材料 | 路径 | 说明 |
|---|---|---|
| **安卓现成安装包** | [`android/`](android/) | **宿主 APK（分卷，含 AI 内核）＋ 拾意应用包 ＋ 安装 / 验收 / 坑清单** —— 先看 [`android/README.md`](android/README.md) |
| **宿主改造补丁** | [`rinx/patches/`](rinx/patches/) | 5 个补丁（含 makepad 三条换机/慢机器修复），基线 + `git apply` 命令 + 复现说明 |
| 手机端复现说明（自行构建） | [`docs/手机端复现说明.md`](docs/手机端复现说明.md) | 从源码编 Rinx 安卓包 → 装机 → 导入 → 绑房间（含"打包器与宿主必须同版 makepad"这个必踩坑） |
| 复现说明 | [`README.md`](README.md) §8 | 三级：看已有证据 / 一键重跑 / 改着试（前置与耗时已如实标注） |
| 五屏端到端脚本 | `build/verify_flow.py` | 正流程 + 失败态 + 记忆三条断言 |
| 流程逻辑 | `src/shiyi_flow.py` | 可单独跑，打印每屏内容与决定 |
| 门禁报告 | `review/GATE.txt` | `hub check` 输出（含 grants 行） |
| 官方 scan 回答 | `review/ANSWERS.md` | 七问逐条，带源码行号 |
| scan 包 | `review/scan-packet.json` | `hub scan` 产物 |
| 宿主扩展 | `octos/host-extension/` | 语音扩展（可选，缺它不影响在官方宿主打开） |

## 六、仓库必备文件

`README.md` · `LICENSE`（Apache-2.0）· `PRIVACY.md` · `SUPPORT.md` · `NOTICE` · `AGENTS.md` · `docs/STRUCTURE.md` · `SUBMISSION.md` · `.gitattributes` · `.gitignore` · `.github/workflows/publish-app.yml`

## 七、已知限制

- `matrix.*`（读消息 / 档案 / 发消息）三项由 **Rinx** 提供，**官方 OctoSense 宿主不提供**；在官方宿主上运行时**如实降级**、不假装（详见 [`review/ANSWERS.md`](review/ANSWERS.md) 第 3 问）。
- 到点排程 / 发声（`rinx.schedule`）同为 Rinx 专有，宿主缺失时同样降级。
- 手机端**未在 OctoSense Home 宿主上验证**；`listing.platforms` 的 `android` 指实测过的运行路径（真机 + Rinx 本地导入）。
- 桌面端走标准 SMTP / IMAP 外部服务器，**未做企业邮箱域规模验证**。
- **宿主侧一道环境要求**：宿主对"迷你应用脚本评估"有 **64ms 默认时限**（`makepad/widgets/src/widget_async.rs`），本作品界面脚本 59.6KB，**在较慢的机器上会被掐断 ⇒ 正文整块空白**（宿主日志 `script time budget exceeded`）。**实测 3 台机器对照得出**；对策：用我们修好的宿主（[`rinx/patches/04`](rinx/patches/04-makepad-splash-eval-budget.patch)，放宽到 3000ms），或走零安装的 L0 证据层。**官方 `card-host` 已在本机实测（2026-10-13）**：直接用它跑本仓 `bundle/` → **`admitted` → `[SPLASH] eval: 59625 bytes view=true`** + 抓到完整画面帧（139 KB）+ 元素快照 ⇒ **作品在官方原始宿主（未打任何补丁）上能正常运行**。该 64ms 是**较慢的机器**才触发的边界（本机 14 核不触发），不是作品缺陷。
- **非编译机上官方宿主可能渲染不全**（文字不显示 / 图标缺失）：宿主/makepad 的资源按**编译时那台机器的绝对路径**查找，换机后落空（`card-host` 日志会打 `font member … is not available in this build`）；**不是作品缺陷**（同一份 bundle 在编译机完整渲染）。同类修复已作为补丁提交：`rinx/patches/03`（字体）、`05`（图标）。
- 逐条限制见 [`docs/数据来源与限制.md`](docs/数据来源与限制.md)。

## 附、材料与官方评分维度的对应

| 官方维度 | 对应材料 |
|---|---|
| ① 需求与任务价值 | 演示材料（两条场景片）· **队外真人试用实录**（`docs/evidence/user-trial-20261013/`）· `docs/作品设计_拾意.md` |
| ② 核心流程可用性 | 证据材料（`docs/evidence/act/`、`docs/evidence/repin/`）· `build/_evidence/flow_run.json` · `review/GATE.txt` |
| ③ 数据来源与失败状态 | `build/_evidence/neg_*.log`、`neg_*.png` · `docs/evidence/identify/`、`docs/evidence/model-path/` · `docs/数据来源与限制.md` · `docs/失败场景与回退_系统留证.md` |
| ④ 复现与材料 | 复现材料（本节五）· 上游修复提交（本节一·C，#121 / #122）· `review/` · `SUBMISSION.md` |
