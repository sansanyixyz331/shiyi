# 证据 · 「助手原地改卡」（桌面 + 手机双端已跑通）

> **一句话**：给拾意挂上它自己的工具 `shiyi.repin` 之后，**助手在卡的对话里就能把你钉的那张卡原地改掉**——
> 模型自己选工具、传参数，卡的标题/时间/地点真的变了，**不是又长一张，是那一张被换掉**。
> 这是「能聊」到「能改」的那一步：**从顾问到代理**。

> **不碰官方内核**：走的是官方预留的扩展点（`bundle/tools.json` 声明 `implemented_by:"host-service"` +
> 宿主侧注册同名 host service），和官方 Calendar / News / Mail 的成卡工具是**同一条路**。

---

## 一、桌面（Windows · `octosense.exe` 参考宿主 + `liboctos` 内核）

**内核 pin**：`056173e8` · **provider**：DeepSeek V4 Flash

### 现场操作

1. 按 **F9** 打开快览屏
2. 点开卡 `shiyi-p1`（原内容：**下周三去深圳见客户**）
3. 切到 **Chat** 页签
4. 输入 **「把这张卡改成下周四去广州见客户」** → 发送

### 黄金证据（`desktop_card_chat.jsonl`，会话 `9cc55cb2-p1-card-chat`）

**① 模型自己发出的 tool_call**（不是我们摆的）：

```json
{"role":"assistant","content":"","tool_calls":[{"id":"call_00_4f65OoAW30d9HXQ3t4bC9939","name":"shiyi_repin","arguments":{"card_id":"shiyi-p1","title":"下周四去广州见客户","when":"下周四","where":"广州","as_of":"2026-10-6 14:08"}}],"reasoning_content":"The user wants to change the pinned card. I have the `shiyi_repin` tool. ... Note the previous turn said I couldn't edit the card — but now the tool `shiyi_repin` is available. So I should use it. ... Let me call."}
```

**② 工具真返回**（宿主侧执行成功，卡被替换）：

```json
{"role":"tool","content":"{\"card_id\":\"shiyi-p1\",\"expires_at\":1791878601433,\"replaced\":true}","tool_call_id":"call_00_4f65OoAW30d9HXQ3t4bC9939"}
```

**③ 模型收尾回复**：

```json
{"role":"assistant","content":"卡片已改好，现在显示的是「下周四去广州见客户」，时间和地点也换成了「下周四 / 广州」。下周四对应 2026-10-15，需要的话我可以再帮你查那天广州的天气或设个提醒。"}
```

**④ 改卡后截图**（`card_after_repin.png`，原图 1750×1125，OCR 复核）：

```
下 周 四 去 广 州 见 客 户              ← 卡片新标题（原为「下周三去深圳见客户」）
把 这 张 卡 改 成 下 周 四 去 广 州 见 客 户   ← 用户输入
卡 片 已 改 好 , 现 在 显 示 的 是 [ 下 周 四 去 广 州 见 客 户 ] , …   ← 助手回复
```

**⑤ 宿主日志**：`glance: os.shiyi published shiyi-p1`（`replaced:true`）。

**⑥ 端到端录屏**（`desktop_repin_end_to_end.mp4`，52s / 1750×1124 / **真录屏非帧拼**）：

一段连续真实录屏，全程无人手介入、遥控口驱动：**造卡 → F9 开快览屏 → 点开卡 → 切 Chat
→ 输入「把这张卡改成下周四去广州见客户」→ 点 ↑ 发送 → 助手调 `shiyi.repin` → 卡原地变**。
逐帧 OCR 可复核：约 27s 卡片标题仍为「下周三去深圳见客户」；约 30s 起变为「下周四去广州见客户」
且出现助手回复「…原来的深圳那条被替换掉了，没有多出一张」。（录制由遥控口逐步驱动，驱动脚本为开发期工具、未随仓发布。）

---

## 二、手机（小米13 · `f40f11dc` · Android 13 / arm64-v8a · 已 root）

**包**：`dev.makepad.octosense.shiyi`（旁装，**不碰**官方 9-19 版）
**APK**：`phone/target/android/makepad-android-apk/octosense_home/apk/octo_sense.apk`（252 MB，含 `liboctos.so` + 新 `tools.json`）

### 现场操作（全 adb 驱动）

1. `run-as` 写内核 provider：`files/octos-home/.octos/profiles/_main.json`（DeepSeek V4 Flash）
2. 拉起 App → 日志 `octos: kernel service ready` + `glance: the notice service answers ["os.photos","os.maps","os.camera","os.ai-providers","os.youtube"]`（**不含 os.shiyi** ⇒ 拾意已有自己服务）
3. **造卡**：搜索"拾意" → 打开 → 输入"明天下午四点去银行办卡" → 造卡 → 钉到快览屏
4. **右滑到 glance 页**（手机端 glance 在最左页，位置 `-1`）→ 点卡 → **Card / Chat 两页签** → Chat
5. 首次要授权 → 直接从数据侧写 `files/.octosense/approvals/consent.json`
6. 输入 **「把这张卡改成后天上午九点去机场接人」** → 发送

### 黄金证据

**① 会话 jsonl（`phone_card_chat.jsonl`）**

模型自己发出的 tool_call：
```json
{"name":"shiyi_repin","arguments":{"card_id":"shiyi-p5","title":"后天上午九点去机场接人","when":"2026-10-08 上午九点","where":"机场","as_of":"2026-10-6 16:19"}}
```
工具真返回：
```json
{"card_id":"shiyi-p5","expires_at":1791879623694,"replaced":true}
```
模型收尾回复：*"已改好：这张卡现在是「后天上午九点去机场接人」，时间标为 2026-10-08 上午九点，地点是机场，**原来那张已经被替换，不会多出一张**。"*

**② 工具审计（`phone_tool_audit.jsonl`，内核自己的账）**

```json
{"tool":"shiyi.repin","app":"os.shiyi","risk":"act","decision":"allowed","outcome":"ok","duration_ms":102,"args_bytes":142,"result_bytes":65}
```

**③ 改卡前后截图**

| 文件 | 看什么 |
|---|---|
| `phone_card_before.png` | 卡原样：「明天下午四点去银行办卡」 |
| `phone_assistant_replied.png` | Chat 里助手回复已改好 |
| `phone_card_after.png` | **glance 页卡已变**：「拾意 · 后天上午九点去机场接人 / 地点 · 机场」 |

**④ 端到端录屏**（`phone_repin_end_to_end.mp4`，150s / 1080×2400 / **真机录屏**）：

小米13 真机一段连续录屏，全 adb 驱动、无人手：**冷启动 → 左滑到 app 网格 → 点拾意 →
输入一句话造卡 → 返回桌面 → 滑到 glance 页 → 点卡 → 切 Chat → 输入「把这张卡改成下周四去广州见客户」
→ 点 ↑ 发送 → 助手回「已改好…原地替换了原来那张」→ glance 页卡已变**。
逐帧 OCR 可复核：约 42s 卡仍为「下周三去深圳见客户」+ 用户输入；约 53s 助手回复「已改好，卡片
shiyi-p6 现在显示「下周四去广州见客户」…」；约 105s glance 页卡变为「拾意 · 下周四去广州见客户 / 地点 · 广州」。
（全程 adb 驱动，驱动脚本为开发期工具、未随仓发布。）

---

## 三、链路要点（为什么这么省）

- **免 grant**：`crates/shell/src/script_apps.rs:243` 判定 `app.strip_prefix("os.") == Some(family)` 时**自动放行 own namespace**；`os.shiyi` 是系统 app、family=`shiyi` ⇒ **连 manifest 都不用改**。
- **digest 自动盖章**：系统 app 的 bundle 由构建期 `pack_system_app` **自动重算摘要并盖章**（源 manifest 的 `integrity.bundle_blake3` 留空 `""`）⇒ **无需手动签名**。
- **卡按 `(app, card_id)` 键控**：`glance.rs:390/455` 同 `card_id` 再发布 = **替换**（返回 `{"replaced": true}`），不是新增一张。
- **卡对话 = 该 app 自己 conversation 里的一次 turn**（`glance_chat.rs:222`）⇒ 助手能调的工具 = 该 app `tools.json` 声明的。
- **官方留的口子**：卡对话宿主提示词（`l0-chat/src/lib.rs:539`）明写 *"Only claim a change after an executable tool confirms it"* / *"If you cannot edit this card or perform an action, say so plainly"* —— 官方本来就**等着** app 挂工具。

## 代码落点（相对官方 OctoSense 仓库）

| 文件 | 状态 | 说明 |
|---|---|---|
| `apps/shiyi/bundle/tools.json` | 新增 | 声明工具 `shiyi.repin`（`implemented_by:"host-service"`, risk `act`） |
| `crates/shell/src/shiyi.rs` | 新增 | 拾意的 host service；`repin()` 从**活卡**取 L0 源码**原样复用**、只换数据，再 `publish_for("os.shiyi", …)` |
| `crates/shell/src/lib.rs` | 修改 | `pub mod shiyi;` |
| `crates/shell/src/apps.rs` | 修改 | `register_host_services()` 里 `crate::shiyi::register();` |

> 本仓内**随附的落地副本**（可直接对照查看）在 [`../../../octos/`](../../../octos/README.md)：
> `octos/apps/shiyi/bundle/tools.json`、`octos/crates/shell/src/shiyi.rs`。

**未碰 octos 内核一行。**

## 边界（fail-closed）

- 卡不存在 / 不是 L0 卡 / 标题空或超长 ⇒ `shiyi.repin` **直接拒**（带模型能照办的错误原因），**绝不动别的卡**。
- 模型改的是**数据**（title/when/where/as_of），**卡源码原样复用** ⇒ 卡永远还是 app 自己那张卡。
- **路 B（让 main.splash 自己实现工具）当前被宿主硬拒**（`script_apps.rs:237`：*"this host does not support script tool dispatch"*）⇒ 这条得上游接线，**我们没走**。
