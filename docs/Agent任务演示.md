# Agent 任务演示 · 拾意 Pickup

> 官方《作品提交与 App Hub》第 5 项要求：**输入是什么、Agent 实际完成哪些步骤、
> 如何核验结果、哪些环节需要人工确认**。本文件按这四问逐条写清，
> 每一步都对应到仓库里的真实代码与运行证据，**不含设计稿式描述**。

---

## 1. 输入是什么

一条**已经存在的消息**（聊天消息；桌面端场景素材为邮件原文）—— 不是用户对着 AI 下的指令，也不是表单填写。

**两个形态取的输入是同一类东西，进入方式不同**：卡片包形态是**一条消息进五屏**（下表三件字段）；**脚本应用（主提交）** 是**从绑定房间里读出来、你点其中一条**（见 §2.2）。

| 字段 | 来源（代码里的 `from`） | 例子 |
|---|---|---|
| 消息正文 | `message_text` | `下周三我得去趟深圳` |
| 房间/发信人 | `message_meta` | `家庭群` |
| 收到时刻 | `system_clock` | `2026-09-24 21:14` |

`src/intent_card.py` 把这三样组织成一张卡的语义结构（`build_card()`），
**每个对外可见的事实都带 `facts[].from` 标明出处**（`message_text` / `message_meta` /
`system_clock` / `rules(…)`）。这是 no-facts 纪律的代码级落实。

## 2. Agent 实际完成哪些步骤

本作品有**两个形态**，Agent 的步骤不一样 —— 先看**卡片包形态（L0 · 五屏）**（§2.1），再看**复赛主提交的脚本应用**（§2.2）。

### 2.1 卡片包形态（L0 · 五屏）

五步推进，**屏由 Agent 推、卡片自己不跳**（Kit 节点不能声明事件——见 `README.md` §11 附录·结论①）。
每步的语义：

| 步 | 屏 | Agent 这一步在干什么 | 依据代码 |
|---|---|---|---|
| 一 | `shiyi-01-read` 识别 | 从消息里抽出**时间 / 地点 / 类型**三类信号，逐条标「出自原文」或「识别所得」；命中长期偏好时同时给出「命中哪条」 | `_parse_when` / `_parse_where` / `_parse_intent` / `_memory_applies` |
| 二 | `shiyi-02-ask` 追问 | **只问消息永远说不出来的两样**（几点走 / 从哪出发）；基础信息真缺了才回头问 | `_frame_ask` |
| 三 | `shiyi-03-plan` 方案 | 把命中的老规矩摆出来，给一版**被它筛过**的候选（"只查了高铁，因为你坐高铁不坐飞机"） | `_frame_plan` |
| 四 | `shiyi-04-memo` 记忆 | 摊开「原来记着的」vs「这次要加的」（"原来"取自**真实记忆文件**，不是常量），**都可读可改**；点「记下」**真写盘** | `_frame_memo` / `memory_store.apply_keep` |
| 五 | `shiyi-05-done` 回执 | 三行回执，**分「真做了」与「没动」**：① 本机记忆真被写（写的是哪个文件的哪一项）② 行程没动 ③ 日历与提醒没动 —— 不摆"已完成"的样子，无积分无徽章 | `_frame_done` |

**关键的机制事实**：每屏按钮的含义写在它旁边的 `service-actions.json`
（`控件名 → 事件名`），Agent 读它来决定下一屏。共 **5 屏 / 14 个控件 / 14 个事件**：

| 屏 | 控件 → 事件 |
|---|---|
| read | `action_yes`→`intent.confirmed`；`action_fix`→`intent.corrected` |
| ask | `opt_a1`→`ask.when.morning`；`opt_a2`→`ask.when.afternoon`；`opt_b1`→`ask.from.home`；`opt_b2`→`ask.from.work`；`action_go`→`ask.settled`；`action_later`→`ask.deferred` |
| plan | `action_take`→`plan.take_recommended`；`action_other`→`plan.another_round` |
| memo | `action_keep`→`memo.keep`；`action_skip`→`memo.skip` |
| done | `action_open`→`trip.open`；`action_again`→`app.restart` |

`src/shiyi_flow.py` 不硬编码这些事件名，而是**直接读每屏的 `service-actions.json`**
（`load_controls()`）——改了卡，流程跟着变，不会对不上号。

### 2.2 主提交形态：脚本应用（`shiyi-live` · 一卡直出）

**这才是复赛提交的那一个**（根 `bundle/main.splash`，`version: 0.8.6`）。
**桌面端（Windows 官方参考宿主）与手机端（小米13 · Rinx）走的是同一条路径** —— 同一份脚本、同一串宿主调用。

**一次任务，Agent 干什么：**

| 步 | Agent 这一步在干什么 | 依据代码 |
|---|---|---|
| ① 读 | 读**你导入时绑定的那个房间**最近的消息（`matrix.read_messages`，取 10 条）；同时读 `octos.session.history`（助手会话进记忆盒）、`matrix.profile`（认出哪条是**你自己说的**，标「（你）」） | `chat_fetch()` / `ahist_fetch()` / `profile_fetch()` |
| ② 选 | **你点其中一条** —— 它就是这一轮的输入（不是下指令、不是填表） | `use_one()` |
| ③ 认 + 决策 | 助手当**决策核心**（`model.complete`）：出**人话标题**、判**要不要提醒 / 提前多久**、写**提醒话术**、给**依据**；同时用本机记忆判「命中哪条老规矩」 | `ask_model()` / `model_task()` / `model_schema()` / `mem_hints()` |
| ④ 确认 | 卡上**等你点头**，你点确认才往下走 | — |
| ⑤ 办 + 记 | 写回本机记忆（`memory.json`：偏好 / 常去的地方 / 卡片流水），并把结论**真发回群** —— 「记下了」→「办成了」 | `mem_write()` / `send_back()` / `confirm()` |
| ⑥ 降级 | 助手不可用 ⇒ **退到「本机规则」**：仍判类型与时间、卡照出、事照记，只在卡上**如实标注**「识别来源 · 本地规则」 | `ask_model()` 的 `host.has("model")` 分支 |

**与 §2.1 的区别（一句话）**：五屏那条是"**一张一张卡往下推**"；脚本应用是"**一卡直出**" —— 一条消息进去，一张卡当场长出来，确认即办。**两条都是本作品，形态不同。**

**真机实测（同一条路径，两个端都跑通）：**

| 端 | 宿主 | 实测链 |
|---|---|---|
| **桌面** | Windows · 官方参考宿主（OctoSense 宿主） | 读房间 → 点一条 → 造卡 → 确认 → **群里真多一条回执**（记忆 0→1） |
| **手机** | 小米13 · **Rinx**（内置 OctoSense 内核） | 读群 → 点一条 → **AI 出卡**（卡上标「识别来源 · 设备助手」）→ 确认 → 「**已把结果发回群**」 |

证据：`docs/evidence/act/`（Rinx 真机全链 · 27s 连续录屏 + 5 张截图）、`docs/evidence/chat-read/`（读房间 → 造卡 → 确认 → 记忆 5 卡）、`docs/evidence/phone-live-20261011/`（手机整链截图 + 内核日志原文：`calling LLM` → `LLM response received`）。

## 3. 如何核验结果

核验分两层：**逻辑层**（Python 自测）与**运行时层**（官方参考宿主里真跑）。

### 3.1 运行时层（最有说服力，官方要的"实际运行证据"）

`build/verify_flow.py` 在**官方参考宿主 `card-host`** 里跑完整链路，每一步都出可核对的数字：

```
一条消息 → 起宿主挂卡 → 等稳定帧 → 抓图
        → /snap 证实目标控件「在 / 可见 / 可点」三项全 true
        → /click 打到该控件矩形中心 → 宿主应答 {"ok":1,"f":N}
        → 读该屏 service-actions.json 里声明的事件名 → 推下一屏 → …
```

实测（`build/_evidence/flow_run.json` 逐条留痕）：

| 屏 | 渲染字节 | 点中控件 | 控件矩形 | 宿主应答 | 事件 → 下一屏 |
|---|---|---|---|---|---|
| 1 read | 76739 | `action_yes` | [24,800,364,54] | ok | `intent.confirmed` → ask |
| 2 ask | 56022 | `opt_a1`/`opt_b1`/`action_go` | … | ok | → plan |
| 3 plan | 66127 | `action_take` | [24,800,364,54] | `{"ok":1,"f":20}` | `plan.take_recommended` → memo |
| 4 memo | 50954 | `action_keep` | [24,800,364,54] | `{"ok":1,"f":22}` | `memo.keep` → done |
| 5 done | 55843 | `action_open` | [24,800,364,54] | `{"ok":1,"f":23}` | `trip.open` →（终点） |

**判真的三个要点**（都是踩过坑才定的）：
- **五屏字节各不相同**（49–77 KB）→ 证明每屏是**真的不同画面**，不是同一张被复制。
- **"控件在/可点/点得中"三项全 true** → 证明点击**真打在真控件上**，不是坐标空点。
- **事件链完整推进**（`intent.confirmed → … → trip.open`）→ 证明**流程真的走完了**。

**主提交形态（脚本应用）的运行时证据**（真机实测，桌面 + 手机同路径）：
`docs/evidence/act/`（Rinx 真机，27s 连续录屏：读房间 → 造卡 → 确认 → 群里真多一条回执）、
`docs/evidence/chat-read/`（读房间 → 造卡 → 确认 → 记忆）、
`docs/evidence/phone-live-20261011/`（手机整链 5 图 + 内核日志：`calling LLM` → `LLM response received`）。

### 3.2 逻辑层

```sh
python src/shiyi_flow.py    # 走完五屏，打印每屏内容与走过的决定
python src/intent_card.py   # 三条样例消息的识别结果 + 事实来源
```

### 3.3 门禁层

```sh
"$HUB_BIN" check "$APP_REPO/bundle" --allow-unsigned   # → PASSED
"$HUB_BIN" scan  "$APP_REPO/bundle" --packet "$APP_REPO/build/review.json"
```
官方明示：**预检不覆盖真实交互**，所以第 3.1 层的冒烟不可省。

### 3.4 记忆层（长期记忆真的写了吗）

"它记住了"这句话，作品得拿得出东西来核。`build/verify_flow.py` 同一次运行里
对**长期记忆**做三条断言（全部记进 `flow_run.json` 的 `memory` 段）：

| 断言 | 做法 | 实测结果 |
|---|---|---|
| `keep_wrote_file` | 点「记下」 | 本机 `.local-state/memory.json` 真被写：`places.深圳 = {默认早班, 从家里出发, 来源消息, 时间戳}` ✓ |
| `memory_is_effective` | 再跑一遍 | 进记忆屏时读到的是**上一遍写进去的那条**，不是代码常量 ✓ |
| `skip_left_file_untouched` | 点「这次别记」 | 文件 sha 前后一致（一个字节没动）✓ |

记忆的写入完全来自：① 用户消息原文，② 用户在追问屏按下的选项 —— 没有一条是推断的，
每条都带 `learned_from`（哪条消息教它的）。存储位置与权限见 `docs/数据来源与限制.md` §5.4。

## 4. 哪些环节需要人工确认

**每一屏都是一张"等你点头的卡片"，没有一个环节自动往下走。**

| 环节 | 人要做的事 | 不做会怎样 |
|---|---|---|
| 识别后 | 点「对，就是这件事」或「不对，改一下」 | 不点 → 停在识别屏（`intent.corrected` 则回重读） |
| 追问中 | 选「几点走」「从哪出发」 | 不答 → `ask.deferred` 挂起，等人回来 |
| 方案前 | 点「就要第一班」或「换一版看看」 | 不点 → 停方案屏（换一版则重排） |
| 记忆前 | 点「记下」或「这次别记」 | 不选 → 停在记忆屏；`memo.skip` 则不写但流程照走 |
| 回执后 | 点「看行程」或「重开一条」 | 不点 → 停回执屏 |

**脚本应用（主提交）同理**：房间是它自己读的，但**造出来的卡必须你点确认，才写记忆、才发回群** —— 没有"自动替你办事"那一步（`confirm()`）。

**拿不准就不猜**：`intent_card.py` 里低置信字段（`confidence` 低 / `needs_user=true`）
一律交回给人确认（如指代词「那个」直接出追问），而不是编一个看起来像样的答案。

## 5. Agent 的边界（一句话）

**Agent 只做识别、组织与推进；事实来自消息原文与本地规则；执行前必过用户。**
不编造执行结果、不编造服务状态、不把"建议"写成"已完成"——这三条是硬约束
（`AGENTS.md` 与 `README.md` §11 均列为红线）。
