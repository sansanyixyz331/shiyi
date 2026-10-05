# 拾意 · 现场造卡（shiyi-live）0.7.1

**一个能用的应用**：输入一句话，它在**本机**识别出时间/地点/类型，**现场长出一张卡**，
并把确认过的卡与你的习惯**记住**（长期记忆）。不依赖任何服务，离线也完整可用。

- 形态：**脚本应用**（`main.splash`，OctoScript）—— 有逻辑、能交互（输入框 / 按钮 / 动态渲染 / 定时器 / 文件读写）
- 宿主：**Rinx 真机已跑通**（导入 → Run → 说习惯 → 确认 → 记忆更新 → 造出行卡带记忆行 → 再确认；
  证据 `docs/evidence/live-app/` 与 `build/_gen_video/live-app-in-rinx.mp4`），官方参考宿主 `card-host` 也跑得通
- 识别口径：与生成器同一套（强信号优先：提醒 / 买 → 寄取 → 见碰 → 去飞）
- **按场景长不同的卡**：出行 / 会面 / 代办 / 采买 / 提醒 —— 题头、行标签、动作各不同
- **长期记忆**（见下）：与生成器**同一套 schema**
- **时间给真日期**：`下周三` → `下周三 · 10月14日`，`周末` → `这个周末 · 10月10日`
- **三种状态**：造卡 →（改一下｜确认）→ ✓ 已记下 + 再来一张
- 整页可滚动（`ScrollYView`）；卡片高到按钮出画时，滚一下就到（真机实测过）

## 长期记忆（`memory.json`）

存在应用自己的 jail 里 —— `card-host` 是 `<app-data>/shiyi-live/`，Rinx 是
`<rinx-data>/miniapps/<账号>/shiyi-live/`。**schema 与生成器那份完全一致**：

```json
{"version":1, "updated_at":"2026-10-05 04:28", "seeded_from":"shiyi-live",
 "prefs":{"no_flight":true, "prefers_rail":true, "no_wednesday_pm":true},
 "places":{"深圳":{"seen":1, "at":"…", "last_kind":"trip", "default_depart":"早班", "from":"家里"}},
 "log":[{"at":"…","kind":"trip","text":"下周三我得去趟深圳","when":"下周三 · 10月14日","where":"深圳","confirmed":true}]}
```

**记忆用在三处**：
1. **卡上给出「记忆行」**（这才叫"知道用户喜好"）：
   - `记忆 · 你不坐飞机 → 这次只给高铁`
   - `记忆 · 深圳 通常早班`
   - `⚠ 记忆里说「周三下午别安排」→ 这次要不要改天？`（**冲突提醒**——记忆唯一能主动纠正你的地方）
2. **确认 = 记住**：写 `log` 一条、把地方记进 `places`（**保留原有 `default_depart`/`from` 等字段，不覆盖掉**）、
   从原文里学几条明确的偏好（`不坐飞机` / `高铁` / `周三下午别安排` —— 只认这几种，不猜）
3. **`mem_brief()`**：把记忆拼成一段话。**接上设备助手时，这段就是随用户那句话一起发给模型的上下文**
   —— 现在还没接，但接口留给它了

**要用它，清单里必须声明 `storage`**（`capabilities: ["storage"]` + `storage.max_bytes`）。
不声明也**可能**能写（宿主给了 jail 就行），但隐私摘要来自这个声明，所以照实声明。

**想让它读生成器那份记忆**：把仓库的 `.local-state/memory.json` 拷进 jail 即可（实测能直接读，
界面会显示 `你：偏好高铁 · 不坐飞机 · 周三下午别安排` 与 `常去：深圳 · 通常早班`）。
反过来，app 写出来的文件生成器也读得懂（同 schema）。

**验持久化**：造卡 → 确认 → 关掉应用 → 再打开。记忆条里的张数、偏好、常去都还在（这就是"长期"）。

## ⚠️ 盖章必须用「与运行宿主同平台」的 hub（2026-10-05 实测踩到）

这个 bundle 的**摘要是分平台的**（官方 #75：`digest_dir` 把相对路径也一起哈希 —— Windows 算 `\`、
Linux 算 `/`）。而**这个应用跑在 Windows 的 Rinx / card-host 上** ⇒ **必须用 Windows 的 hub 盖章**：

```bash
hub.exe stamp apps/shiyi-live/bundle     # ← 本应用用 Windows 的 hub
```

**实测**：Linux hub 盖出 `3292adc8…`，而 Windows card-host 自己算出 `1eb813d4…` ⇒ **当场被拒**；
被拒时宿主只画一张失败卡（`card-host refused this bundle / bundle digest … does not match`）。
换 Windows hub 盖章后才 `admitted`：

```
card-host: shiyi-live 0.5.0 admitted — capabilities {"model","storage"}, storage 262144 bytes
```

> ⚠️ **别把「平台差异」误诊成「忘盖章」（我本人踩过，已做决定性实验定案）**：
> 拿 **Linux hub 去 check 一个 Windows 盖章的包**，它**永远**报 digest 不一致 —— 这**不是**包坏了。
> 判据：**先确认「盖章用的 hub 平台 == 运行宿主的平台」，再谈摘要对不对。**
> 定案实验：取**改动前**的包内容 + **Windows** hub 重算 → 得到的正好是清单里原本那个值
> ⇒ **原来的章是对的**，之前的"不一致"纯粹是拿 Linux 看 Windows 的包。
>
> 注意与 `bundle/`（初赛提交物）**相反**：那是交到 **Linux** 评测的，所以**留 Linux digest**。
> 一句话：**谁运行它，就用谁的 hub 盖章。**
>
> 补充实测：Windows 的 `hub check` 目前**本身还跑不通**（同一个 #75 的路径 bug，
> 报 `not a portable bundle path: "assets\icon.svg"`）⇒ Windows 侧只能用 `stamp`，
> 验收靠宿主日志里的 `admitted` 或抓帧。修这个 bug 的 PR 就是本队的 `#79`。

## 跑

```bash
# 官方参考宿主
card-host --bundle apps/shiyi-live/bundle --app-data <tmp> --allow-unsigned --remote 8977
# 抓帧： curl "http://127.0.0.1:8977/g?raw=1" -o frame.png

# Rinx 真机：Mini apps → 导入应用 → 填 bundle 绝对路径 → Review bundle → Run
```

## 录

```bash
# 宿主内逐帧录制（真渲染帧）
python build/record_live_app.py <已打好摘要的 bundle> build/_gen_video/live-app.mp4

# 真机（Rinx 窗口）驱动 + 录制：点例子胶囊、定位主按钮、抓每一帧
python build/record_rinx_app.py build/_gen_video/live-app-in-rinx.mp4
```

`record_live_app.py` 自己会把启动行换成自动轮换版
（`start_timeout(1.0, || cycle())` + `start_interval(3.0, || cycle())`，五条样例轮流）。
`record_rinx_app.py` 里胶囊坐标是**量出来的**，主按钮是**按颜色现场找的**——因为卡片高度随内容变
（出行卡有时间+地点两行，代办卡只有一行），写死 y 会点空。

## 改完必须重盖摘要

**改 `main.splash` 后一定要 `hub stamp`**，否则宿主直接拒：

```
card-host refused this bundle
bundle digest <新的> does not match the manifest's <旧的>
```

`card-host` 和 **Rinx 都校验摘要**。这个坑连踩两次（一次在 Rinx 导入、一次在录制），
现在 `build/shot_bundle.py` / `record_*` 前都会先盖。

## 接 AI：`model.complete`（**已实现、本地三态验证过；出厂关 —— 原因见下方 0.7.1 实测**）

按官方 `AI-SERVICES.md` 的契约写好了整条路，但**默认不启用** —— 现在不会把用户的话发给任何助手。

```splash
host.request("model.complete", {
    task:   model_task()                       // 要它干什么
    input:  {text: t memory: mem_brief()}      // ← 用户那句话 + 长期记忆，都在这里
    schema: model_schema()                     // 必须过 JSON Schema，回复才被接受
    class:  "fast"
}, fn(r){
    if r.is_ok { apply_model_output(r.data.output, t) }   // r.data.output
    else       { identify_rules(t) }                       // 回退本机规则
})
```

**两个开关都在 `main.splash` 顶部**：

| 开关 | 现在 | 复赛怎么做 |
|---|---|---|
| `ASK_MODEL` | **`false`** —— 一律走本机规则（`model.complete` 在 Rinx 上必被拒，且顶栏会常驻一条提示 ⇒ 出厂关） | 在**提供 `model` 服务的宿主**（OctoSense shell）上改成 `true`，就会真的调设备助手 |
| `MODEL_STANDIN` | `false` —— 开发期替身 | 保持 `false`。仅在本地验证用：从 jail 的 `model-stub.json` 读一条回复，走**同一条**「回复 → 卡」解析路径 |

**未启用时卡上照旧**写 `识别来源 · 本机规则（不依赖任何服务）`；启用后如实标注走了哪条：
`设备助手（长期记忆已带上）` / `本机规则（设备助手不可用）` / `设备助手（本地替身…）`。
**官方要求"不可用时应用也要完整可用"，所以任何 `r.is_ok == false` 都回退，不重试、不挡路。**

### 本地验过的三种状态（都出图了）

| 状态 | 怎么跑 | 结果 |
|---|---|---|
| **默认** | `ASK_MODEL=false` | 与 0.4.0 完全一致：`本机规则（不依赖任何服务）` |
| **真回退** | `ASK_MODEL=true`，`card-host`（**没有 model 服务**） | 卡照出，来源写 `本机规则（设备助手不可用）` |
| **走模型** | 再加 `MODEL_STANDIN=true` + `model-stub.json` | 卡按**回复**长：`目的地 · 慕尼黑`（规则认不出这个城市） |

证据在 `docs/evidence/model-path/`：`fallback-in-card-host.png`、`model-standin-in-card-host.png`、
`payload-sent-to-model.json`。

**那第三张图里最值钱的是 `payload-sent-to-model.json`** —— 替身会把「本该发出去的载荷」也落盘，
所以能直接看到**长期记忆确实进了 `input`**：

```json
{"task":"把用户这句话里的事，识别成一张卡需要的四个字段。…",
 "input":{"text":"下个月初得去趟慕尼黑看展会",
          "memory":"用户长期记忆：偏好：坐高铁、不坐飞机、周三下午别安排。常去 深圳 · 通常早班。"},
 "class":"fast"}
```

**复赛出厂态（0.7.1）**：`READ_CHAT = true`、`READ_ASSIST_HISTORY = true`（两条**真能跑通**的总线读），`ASK_MODEL = false`（Rinx 不提供）。要接模型再加 `model`：把 `ASK_MODEL` 改 `true` ⇒ ② `hub stamp`
③ 在宿主里配好 AI provider
（OctoSense Shells 的 `model` 服务从**用户自己的** provider 回答；应用永远看不到 provider / model id / key）
④ 重跑门禁确认 `grants: capabilities {"model", "octos.session.history", "matrix.read_messages", …}`。
⚠️ 声明 `model` 会让商店多一条权限说明（"把你给它的内容发给你配置的 AI provider"）；
**如果不打算启用，就从 `capabilities` 里去掉 `model`**。
⚠️ 预算由宿主管：默认 6 次/分钟、100 次/天、10 万 token/天 —— 所以**别每敲一个字就问一次**。

## 读设备助手的会话记忆：`octos.session.history`（**已实现，默认关；复赛开**）

这是**第二个「长期记忆」来源**。本机记住的是**你造的卡**；助手那边记住的是**你在对话里说过的**
—— 两个合起来，才叫真知道你是谁。全场只有 2 队声明了这条能力（`00_docs\对手赛情侦察_20261005.md`）。

**官方契约**（`AI-SERVICES.md` § The assistant capabilities）：capability 就是同名的 `octos.session.history`；
`octos.session.history` 调一次、args `{}`，返回 `{session_id, messages:[…]}` —— **两条车道（person /
system_agent）按时间合并**，每条带 `lane` 与 `speaker`。官方原话：**"脚本 app 靠它读会话（含系统 agent 的轮次）"**。
脚本 app **不许用 `bindings.json`**，只能直接 `host.request`（`HOST-SERVICES.md`）。

```splash
host.request("octos.session.history", {}, fn(r){
    if r.is_ok { ahist_ingest(r.data) }        // 嚼成展示行，并喂给 mem_brief()
    else       { ahist_state = "这次读不到" }   // 官方要求：不可用也要完整可用 ⇒ 只写一行，不挡路
})
```

读到的会话进两处：**记忆盒子上多一行「助手记忆 · 读到 N 条会话」**（取最近 3 条，`你：` / `助手：` 分标），
以及 **`mem_brief()`** —— 真接上模型时，它和本机记忆一起进 `input.memory`。

**开关**（`main.splash` 顶部，默认都关）：

| 开关 | 现在 | 复赛怎么做 |
|---|---|---|
| `READ_ASSIST_HISTORY` | **`true`（0.7.1 起）** —— 开屏就读设备助手会话 | 保持 `true` |
| `HIST_STANDIN` | `false` —— 开发期替身 | 保持 `false`。本地验用：从 jail 的 `history-stub.json` 读一段会话，走**同一条**解析路径 |

> 解析一律**枚举**（`for fk fv in m`）、不点缺失的键（缺字段在 splash 里是**报错不是 nil**）；
> 截断用 `match_str(regex("^.{0,26}"))`（splash **没有 slice**）。

### 本地验过的四种状态（都出图了，`docs/evidence/assist-memory/`）

| 状态 | 怎么跑 | 结果 |
|---|---|---|
| **默认**（回归） | 两个开关 false | 与 0.5.0 逐像素一致：无助手记忆行（`00-default-unchanged.png`） |
| **替身** | `READ_ASSIST_HISTORY=true` + `HIST_STANDIN=true` + `history-stub.json` | `助手记忆 · 读到 4 条会话` + `助手：…/ 你：…/ 助手：…`（`01-assist-memory-4-rows.png`） |
| **真回退** | `READ_ASSIST_HISTORY=true`，card-host（**没有 octos 服务**） | 照常渲染，出现 `助手记忆 · 这次读不到`（`02-assist-memory-unavailable.png`） |
| **模型回退** | `ASK_MODEL=true` + 真造一张卡 | 卡照出，底部如实写 `识别来源 · 本机规则（设备助手不可用）`（`03-model-fallback-with-card.png`） |
| **真机（Rinx）** | `READ_ASSIST_HISTORY=true`，真宿主 + 真助手（`primary: ready`） | Review 认下 3 条服务（`storage, model, octos.session.history`）；Run 后出现 `助手记忆 · 助手会话是空的` —— **真服务答了**（`04-rinx-real-service.png`） |

五种状态 card-host 侧全部 `admitted`、**运行期 0 错误**；真机 Rinx 侧跑通且本机记忆跨导入仍在。

## 从绑定房间里读消息：`matrix.read_messages`（**0.7.0 新增；0.7.1 起默认开**）

这是**「读消息」这条能力**—— 前面两个来源（本机卡的记忆、助手的会话）都不含"群里刚说了什么"。
官方 12 场景里「即时消息 / 日历」要落地，第一步就得**能读到消息**。全场只有 3 队声明了它（`00_docs\对手赛情侦察_20261005.md`）。

**官方契约**（源码为准，`Rinx/src/host/matrix/mod.rs:545` + `crates/miniapp-core/src/matrix.rs:209`）：

- 服务名 `matrix.read_messages`；args `{room_id, limit}`（`limit` 会被 clamp 到 **1..30**，默认 10）；
- ⚠️ **需 app 在导入时绑定一个房间** —— `parse()` 明写：非 `room_free` 的服务、没绑房间 ⇒
  `this mini-app is not attached to a room`。导入表单的 **`Room ID to allow (optional)`** 那一栏就是它；
- 返回 `{"messages":[…], "unread_count":N}`，每条含 `sender / sender_id / event_id / body / ts / msgtype / room_id / unread`，**旧→新**排列。

脚本 app **不许用 `bindings.json`**，只能直接 `host.request`：

```splash
host.request("matrix.read_messages", {limit: 10}, fn(r){
    if r.is_ok { chat_ingest(r.data) }         // 嚼成可点的消息行
    else       { chat_state = "这次读不到" }    // 不可用也要完整可用 ⇒ 只写一行，不挡路
})
```

**闭环**（这才是评委「任务验证」要的那个）：**读到消息 → 点一条 → 它变成输入 → 现场造卡 → 确认 → 写回记忆**。
每条消息行是一个 `Msg` 按钮，`on_click` 直接 `use_one(chat_texts[i])`。

**开关**（`main.splash` 顶部，默认都关）：

| 开关 | 现在 | 复赛怎么做 |
|---|---|---|
| `READ_CHAT` | **`true`（0.7.1 起）** —— 开屏就读绑定房间的最近消息；宿主没这服务或没绑房间 ⇒ 只写一行 | 保持 `true` |
| `CHAT_STANDIN` | `false` —— 开发期替身 | 保持 `false`。本地验用：从 jail 的 `chat-stub.json` 读一段消息，走**同一条**解析路径 |

### 验过的状态（都出图了）

**card-host 三态**（`docs/evidence/chat-read/cardhost/`）：默认（与 0.6.0 一致、无聊天盒）／替身
（`从聊天拾意 · 读到 3 条消息` + 三条可点行）／无服务（`从聊天拾意` + `这次读不到`）—— 三态全部
`admitted`、**运行期 0 错误**。

**真机 Rinx 全链路**（`docs/evidence/chat-read/`，2026-10-05 · 0.7.1 出厂态）：

> 🎬 **演示片（27.5 秒）**：`docs/evidence/chat-read/demo-rinx-loop.mp4` —— 从 Mini apps → 导入（绑房间）
> → Review → Run → 读到 ×3 条 → 造卡 → 确认 → 记忆 4→5，一镜到底。

| 步骤 | 实据 |
|---|---|
| 导入 + Review | `拾意 · 现场造卡 0.7.1`；`Services: storage, model, octos.session.history, matrix.read_messages`；`Allowed room: !6OTF…` |
| Run | `从聊天拾意 · 读到 4 条消息`（真房间真消息）+ `助手记忆 · 助手会话是空的`（**octos 服务也真答了**）（`00-rinx-reads-room.png`） |
| 点一条 | 输入框出现那条消息原文（`01-picked-into-input.png`） |
| 造卡 | `出发 · 下周三 · 10月14日` + `记忆 · 你不坐飞机 → 这次只给高铁`（`02-card-built-from-message.png`） |
| 确认 | `记下了 —— 记忆已更新`（`03-confirmed.png`） |
| 写回 | `记住 4 张卡` → **`5 张卡`**；`深圳 去过 3 次` → **`4 次`**（`04-memory-5-cards.png`） |

### ⚠️ 为什么 `ASK_MODEL` 出厂是 `false`（0.7.1 实测定的）

拿 Rinx 跑通了才发现：**Rinx 把 `manifest.capabilities` 原样当成租约的服务集**（`src/miniapps/ui.rs:425`），
而模型这条**能力名是 `model`、服务名是 `model.complete`** ⇒ 调 `model.complete` **必被拒**：

```
Mini app was not granted model.complete
```

而且这句是宿主顶栏的**常驻**提示（`notice` 是持久 label）⇒ 演示时整场挂着一条"未授权"，看着像坏了。
官方 `AI-SERVICES.md` 写的是 **`model` 由 OctoSense shell 提供**（Rinx 未实现）⇒ 干脆默认关，
识别走本机规则（本来就不依赖服务）。**在真正提供 `model` 的宿主上，把它改 `true` 即可** —— 代码路径
（`ask_model` + schema + fail-closed 回退）已实现、本地三态验证过，见 §接 AI。

## 这个宿主版本支持什么（实测，别再凭猜）

**都支持**：`Inset{}` 形式的 `padding`、`spacing`、多层嵌套、`ScrollYView`、
`align: Align{x: 0.5 / 1.0}`、`flow: Flow.Right{wrap: true}`（窄了自动换行）、
`let Style = ButtonFlat{...}` 样式复用、`RoundedView{show_bg: true draw_bg.border_radius: …}`、
`theme.font_bold{font_size: …}`、`TextInput` 加 `draw_bg +: {border_color …}`、
`local_time()` / `time_now()`（`local_time` 字段可直接做日期运算）、
`on_render` 里的 `if` / `for`（写成 `if x.len()==0 {A}` 再 `for i in x.len() {B}`，不要 `else for`）。

**真的会踩的坑**：
- 注释只能 `//` 或 `/* */` —— `#` 是颜色记号，不是注释；写错会让初始化中断。
- **注释里别用 ASCII 双引号**（`// 这是"引号"`）。踩过一次：一次编辑把注释和下一行的 `fn` 并成了一行，
  函数被吞进注释、只剩一个孤立的 `}`，**整棵树渲染成纯白**，日志里却什么都没有。
  **改完数一遍括号**（`{` 与 `}` 的净差必须是 0）—— 这次就是靠"净差 -1"定位到的。
- 十六进制色必须 `#x` 开头（如 `#x0e1a16`），否则 tokenizer 把 `e` 当指数。
- **读一个不存在的字段是「报错」，不是 nil**（`property … not found in prototype chain`）。
  所以读记忆一律**枚举**（`for k v in obj { if k == "…" }`），**赋值可以创建**（`mem.prefs = {}` 没问题）。
- **`flow: Right` 不是"右对齐"**，它只是"横向排列"，默认从左边开始排。
  要右对齐得再加 `align: Align{x: 1.0}`（官方 app 用的是 `align: Align{y: 0.5}`，x 默认 0＝靠左）。
- **定宽列在窄屏会被裁**。原先用 `width: 720` 的"居中列"，在 515 宽的宿主上实测
  面板 **左边界=0、右边界=514（两边顶到边）** ⇒ 是被裁掉的，不是居中
  （判据：文字左对齐，右边被裁看不出来，所以一开始误判成"没裁"）。
  现在改成**全宽 + `padding: Inset{}`**（官方 app 的做法），窄屏安全、宽屏正常。
- 括号必须对齐。**曾有一次"只渲染出标题"**，当时误判为"宿主不吃 `Inset`/`spacing`"——
  逐项实测（探针 app）证明**都吃**，真因是那段布局**少了一个闭合括号**。
- 🚨 **在 `on_render` 里写 `else { if … {…} }`（嵌套 `if` 直接放进 `else` 块）会让整个渲染闭包抛栈错**：
  `[E] splash:... - pop_stack_resolved on empty stack` + `on_render closure failed; discarding its output`
  ⇒ **那一整块 on_render 的输出被丢弃**（实测：记忆盒整块消失，连"长期记忆"标题也没了），
  **而全局括号净差仍是 0 ⇒ 光数括号查不出来**。
  改法：**拆成两个独立的 `if`**（`if 条件A {…}` 再 `if 条件B {…}`）。
  ⚠️ **边界（实测）**：普通函数里的 `else { if … }`（如本文件的 `mem_hints`）**能跑** —— v0.5.0 真机出过图。
  所以**只有 `on_render` 内**这一处致命；但为省心，**一律拆开**。
  > 这条现在由 `preflight_shiyi.py`（技能 `scripts/`，已挂 pre-commit）**在提交前硬拦**：`on_render` 内的 `else { if` 直接 FAIL。

定位法：逐段加、每段渲染一次、看哪些元素还在；同时看 `[SPLASH] eval: N bytes` 与
行投影数出实际渲染了几行（别只信 OCR——淡色小字、深底浅字 OCR 会漏读或读错）。

## 清单侧的坑

- **`listing.json` 没有 `version` 字段**。多写一个，门禁直接拒：
  `listing is not valid: unknown field version, expected one of schema, subtitle, description, …`。
  版本只写在 `manifest.json` 里。
- 声明了 `storage` 之后，门禁会显示 `grants: capabilities {"storage"}, storage 262144 bytes` —— 这就对了。

## 已知边界

- 识别是本机**规则**（regex + 词表），不是模型。Rinx 真机现在自带"设备助手"
  （导入页可见 provider / Base URL / API Key 配置，`primary: ready`），
  接上它就能把规则换成模型，并把 `mem_brief()` 当上下文一起发过去——**那是下一步，不是现在**。
- 城市表是手写的 16 个；没认出来时卡面会明说"原文里没读到时间和地点"。
- 偏好只认几条明确说法（不坐飞机 / 高铁 / 周三下午别安排）。**不去猜**用户的隐含偏好。
- "确认"目前只写进**本应用的**记忆（不改系统日历、不建系统提醒）——要真写，
  得用宿主服务（`host.request`）而不是自己的 jail。
