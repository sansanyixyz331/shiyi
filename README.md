# 拾意 · Pickup

> **从你的聊天里，读出你没说出口的安排。**
> *Reads the plan you never said out loud, from the messages you already sent.*

GOSIM **Agentic App 黑客松 2026「意图即应用」** 参赛作品。

---

## ⚡ 30 秒版（评委先看这段）

| | |
|---|---|
| **这是什么** | **OctoScript L0 卡片应用**——把消息里一句随手的话变成一张"等你确认"的卡片；你确认它才执行，并写进长期记忆 |
| **怎么跑（零依赖）** | 解压 `拾意_便携演示包_完整版_20260930.zip` → 双击 **`一键运行.cmd`** → 五个窗口依次弹出、结束打印 `Exit code = 0`（自带宿主与运行库，**不用装任何东西**）；官方参考宿主跑法见 **§5** |
| **形态 / 场景** | **两种官方承认的形态 + 一条本体形态**：① **L0 卡片包**（主提交，`bundle/`）② **脚本应用 · 现场造卡**（`apps/shiyi-live/`）③ **OctoSense 系统 app**（`octos/`，原生快览屏卡 + **助手原地改卡**）；官方 12 场景之「**即时消息**」（宿主 **Rinx**，即早期 `robrix2`） |
| **达标** | OctoScript 应用 ✅ · 公开仓 Apache-2.0 ✅ · README ✅ · 失败态 ✅ · 2 分 15 秒演示 ✅ |
| **三种交付面** | ① **L0 卡片**（`bundle/`）：打开即渲染五屏 + 三条**总线调用**（读助手记忆 / 问助手 / 真发消息）；② **脚本应用**（`apps/shiyi-live/`）：**一句话当场长出卡**，改一下 / **确认（结果真发回绑定群）** / 再来一张，真交互；③ **OctoSense 系统 app**（`octos/`）：卡钉在**快览屏**、**助手能在卡的对话里原地改卡**（桌面 + 手机双端已跑通，未碰内核一行）。同一套识别口径与长期记忆 |
| **一页速览** | [`评审速览.md`](评审速览.md)（3 分钟看懂）· **[`docs/对标官方场景与评审口径.md`](docs/对标官方场景与评审口径.md)（逐条对官方评分口径）** · 材料对照 [`SUBMISSION.md`](SUBMISSION.md) |

---

## 1. 一句话

聊天里一条随手的话——"下周三我得去趟深圳"——藏着时间、地点、和一个没人接手的待办。
**拾意**把它认出来，做成一张**等你点头的卡片**；你确认，它去执行；同时它记得你的老规矩
（"我不坐飞机""周三下午别排事"），下次自动避开。

**Agent 干活，人保留控制。**

## 2. 赛题对应

| 官方题眼 | 拾意的对应 |
|---|---|
| 意图不一定来自你说的话 | 意图来自**消息正文**（不是 prompt） |
| 藏在一条消息、一个时间点、一次状态变化里 | 时间词 / 地点词 / 承诺词 / 状态变化 |
| 整理成**等用户确认的卡片** | 每步一张待确认卡，确认后才执行 |
| 应用为人保留控制 | 全程可撤回、可接管、来源可查 |

**官方 12 场景**：本作品落在「**即时消息**」场景（宿主 **Rinx**，即官方早期的 `robrix2`）。

## 3. 与官方范例的差异（我们做什么不一样）

官方范例 `aircon` 演示的是"**购物—物流—安装—付款**"的服务链路（事实来自外部服务）。
拾意演示的是"**消息 → 意图 → 卡片 → 执行**"的认知链路（事实来自消息原文 + 真实服务），
并且多一层 **长期记忆**：它不仅处理这一条消息，还**记得你的历史偏好**并据此改变建议。

## 4. 仓库结构

```
shiyi/
  AGENTS.md              # 开发约定（给 agent / 协作者）
  README.md              # 本文件
  LICENSE                # Apache-2.0
  PRIVACY.md             # 数据与隐私声明（listing.privacy_policy_url 指向它）
  bundle/                # ★ 唯一的发布产物（提交物）—— 只带首屏
    manifest.json        # 应用身份 / 版本 / 完整性与能力声明（capabilities: matrix.send_message, octos.session.open, octos.turn.start）
    listing.json         # 商店条目：描述 / 分类 / 截图 / 图标 / 许可
    bindings.json        # 能力接线：on_open 问本机设备助手一句，结果写进卡片数据槽 read
    page.card            # 屏 1 · 识别（Octoscript L0，手写）
    page.data.json       # 该屏布局（坐标实测）
    kit/native/light/kit.json   # 五屏共用的组件包（16 组件 / 12 token）
    assets/icon.svg
    screenshots/         # 五屏真实截图（01-read … 05-done）
  cards/                 # ★ 完整五屏：屏 = 独立卡（官方 aircon 12 屏同构）
    shiyi-01-read/       #   page.card + page.data.json
    shiyi-02-ask/        #   + service-actions.json（该屏按钮的含义）
    shiyi-03-plan/       #   + screenshots/01.png（该屏真实截图）
    shiyi-04-memo/
    shiyi-05-done/
  src/                   # 服务逻辑（Agent 侧）
    intent_card.py       # 识别内核：消息 → 结构化事实（每条带来源）
    shiyi_flow.py        # 五屏流程状态机（事件名直接读 service-actions.json）
    memory_store.py      # 本机长期记忆：真读写 .local-state/memory.json（零权限/零网络）
  docs/
    作品设计_拾意.md      # 选题 / 流程 / 数据来源 / no-facts 声明
    小程序机制笔记.md      # Hub app / Card bundle / Image-to-AppCard 机制
  ai/                    # ★ 不进 bundle：接设备助手（AI）的契约备件
    AGENT.md             #   应用自己的 Agent 契约（角色 / 输入 / 验收 / 记忆 / 降级）
    tools.json           #   三个工具：intent.read / memo.read / memo.save
    manifest.ai.json     #   AI 版清单（capabilities: storage, model + agent 块）
    本地跑通_20261004.md  #   ★ 本地 AI 跑通实证与配方（Rinx → 本地 octos 内核 → DeepSeek）
    证据/                 #   内核会话 / 内核日志 / 验收截图 / **卡片显示回复**实拍（已脱敏）
    templates/            #   ★ 显示 AI 回复的卡 + bindings + data 占位（可直接复用）
  rinx/                  # ★ 不进 bundle：宿主执行扩展 + 真机实证
    manifest.send.json   #   执行版清单（capabilities: matrix.send_message）；「真发送」的独立接线参考与真机实证（同一能力自 0.3.3 起已进 bundle）
    bindings.json        #   能力接线：on_open 声明
    证据/                 #   真机实证（Review / Run 截图 + 房间消息 JSON）
  octos/                 # ★ 不进 bundle：OctoSense 本体扩展（助手「原地改卡」）
    apps/shiyi/bundle/   #   拾意做成 OctoSense 系统 app（manifest + main.splash + tools.json 声明 shiyi.repin）
    crates/shell/src/    #   宿主侧扩展（shiyi.rs：捡起自己的 host service；对齐官方 Calendar/notice 的写法）
    README.md            #   原理 / 代码落点 / 复现 / 边界（未碰内核一行）
  build/                 # ★ 不进 bundle
    render_cards.py      # 逐屏渲染：组临时 bundle → 盖章 → 起宿主 → 抓图 → 裁图
    sync_bundle.py       # 首屏 + 五张截图 → bundle（单一真源，防止两份不一致）
    crop_png.py          # 纯 stdlib 裁图
    review.json          # 官方审查包（scan 产物）
```

> 规则：**只有 `bundle/` 是提交物**；源码、脚本、密钥、审查包一律留在 `bundle/` 外。

## 4b. 五屏

一个消息走完五个决策点，**一屏一屏推进**（屏 = 独立卡，不是卡内状态机）：

| 屏 | 目录 | 这一屏在干什么 |
|---|---|---|
| 1 识别 | `cards/shiyi-01-read` | 原话 + 抽出的事实（每条标「出自原文」或「识别所得」）→ 确认 |
| 2 追问 | `cards/shiyi-02-ask` | 只问消息永远说不出的两样（几点走 / 从哪出发）→ 定 |
| 3 方案 | `cards/shiyi-03-plan` | 把老规矩摆出来，再给一版被它筛过的候选 → 选 |
| 4 记忆 | `cards/shiyi-04-memo` | 旧规矩 vs 这次要加的，都可读可改 → 记 / 不记 |
| 5 完成 | `cards/shiyi-05-done` | 回执三行：**一件真做了、两件明说没动**（不摆"已完成"的样子），无积分无徽章 → 看行程 / 重开 |

## 4c. 扩展能力：设备助手（AI）与宿主执行

`bundle/manifest.json` 声明**三条官方白名单能力**：`octos.session.open`、`octos.turn.start`、
`matrix.send_message`。`bundle/bindings.json` 在打开首屏时按序做三件事：开一个与设备助手的会话、
问它一句、把这一屏的回执发进**导入时选定的**聊天房间。**三条全部在提交物里**，不是备件：

| 线 | 接到哪（官方能力） | 状态 | 位置 |
|---|---|---|---|
| **设备助手（AI）** | `octos.session.open` · `octos.turn.start` | ✅ **已进提交物**：`bundle/` 声明 + `bindings.json` 接线，首屏卡多一行"助手给的答案" | `bundle/` + [`ai/`](ai/) |
| **宿主执行（真发消息）** | `matrix.send_message` | ✅ **已进提交物**（0.3.3 起）：同一条 `bindings.json` 把回执发进聊天；发不出去也不影响卡片 | `bundle/` + [`rinx/`](rinx/) |

**① AI 线 —— 接"设备助手"（已经写进提交物本身）**
`bundle/manifest.json` 声明官方白名单能力 **`octos.session.open` + `octos.turn.start`**；
`bundle/bindings.json` 在打开时问本机助手一句"这句话还缺什么才能排成行程"，答案**印在首屏卡上**，
与本地规则那条**并列**：

```
还没定：坐哪班、几点。这一步我不猜。          ← 本地规则（永远在）
还缺出发城市和（往返）时间                    ← 设备助手（本机 octos 内核）
```

- **两条路都真实，且卡不依赖任何服务成功**：助手在 → 多渲染一行助手答案；
  助手不在 / 回合失败（例如宿主没配 provider）→ `when read.is_ok` guard 为假，**那条路径根本不求值** ⇒
  卡片照常显示、**不报错**（这条是实测出来的：见 [`ai/证据/`](ai/证据/) 的两张对照图）。
- 官方门禁实测（Linux 侧 `hub`）：`hub check` → **`shiyi 0.3.3 — PASSED`**（**发布者签名版，无告警**；未签名包在开发期需加 `--allow-unsigned`），`grants: capabilities {matrix.send_message, octos.session.open, octos.turn.start}`；
  官方参考宿主 `card-host` 也正常 admit + 渲染（**23 节点、0 诊断**）。
- **在官方 `card-host` 里长什么样（重要，避免误判为缺陷）**：官方参考宿主**不提供任何 host service**，
  所以它渲染的是**本地规则行**（23 节点）——**这就是官方要求的"不依赖服务也完整可用"**，不是缺功能。
  助手行只在**配了本机助手的宿主**（如 Rinx + 本机 octos 内核）里多出来。**两处都是设计意图**：
  官方原文 "`card-host` provides no host services … **build the app to be complete without them**"，
  我方用 `when read.is_ok` guard 兑现了这一点。
- 完整实证与配方：[`ai/本地跑通_20261004.md`](ai/本地跑通_20261004.md)（内核往返 4 轮 + 出货版实拍）、
  [`ai/templates/`](ai/templates/)（可复用三件）、[`ai/README.md`](ai/README.md)（接入面说明）。

**② 执行线 —— 让这一屏的回执真的发出去**

`matrix.send_message` 也在同一份 `bundle/bindings.json` 里：打开首屏时，宿主把一句话发进
**导入时选定的房间**。这一条**本机真跑通** —— Review 界面明写 `Services: matrix.send_message`
与 `Allowed room`，消息 **API 可查**（见 [`rinx/证据/`](rinx/证据/)）：

```json
{ "content": { "body": "【拾意 Pickup】下周三去深圳 — 已确认，日程已记下。",
               "msgtype": "m.text" },
  "sender": "@sansanyi331:matrix.rinx.chat",
  "room_id": "!6OTFycyqxSkwYHJuBr:matrix.rinx.chat",
  "type": "m.room.message" }
```

- **全流程实录**：[`rinx/证据/演示视频_Rinx执行链_拾意.mp4`](rinx/证据/演示视频_Rinx执行链_拾意.mp4)（43 秒，带字幕：导入 → 填房间 → Review → Run → 消息进聊天）
- **真机连续录屏（0.7.2 五能力端到端）**：[`docs/evidence/live-run/rinx-live-end-to-end.mp4`](docs/evidence/live-run/rinx-live-end-to-end.mp4)（**20.7 秒，一段连续真实录屏，非帧拼**：Review 5 服务 → Run → 读房间消息 → 造卡 → 确认 → 记忆 0→1；由 Rinx 自带 `MAKEPAD_REMOTE` 遥控口驱动，复现见同目录 README）

> **它放在哪里、为什么会这样**：`matrix.send_message` **在官方封闭能力清单里**（45 个 `matrix.*` 之一），
> 声明它是**合法**的。发到哪个房间**不是卡片说了算** —— 房间在**导入表单里手填、由宿主绑进租约**，
> 没填就答 `not attached to a room`。而官方参考宿主 `card-host` **不注册任何 host service**
> ⇒ 在那里三个调用**一个都不会发生**（本机实测：带 `bindings.json` 与不带，首屏渲染**逐字节相同**），
> 卡片照常完整显示。**每个读服务结果的路径都包在 `when X.is_ok` 里**：助手不在、房间没绑、模型没配，
> 都只是让那一行不出现，**不会让卡片崩，也不会让应用打不开**。

## 4d. 端到端环境：这条线是在 Windows 上跑通的

本作品把设备助手 `octos.*` **真接线、真跑通**，整条链（宿主 → 内核 → 模型 → 回复上卡）是在 **Windows** 上走完的。

在 Windows 上跑通，我们遇到了两个坑、各自填掉：

1. **官方预编译的 octos 对不上。** Rinx 用 `packaging/octos.lock.json` 把内核钉在一个**精确 commit**（`fe08d8e6…`）上；而官方发行的预编译包是按 **release tag** 出的（rc.10–rc.13 对应的 commit 都不是它）⇒ **只能按 lock 从源码编**（`tools/package-octos.py desktop`）。
2. **官方 `hub` 门禁在 Windows 上自身有 bug。** 新准入门（PR #56）里，目录遍历产出的相对路径在 Windows 是 `\`，紧接着的校验又**禁止路径含 `\`** ⇒ **Windows 上任何带子目录的包都会被拒**（Linux/macOS 出 `/`，不触发）。我们在 **WSL/Linux** 另编一份同版本 `hub` 来跑门禁（官方判据环境本就是 Linux/macOS），并把该 bug 报给了官方（**issue #75**）。

填完这两个坑之后的端到端结果：

- **Rinx（Windows）+ 本机自编 octos 内核 + DeepSeek**：首屏卡的助手行**连续 4 轮渲染出各不相同的真实回复**（[`ai/本地跑通_20261004.md`](ai/本地跑通_20261004.md)）。
- **消息真发出**：经 Rinx 把确认消息发进 Matrix 房间 `!6OTFycyqxSkwYHJuBr:matrix.rinx.chat`（[`rinx/证据/`](rinx/证据/)，房间消息 API 可查）。

> 这一版是在 **Windows**——官方工具支持相对弱的平台——上完成的端到端助手往返；过程中顺手替官方抓到一个 Windows 专属的门禁 bug（#75）。这是**实测填坑**，不是配置出来的。

## 5. 怎么跑（官方参考宿主）

### 5.1 复现环境（让评审拿到同一版本）

| 项 | 值 |
|---|---|
| **宿主** | 官方 OctoSense App Hub 参考实现 `card-host` |
| **宿主修订** | 本地 checkout 最新 `e014fa9`（2026-10-04，含结构化准入门禁）；早期端到端验证在 `e86d43f5`（09-23）上完成 |
| **构建** | `hub` / `card-host` 自 2026-09-26 起从源码构建（本机隔离环境）；发布前门禁另在 **WSL/Linux** 重建同版本复核 |
| **支持平台** | 卡片包**与平台无关**（纯数据）；本作品在 **Windows 桌面参考宿主**完成端到端验证，发布前门禁在 **Linux** 复核通过；**目标设备平台尚未验证**（官方运行包未公布）——故 `listing.platforms` 只如实声明 `["windows"]` |
| **依赖** | Rust 工具链 + 共享 Makepad/Octoscript checkout（见官方 `NATIVE-WORKSPACE.md`） |

### 5.2 启动说明

前置：Rust 工具链 + 共享 Makepad/Octoscript checkout（见官方 `NATIVE-WORKSPACE.md`）。

本机已备一套隔离环境（`F:\gosim_build\`，入口 `source F:/gosim_build/env.sh`），
`hub` 与 `card-host` 已于 2026-09-26 在其中编译并实跑。以下命令是**实测通过**的那一套。

```sh
source F:/gosim_build/env.sh
export HUB_BIN=F:/gosim_build/cache/target/debug/hub.exe
export CARD_HOST_BIN=F:/gosim_build/cache/target/debug/card-host.exe
export APP_REPO=C:/gosim_agentic/05_app/shiyi

# 1. 盖章（每次改完 bundle 都要重盖；改动会改变摘要）
"$HUB_BIN" stamp "$APP_REPO/bundle"

# 2. 门禁自检（v0.3.3 已签名；未签名包加 --allow-unsigned 的告警属开发期正常）
"$HUB_BIN" check "$APP_REPO/bundle" --allow-unsigned
# 2b. 复检发布者签名（可选）
# "$HUB_BIN" check "$APP_REPO/bundle" --publisher-key sansanyixyz331=<公钥>

# 3. 生成审查包（必须放 bundle 之外）
"$HUB_BIN" scan "$APP_REPO/bundle" --packet "$APP_REPO/build/review.json"

# 4. 参考宿主运行（须在 Hub 仓库里启动，宿主资源才解析得到）
cd F:/gosim_build/octosense-org/OctoSense-App-Hub
"$CARD_HOST_BIN" --bundle "$APP_REPO/bundle" --app-data "$APP_REPO/.local-state" --allow-unsigned --remote

# 5. 抓真实截图（端点取第 4 步日志里打印的 127.0.0.1:<PORT>）
curl --fail --silent --show-error "$APP_ENDPOINT/g?raw=1" -o "$APP_REPO/build/shots/shot.png"
curl --fail --silent --show-error "$APP_ENDPOINT/quit"
```

截图带宿主自绘标题栏（约 42 px），用 `build/crop_png.py`（纯 stdlib，零依赖）
裁掉后再放进 `bundle/screenshots/`。

以上是手工路径。**五屏已自动化**，日常只用两条命令：

```sh
# 五屏全跑一遍：每屏组临时 bundle（共用 kit）→ 盖章 → 起宿主 → 抓图 → 裁图
python build/render_cards.py                 # 或只跑某屏：render_cards.py shiyi-02-ask

# 同步：首屏 → bundle/page.card，五张截图 → bundle/screenshots/，顺带刷新 listing
python build/sync_bundle.py

# 然后照旧 stamp / check / scan
```

`cards/` 是五屏的唯一真源，`bundle/` 由 `sync_bundle.py` 从它生成 —— 不存在
"bundle 和 cards 两份首屏互相不一致"这种事。跑流程看逻辑：

```sh
python src/shiyi_flow.py        # 走完五屏，打印每屏内容与走过的决定
```

**端到端验证（A3 + B4 一次跑完）**：

```sh
python build/verify_flow.py                 # 正流程 + 两个失败态
python build/verify_flow.py --positive      # 只跑正流程
python build/verify_flow.py --negative      # 只跑失败态
```

它把「一条消息 → 逐屏卡 → 用户点按钮 → 下一屏」在官方参考宿主里真跑一遍：
每屏先组包盖章、起宿主、等稳定帧、抓图，再用 `/snap` 证实目标控件**在、可见、可点**，
然后 `/click` 打到它的中心，取该控件在 `service-actions.json` 里声明的事件名推下一屏。
证据落在 `build/_evidence/`：`flow_run.json`（全步骤）+ `shots/*.png`（每屏宿主内截图）+ 宿主日志。

同一次运行里还做**长期记忆的真读写取证**（对应官方「结果核验」轴），三条断言：

| 断言 | 做法 | 期望 |
|---|---|---|
| `keep_wrote_file` | 点「记下」 | 本机记忆文件真被写（留路径 / sha / 内容 / 时间戳） |
| `memory_is_effective` | 再跑一遍 | 读得到上一遍写进去的东西（证明不是常量） |
| `skip_left_file_untouched` | 点「这次别记」 | 文件 sha 一个字节不变 |

三条都记进 `flow_run.json` 的 `memory` 段。只想看记忆层本身：`python src/memory_store.py`。

**演示短片（A4）**：

```sh
python build/record_demo.py                 # 全片（片头卡 + 五屏正流程 + 两个失败态 + 片尾卡）
python build/record_demo.py --from-frames   # 只重编码，不重录
python build/record_demo.py --no-caption    # 不要字幕
```

跑的是上面同一条链路，区别只在**一边跑一边逐帧录宿主窗口本身**（宿主自带的
`/g?raw=1`，10 fps），再用 ffmpeg 合成 mp4。字幕用的全是卡内真实文案，并且先在
底部 pad 出一条字幕带再画进去 —— 不遮卡片、不盖按钮。

全片四段：① 片头卡 → ② 五屏正流程（每步真点击）→ ③ **两个失败态**（未签名 /
包被改过一个字符 → 真起宿主、真被拒、录到拒绝后的空窗口，画面上叠宿主原话）
→ ④ 片尾卡。

成片：`build/_video/shiyi-walkthrough.mp4`（**2 分 16 秒 / 1355 帧**，满足官方
初赛"2–3 分钟演示"的要求）。说明：这是**桌面官方参考宿主**里的真实运行录制；
手机端要等官方"支持设备／运行包"公布（官方那条 HTTP 自动化通道在 Android 上被
编译掉了，手机端另有真机触摸注入的一套，是几小时级的活）。

## 6. 当前状态

| 项 | 状态 |
|---|---|
| 选题与设计 | ✅ 已定（见 `docs/作品设计_拾意.md`） |
| 仓库骨架 | ✅ 已搭 |
| 卡片本体 | ✅ **五屏全部手写 L0，逐屏实跑渲染** |
| kit 组件包 | ✅ 五屏共用 `bundle/kit/native/light/kit.json`（16 组件 + 12 token） |
| 卡外动作 | ✅ 每屏 `service-actions.json`（**14 个控件 / 14 个事件**，与流程同源） |
| 宿主运行 | ✅ `card-host` 逐屏跑通（五屏 `[SPLASH] … view=true`，零 lower 错误） |
| 真实截图 | ✅ 五张 `515×1073`（实拍后裁掉宿主标题栏，入 bundle 与各屏目录） |
| 门禁 | ✅ `hub check` **PASSED**（**v0.3.3 发布者签名版，无告警**；Linux 侧 `hub`） |
| 审查包 | ✅ `build/review.json`（7 个审查问题，放 bundle 之外） |
| 服务逻辑 | ✅ 五屏流程状态机（`src/shiyi_flow.py`）**已与官方参考宿主串成端到端** |
| 端到端验证（A3） | ✅ `build/verify_flow.py`：五屏逐屏真渲染 + 每步真实点击命中控件 + 事件链推进 → `build/_evidence/` |
| 失败态取证（B4） | ✅ 未签名 / 摘要不符 → 宿主拒绝且**零渲染**（fail-closed），日志与抓图留证 |
| 演示短片（A4） | ✅ `build/_video/shiyi-walkthrough.mp4`（**2 分 15 秒 / 1350 帧**：片头卡 + 五屏正流程 + **两个失败态** + 片尾卡；**真实宿主逐帧录制，非动画**） |
| **本机记忆（真读写）** | ✅ `src/memory_store.py`：本机 JSON 文件，零权限零网络；点「记下」真写、点「这次别记」一个字节不写；三条断言进 `flow_run.json` |
| **设备助手（AI · 已进提交物）** | ✅ `bundle/` 声明 `octos.session.open`+`octos.turn.start` + `bindings.json` 接线；首屏卡多一行助手答案，助手不在时 guard 兜底、**不报错**；实证 [`ai/证据/`](ai/证据/) |
| **宿主执行 · 真发消息（已进提交物）** | ✅ `bundle/` 声明 `matrix.send_message` + 同一条 `bindings.json`：打开首屏把回执发进导入时选定的房间；**本机真跑通**（实证在 `rinx/证据/`） |
| 签名 / 提交 | ✅ **已签名**（`sansanyixyz331`；`hub sign-manifest` + 公钥复检 `PASSED`）· `hub check` **PASSED**（`grants: capabilities {matrix.send_message, octos.session.open, octos.turn.start}`）· App Hub issue **#76**（提交物升到 `0.3.3` 后同步更新） |

## 7. 实测记录（2026-09-26 跑通的关键契约）

参考宿主 `card-host` 走的是**测量式设计**路径，不是自动布局。三条契约必须同时满足：

1. **`page.card` 里每个节点都必须是 Kit 节点。** `octoscript_ui_l0::kit_pack::tree`
   对非 Kit 节点直接拒绝（`native pack requires a Kit component, got …`）。
   纯语义角色（`Surface`/`Col`/`TextTitle`…）的 L0 卡片由 `kit-host` 渲染，
   **不是这个宿主** —— 这是本轮最大的一个坑。
2. **几何在 `page.data.json` 的 `$kit.placements`**（每个 instance 一条
   `{component, layout:{x,y,w,h}}`）；**外观在 `kit.json` 的 `components`**，
   用 `{"$token": …}` 引 tokens。两边 `component` 名必须一致，
   且 `Kit` 的 `props` 里声明的参数调用时必须全传。
3. **文字节点必须给 `size` 和 `font_src`**，且 `font_src` 必须是
   **`crate名:路径`**（冒号，不是斜杠）—— 写成斜杠会静默找不到字体、
   中文全部渲染成豆腐块。本宿主是 `font_set: International`，自带中文
   （霞鹜文楷）：`makepad_widgets:resources/LXGWWenKaiRegular.ttf`。
   这条在 `v0.3.1` 上被踩过一次：为过门禁把字体换成**包内**子集，
   门禁过了、运行时却读不到（`font_src` 走 `crate_resource(<font_src>)`，
   只认编译进二进制的 crate 资源）⇒ 汉字全变方块。`v0.3.2` 的解法是把内置
   字体写成 **token**、组件用 `{"$token": …}` 对象引用（门禁只把字符串当引用），
   两条规则同时满足、**包里不带字体文件**。落点 `build/builtin_font.py`。

另外三个已踩的坑：

- **组件名不能撞 L0 内置角色名。** `Band` 是角色名，用它会报
  `Band has no argument "instance"`。已改名 `Slab`。
- **`when x == false` 会被拒**（l0.md：guard 只比较已声明的名字与值），
  bool 只用于"只有真值需要渲染"的场合；多态一律用 enum + `when x == .value`。
- **文本换行靠 `variant: "multiline"`**；`single_line` 不换行，超宽直接截断。

### 两条 2026-09-26 才敢下的结论

**① Kit 节点不能声明事件 —— 所以屏必须分开，由 Agent 推。**
`kit_pack::visit` 只接受 `component` / `instance` / `part`，加已声明的 props、
layout、style；多传一个 `on_tap` 会直接报 `xxx has no prop on_tap`。
也就是说**卡片自己跳不到下一屏**。于是每屏按钮的含义写在它旁边的
`service-actions.json`（`控件名 → 事件名`），由 Agent 读、由 Agent 决定下一屏 ——
官方 `aircon` 的 12 屏正好是这个形状。**"哪一屏"是 Agent 的判断，不是卡内的状态机。**

**② 画布尺寸 = 宿主窗口尺寸，不是猜的。**
`card-host` 硬编码 `window.inner_size: vec2(412, 892)`，五屏的 `page` placement
就是 `412×892`。抓到的图是 `515×1073`，那是 **125% DPI**（412×1.25=515），
裁掉宿主自绘标题栏（42 物理像素）后与画布正好成 1.25 倍关系：
`物理 = 逻辑 × 1.25 - 42`。按这个反推排版才准。

### 三条 2026-09-27 做端到端验证时才踩到的坑

- **`--allow-unsigned` 不能漏。** 宿主默认 `require_signature`，漏了就 `refused: … is unsigned`，
  表现为"窗口起来了但一直是空白"——很容易误判成"隐藏窗口不绘制"。看宿主日志一眼就能认出来。
- **抓图必须"等稳定帧"。** 宿主刚起时先给一帧空白（**5440 字节**，只有窗口底色+标题栏），
  所以"抓到 PNG 就算数"或阈值取 5 KB 都会假成功。判定 = 字节数 ≥ 20 KB **且**连续两次 sha 相同
  （真卡 49–77 KB）。
- **`MAKEPAD_HIDE_WINDOWS=1` 在这个 Windows 后端下不绘制**（本机实测：始终只有那帧 5440 空白）。
  自动化要抓图就用**可见窗口**；窗口只在脚本运行期间存在，跑完即退。

## 8. 两条红线

- **no-facts**：一切事实（时间、地点、天气、班次、金额）必须**来自真实数据源并标注来源**；
  模型只负责**识别与组织**，不得编造状态或执行结果。
- **不可只交创意**：最终交付 = **可运行的小程序 + Apache-2.0 开源仓库**。

### 8.1 一次自我纠错（留档）

第 5 屏原来印的是「行程已排 / 日历已加 / 提醒已设」—— **三件一件也没真做**：
车次是演示样例，日历和提醒从没被写过。这违反上面第一条红线（把建议写成了完成），
也在官方的「结果核验」轴上站不住。现在改成：

```
写了记忆 · 去深圳默认早班，从家里出发     ← 真写了（本机记忆文件，可核验）
行程没动 · 周三那班只是方案里的样例        ← 明说没动
日历与提醒没动 · 没碰系统                  ← 明说没动
```

同时把「长期记忆」从代码里的三个常量换成了**真实的本地文件读写** —— 于是
"它记住了"这句话第一次有了可核验的落点。改法与理由见 `src/memory_store.py` 顶部。

## 9. 长期记忆存在哪

| 项 | 值 |
|---|---|
| 位置 | 仓库下 `.local-state/memory.json`（`.gitignore` 已排除，运行期生成） |
| 内容 | 偏好（`prefs`）/ 各地点学到的默认（`places`）/ 每次写入的流水（`log`） |
| 权限 | 三条 host service（`matrix.send_message` / `octos.session.open` / `octos.turn.start`）；**不声明 `net`，不联网**、不读系统日历、不碰任何其他应用；存储用默认配额 |
| 首次运行 | 文件不存在 → 用内建初始值播种，并如实标注 `seeded_from: "builtin_initial"` |
| 可核验 | 打开就是个 JSON；`python build/verify_flow.py` 会断言它被真写、且不会被误写 |

## 作者与支持

| 项 | 值 |
|---|---|
| 作者 / 发布者 | **sansanyixyz331**（队伍 `三三Claw`） |
| 支持 | <https://github.com/sansanyixyz331/shiyi/issues> |
| 仓库 | <https://github.com/sansanyixyz331/shiyi> |
| 版本 | `0.3.3`（tag `v0.3.3`；`v0.3.2` 为初赛冻结版，`v0.3.1` 更早） |
| 许可 | Apache-2.0 |

## License

Apache-2.0 © 2026 sansanyixyz331
