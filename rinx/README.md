# rinx/ — 拾意在 Rinx 宿主里的「执行扩展」

这一目录**不进提交包**（它不在 `bundle/` 里）。它装的是：让「拾意」在宿主 **Rinx** 里
**把确认结果真正执行出去**所需的两份文件，以及**已在真机上跑通的实证**。

一句话：**提交用的 `bundle/` 停在"出卡"（最保险，任何 Shell 都能开）；
这一目录证明同一张卡片接上宿主能力后，能在聊天软件里真的把消息发出去。**

---

## 1. 这是什么能力

官方 App Hub `main` 的 `KNOWN_CAPABILITIES` 里有一整套 **`matrix.*`**，其中
**`matrix.send_message`** 就是"让迷你应用往聊天里发一条消息"。这正是「拾意」五屏里
第 5 屏「回执」想做的动作——**确认之后，真的把安排发进聊天**。

| 文件 | 是什么 |
|---|---|
| `manifest.send.json` | **执行版 `manifest`**：在现行清单上只加一条 `capabilities: ["matrix.send_message"]` |
| `bindings.json` | **能力接线**：`on_open` 里声明"打开即发一条"，把卡片动作接到宿主服务 |
| `证据/演示视频_Rinx执行链_拾意.mp4` | **全流程实录（43 秒，带字幕）**：导入 → 填房间 → Review → Run → **消息出现在聊天里** |
| `证据/`（其余） | 真机实证：Review 通过（显示已授权能力与房间）/ Run 后卡片 / **房间消息 JSON** |

## 2. 为什么单独放这儿，不塞进 `bundle/`

与 `../ai/` 同一条理由，**核实过**：

- 现行**多数 Shell 只认 7 项能力**，manifest 会**拒收未知字段**。把 `matrix.*` 直接写进
  `bundle/manifest.json`，风险是**"作品在评审用的旧宿主里根本打不开"**。
- 官方原话（AI 服务文档）：**「想现在就在 OctoSense 中打开的应用包，请不要使用它们。」**
  → **保命版 `bundle/`（`capabilities = []`）继续当提交物**；执行扩展作为**独立备件**，随宿主就绪再合入。

**保命版 + 独立备件**——和 `ai/` 一个哲学：**提交物永远是最小、最能开的那个形态；深度用备件证明。**

## 3. 怎么用（三步，全部可复现）

前置：本机已编出 Rinx（见 `../README.md` §5 的隔离环境；Rinx 源码 `hagency-org/Rinx`）。

```sh
# 0) 假设仓库根为 $APP，做一份**副本**（绝不改提交物 bundle/）
cp -r "$APP/bundle" /tmp/shiyi-send

# 1) 合入执行扩展：覆盖 manifest + 放入 bindings
cp "$APP/rinx/manifest.send.json" /tmp/shiyi-send/manifest.json
cp "$APP/rinx/bindings.json"      /tmp/shiyi-send/bindings.json

# 2) 重算摘要（★ 必做，否则宿主按摘要不符直接拒收）
"$RINX_BIN" 里的打包器：  rinx-miniapp-package /tmp/shiyi-send
#   期望输出：Packaged shiyi 0.2.2
#   期望摘要：bundle_blake3 = 3235e8f36978facda63eddc818741875051e016b29508ec5727a287e518d7110

# 3) 进 Rinx：左侧「Mini apps」→「Import an app」→ 填副本路径
#    → 在 "Room ID to allow" 填上目标房间 → 「Review bundle」→「Run」
```

**摘要可复现**：`bundle/` 原样 + 本目录两份文件 ⟶ `bundle_blake3` **恒为
`3235e8f3…6710`**（本机实测复现，见 §5）。任何改动都要按第 2 步重算。

> ⚠️ **`matrix.send_message` 发到哪个房间，不是卡片说了算**——是**导入表单里填的房间**
> 绑进宿主的。不填会报 `not attached to a room`。

## 4. 实证（本机 2026-10-04 跑通）

**① Review 通过**（`证据/01_…png`）：界面明写
`Services: matrix.send_message`、`Allowed room: !6OTFycyqxSkwYHJuBr:matrix.rinx.chat`。

**② Run 后卡片渲染**（`证据/02_…png`）：五屏之首的识别卡整张出现在 Rinx 里。

**③ 房间消息真发出**（`证据/房间消息_关键事件.json`，API 直查房间所得）：

```json
{
  "content": { "body": "【拾意 Pickup】下周三去深圳 — 已确认，日程已记下。（经 Rinx 迷你应用发出）",
               "msgtype": "m.text" },
  "event_id": "$_1MPYw2dqjKOP6gBoU26kUrg3ZAEzYx0qpHwfbVg0wc",
  "room_id": "!6OTFycyqxSkwYHJuBr:matrix.rinx.chat",
  "sender": "@sansanyi331:matrix.rinx.chat",
  "type": "m.room.message"
}
```

即：**第三方（本地未签名）迷你应用 → Rinx 宿主 → 真实 Matrix 房间**，整条链路通。

## 5. 宿主机制（接线要点，已摸清）

- **`matrix.send_message` 的房间**来自导入时填的 **Room ID**（宿主绑进 lease），不是卡片参数。
- **`bindings.json` 的 `on_open` 在 Run 时自动执行** ⇒ 想"打开即发"不必改卡片。
- 想"**点按钮才发**"，就在卡片里用 `NAV("l0:{…}")` 触发事件，挂到 `bindings.events` 同名键。
- 宿主能力齐备：`src/host/matrix/policy.rs`（白名单）+ `src/host/matrix/send.rs`（`ensure_room_access(Write) → room.send()`）。
- 本目录模板的 `on_open` 写的是**示例文案**；正式接线时按第 5 屏回执的真实内容替换 `body`。

## 6. 与提交物的关系（一句话）

```
bundle/             ← 提交物。capabilities=[]，任何 Shell 都能开（保命版）
ai/                 ← 备件：接设备助手（model/agent）的契约
rinx/               ← 备件：接宿主执行（matrix.send_message）的适配 + 实证 ★本目录
```

**提交物不掺未知字段；能力在备件里，随宿主就绪合入。**
