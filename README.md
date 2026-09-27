# 拾意 · Pickup

> **从你的聊天里，读出你没说出口的安排。**
> *Reads the plan you never said out loud, from the messages you already sent.*

GOSIM **Agentic App 黑客松 2026「意图即应用」** 参赛作品（应用层 / Nautilus 路径）。

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
    manifest.json        # 应用身份 / 版本 / 完整性与能力声明
    listing.json         # 商店条目：描述 / 分类 / 截图 / 图标 / 许可
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
  docs/
    作品设计_拾意.md      # 选题 / 流程 / 数据来源 / no-facts 声明
    小程序机制笔记.md      # Hub app / Card bundle / Image-to-AppCard 机制
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
| 5 完成 | `cards/shiyi-05-done` | 回执三行（写到哪就说哪），无积分无徽章 → 看行程 / 重开 |

## 5. 怎么跑（官方参考宿主）

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

# 2. 门禁自检（未签名告警属开发期正常——官方原话）
"$HUB_BIN" check "$APP_REPO/bundle" --allow-unsigned

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

**演示短片（A4）**：

```sh
python build/record_demo.py                 # 录五屏正流程 → build/_video/shiyi-walkthrough.mp4
python build/record_demo.py --from-frames   # 只重编码，不重录
python build/record_demo.py --no-caption    # 不要字幕
```

跑的是上面同一条链路，区别只在**一边跑一边逐帧录宿主窗口本身**（宿主自带的
`/g?raw=1`，10 fps），再用 ffmpeg 合成 mp4。字幕用的全是卡内真实文案，并且先在
底部 pad 出一条字幕带再画进去 —— 不遮卡片、不盖按钮。

成片：`build/_video/shiyi-walkthrough.mp4`（约 15.6 秒 / 156 帧 / 146 KB）。
说明：这是**桌面官方参考宿主**里的真实运行录制；手机端要等官方"支持设备／运行包"
公布（官方那条 HTTP 自动化通道在 Android 上被编译掉了，手机端另有真机触摸注入
的一套，是几小时级的活）。

## 6. 当前状态

| 项 | 状态 |
|---|---|
| 选题与设计 | ✅ 已定（见 `docs/作品设计_拾意.md`） |
| 仓库骨架 | ✅ 已搭 |
| 卡片本体 | ✅ **五屏全部手写 L0，逐屏实跑渲染** |
| kit 组件包 | ✅ 五屏共用 `bundle/kit/native/light/kit.json`（16 组件 + 12 token） |
| 卡外动作 | ✅ 每屏 `service-actions.json`（12 个控件 / 12 个事件，与流程同源） |
| 宿主运行 | ✅ `card-host` 逐屏跑通（五屏 `[SPLASH] … view=true`，零 lower 错误） |
| 真实截图 | ✅ 五张 `515×1073`（实拍后裁掉宿主标题栏，入 bundle 与各屏目录） |
| 门禁 | ✅ `hub check` **PASSED**（唯一告警 = 未签名，开发期正常） |
| 审查包 | ✅ `build/review.json`（7 个审查问题，放 bundle 之外） |
| 服务逻辑 | ✅ 五屏流程状态机（`src/shiyi_flow.py`）**已与官方参考宿主串成端到端** |
| 端到端验证（A3） | ✅ `build/verify_flow.py`：五屏逐屏真渲染 + 每步真实点击命中控件 + 事件链推进 → `build/_evidence/` |
| 失败态取证（B4） | ✅ 未签名 / 摘要不符 → 宿主拒绝且**零渲染**（fail-closed），日志与抓图留证 |
| 演示短片（A4） | ✅ `build/_video/shiyi-walkthrough.mp4`（15.6 秒 / 156 帧，**真实宿主逐帧录制，非动画**） |
| 签名 / 提交 | ⬜ 待做（需发布者密钥） |

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

## License

Apache-2.0 © 2026 sansanyixyz331
