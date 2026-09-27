# 提交材料对照表 · 拾意 Pickup

> GOSIM **Agentic App 黑客松 2026「意图即应用」** · 赛道一（OctoSense / AppCard）
> 本文件把官方要求的每一件材料，逐条对应到本仓库里的**具体文件、链接与复现命令**，
> 供评委核查、也供提交前收口。**每一项都能当场点开看。**

| 作品标识 | 值 |
|---|---|
| app id | `shiyi` |
| 名称 | 拾意 Pickup |
| 版本 | `0.2.0`（`manifest.json`） |
| 发布版本 | **tag `v0.2.0`** |
| 固定提交号 | 见本仓库 `main` 分支 HEAD（提交时锁定） |
| 许可证 | **Apache-2.0**（`LICENSE`） |
| 公开仓库 | <https://github.com/sansanyixyz331/shiyi> |
| 作品形态 | **Hub 卡片包**（manifest + listing + page.card + kit） |
| 支持方式 | <https://github.com/sansanyixyz331/shiyi/issues> |

---

## A. 初赛提交物（官方赛程「初赛：需求成立、作品能跑」，10/4 23:59 前）

> 官方原话：*10/4 23:59 前提交**简短需求、可运行最小原型及启动说明、固定版本源码或包、
> 2–3 分钟演示、两张关键截图、数据来源与限制、已报名成员名单**。至少展示一次操作及可核对的
> 结果，以及一个失败或空状态。静态概念稿本身不满足原型要求。*

| # | 官方要求 | 我方对应 | 状态 |
|---|---|---|---|
| 1 | **简短需求** | `README.md` §1–§2（一句话 + 赛题对应，≤300 字） | ✅ |
| 2 | **可运行最小原型及启动说明** | 原型 = `bundle/`（卡片包）+ `cards/`（五屏）+ `src/`（流程）；启动说明 = `README.md` §5 | ✅ |
| 3 | **固定版本源码或包** | 源码 = 本仓库；包 = `bundle/`（`manifest.bundle_blake3` 内容寻址）；版本 = tag `v0.2.0` | ✅ |
| 4 | **2–3 分钟演示** | `build/_video/shiyi-walkthrough.mp4`（**2 分 17 秒**，含五屏正流程 + 两个失败态） | ✅ |
| 5 | **两张关键截图** | ① `bundle/screenshots/01-read.png`（识别：从消息读出时间/地点/类型 + 来源）② `bundle/screenshots/03-plan.png`（记忆命中"坐高铁不坐飞机"→ 只给高铁方案） | ✅ |
| 6 | **数据来源与限制** | `docs/数据来源与限制.md`（逐字段来源 + **限制：车次为演示样例**） | ✅ |
| 7 | **已报名成员名单** | 官方 issue 报名凭证：<https://github.com/gosimfoundation/hackathon-agenticapp26/issues/5#issuecomment-5852150142>（队伍 `三三Claw` / 成员 id `三三Claw-ljh`） | ✅ |
| — | **至少一次可核对的操作** | `build/verify_flow.py` 在宿主内五屏真点击（证据 `build/_evidence/flow_run.json`） | ✅ |
| — | **一个失败或空状态** | 两个失败态：未签名被拒 / 摘要不符被拒（`_evidence` 抓图 + 宿主日志；视频 ③ 段） | ✅ |

## B. 通用材料（官方《作品提交与 App Hub》「所有作品需要的材料」6 项）

| # | 官方要求 | 我方对应 | 状态 |
|---|---|---|---|
| 1 | 公开源码仓库、**固定提交号或发布版本**、**Apache-2.0** | 仓库公开；tag `v0.2.0`；`LICENSE` = Apache-2.0 | ✅ |
| 2 | 应用**目标、适用场景、图标、运行截图、作者与支持方式** | 目标/场景 = `README.md` §1–2；图标 = `bundle/assets/icon.svg`；截图 = `bundle/screenshots/`×5；作者/支持 = `listing.json` publisher + 本文件顶部 | ✅ |
| 3 | **宿主版本、支持平台、依赖与启动说明**（让评审复现同一版本） | 见下方 §C「复现」——含宿主修订、平台、依赖、逐步命令 | ✅ |
| 4 | **数据来源、申请权限、隐私处理，以及用户授权、拒绝和失败时的行为** | `docs/数据来源与限制.md`（来源+限制+权限=零）+ `PRIVACY.md`（隐私）+ 该文件的「授权 / 拒绝 / 失败」三表 | ✅ |
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
| **预检结果** | `build/review.json`（`hub scan` 产物，7 问）+ `hub check` **PASSED** | ✅ |
| **实际运行证据** | `build/_evidence/`（`flow_run.json` + 5 张宿主内截图 + 宿主日志） | ✅ |

## D. 复现（评审照这个走，能拿到同一版本）

**宿主版本**：官方 OctoSense App Hub 参考实现，本作品在本地 checkout 修订
`e86d43f5`（2026-09-23）上验证——**该修订比官方文档页脚钉定的核查依据
`97c2a1fd`（2026-09-20）更新**，故不与官方核查版本冲突。
`hub` 与 `card-host` 均于 2026-09-26 在本地从源码构建。

**支持平台**：卡片包**与平台无关**（纯 manifest + card + kit 数据）。
本作品在 **Windows 桌面官方参考宿主 `card-host`** 上完成端到端验证；
目标设备平台为 **Android**（官方"支持设备/运行包"公布后直接适用）。

**依赖**：Rust 工具链 + 官方共享 Makepad/Octoscript checkout（见官方 `NATIVE-WORKSPACE.md`）。
本机已备隔离环境 `F:\gosim_build\`，入口 `source F:/gosim_build/env.sh`。

**一键复现（端到端 + 失败态）**：

```sh
# 1) 门禁自检（未签名告警为开发期正常，官方原话）
"$HUB_BIN" check "$APP_REPO/bundle" --allow-unsigned        # → PASSED

# 2) 五屏端到端：起官方参考宿主 → 逐屏渲染 → 真点击 → 断言下一屏 → 抓图
python build/verify_flow.py                                  # → build/_evidence/

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
| 演示短片 | `build/_video/shiyi-walkthrough.mp4` | 2 分 17 秒，四段 |
| 门禁 / 审查包 | `build/review.json` | `hub scan` 7 问 |

## F. 已知限制（诚实声明）

- **车次数据为演示样例**（`source: sample`）：`src/shiyi_flow.py` 的 S3 三个班次
  是**示例**，接真实票务服务前**不当作事实**（见 `docs/数据来源与限制.md`）。
- **记忆层当前为本地演示实现**：卡片上的"老规矩"来自本地偏好库（`DEFAULT_PREFS`），
  读写闭环在开发期实现中；卡片已按要求**显式写出"命中哪条、改变了什么"**。
- **未签名**：`bundle/` 未做发布者签名（`hub check` 的唯一告警）；
  官方明示未签名包可本地预检、`--allow-unsigned` 即为该场景。
- **演示在桌面参考宿主**：手机端官方运行包未公布，故演示记录自桌面官方参考宿主。
