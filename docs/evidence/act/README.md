# 证据 · 「确认 = 真办事」（0.7.3）

> **一句话**：确认一张卡，**不只是记一笔** —— 它把这次意图的结论**真的发回你绑定的那个群**。
> 这是「意图即应用」里**「应用」那半截**：卡会长出来，也会**把事办掉**。
> 全部由 Rinx 自带遥控口 `MAKEPAD_REMOTE` 驱动（`/snap` 取坐标、`/click` 与 `/m` 点、`/g` 抓帧），**无人手**。

| 帧 | 文件 | 看什么 |
|---|---|---|
| ① Review | `01-review-six-services.png` | 导入时宿主列出**六个服务**并全部接受：`storage, model, octos.session.history, matrix.read_messages, matrix.profile,` **`matrix.send_message`**；`Allowed room: !6OTFycyqxSkwYHJuBr:matrix.rinx.chat` |
| ② 运行 | `02-app-opened.png` | app 跑起来：长期记忆、读到 4 条房间消息（带「（你）」）、输入框、例子、卡片区 |
| ③ 造卡 | `03-card-built.png` | 点一条消息 → 造卡：读出「出行」卡 · 下周三 · **10月14日** · 深圳 |
| ④ 确认 = 真办事 | `04-confirm-sent.png` | 卡片底部两行：`✓ 已记下，记忆已更新` + **`已把结果发回群 —— 这件事真的办成了`**（青色） |
| ⑤ 落进群 | `05-room-message.png` | 房间「拾意 Pickup · 测试房」· **2026-10-06** 新增一条：**`✅ 拾意已记下 · 下周三 · 10月14日 · 深圳`**（上面 4 条是 10-04 历史） |
| ⑥ 连续录屏 | `rinx-act-end-to-end.mp4` | **27 秒 · 2200×1440 · H.264**，**一段连续真实录屏（非帧拼）**：导入表单 → Review（六服务）→ Run → 清记忆 → 点消息 → 造卡 → **确认** |

## 复现

1. Rinx 以遥控模式启动：`MAKEPAD_REMOTE=8799 ./rinx.exe`（构建产物落在你的工作区）。
2. 导入 `apps/shiyi-live/bundle`，`Room ID to allow` 填一个你已加入的房间 → **Review bundle**（应列出上面六个服务）→ **Run**。
3. 点「从聊天拾意」里任一条消息（或例子、或自写一句）→ **造卡** → **确认行程**。
4. 看两处：卡片底部出现 `已把结果发回群 —— 这件事真的办成了`；回到那个房间，**多出一条由你发出的回执**。

## 边界（fail-closed）

- 宿主没有 `matrix.send_message` 这项服务、或没绑房间 ⇒ 卡片**如实说明**「没能发回群 —— 结果只留在本机」，**绝不假装成功**。
- 发送动作**只针对导入时绑定的那个房间**（`Allowed room`），不发别处。
- 识别仍在本机做，不依赖任何服务；`model.complete` 仍默认关（Rinx 拒绝 `model.complete`，见 `评审速览.md`）。
