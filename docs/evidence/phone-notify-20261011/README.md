# 手机端 · 到点提醒「会说话」+ 开关 · 真机实证

> **2026-10-11 · 小米13（`f40f11dc`）· Rinx 1.1.0（本地构建，含我们加的两项能力）**
> 本目录证三件事：**① 到点提醒真弹系统通知 ② 提醒真的被"念"出来（系统 TTS，有音频日志）③ 有一个开关可以关掉语音**。
> 通知标题与正文都是**助手写的**；全部对实物取证（截图 + `dumpsys` + 音频日志），未修饰。

---

## 1. 链路（谁做什么）

| 步 | 谁 | 做什么 |
|---|---|---|
| ① | 助手（手机走 `octos.turn.start`） | 判**要不要提醒、提前多久**，并**写出提醒时该说的那句话** |
| ② | 作品 `main.splash` | 卡上如实显示「提醒 · 提前 1 天」「到时说 · 「…」」，并给一个**语音开关** |
| ③ | 用户 | 点「记下来」确认（开关想关就关） |
| ④ | 作品 → 宿主 | `rinx.notify`（弹通知）+ **`rinx.speak`（念出来）** |
| ⑤ | 宿主（安卓侧） | 弹**系统通知**（渠道 `rinx.remind`）+ 交给**系统 TTS** 念 |

**要点**：**弹和念都是宿主干的** —— 作品只说"弹什么、念什么"，能不能弹/念由宿主负责。这正是官方 App 模型的形状（应用声明、宿主执行）。

---

## 2. 现场（真机截图 + 原文）

| 文件 | 证什么 |
|---|---|
| `06-switch-on-with-remind.png` | 卡上有「**提醒 · 提前 1 天**」「**到时说 · 「记得去驿站取顺丰快递」**」，按钮行里多了一个 **「语音提醒：开」** |
| `05-switch-off.png` | 点一下开关 → **「语音提醒：关」**（开关真的能切） |
| `04-card-notify-and-spoke.png` | 确认后卡上回执：**「· 已弹提醒：提前 1 天 · 已念出来」** |
| `03-notify-speak-system-notification.png` | 手机**通知栏**里真躺着一条：标题「**去驿站取顺丰快递**」、正文「**记得去驿站取顺丰快递**」 |
| `01-card-remind-lead-hour.png` / `02-system-notification.png` | 更早一轮（加语音之前）的同链路实拍：卡上「提醒 · 提前 1 小时（临期）」+ 通知栏 |
| `notification-dump.txt` | `dumpsys notification` 原文：`pkg=org.octosense.rinx id=9001 channel=rinx.remind`、`android.title=(去驿站取顺丰快递)`、`android.text=(记得去驿站取顺丰快递)` |
| `tts-logcat.txt` | **音频系统日志**：`startOutput() … appname com.xiaomi.mibrain.speech, uid 10250`（18:20:31 起播、18:20:33 停）—— **真的出声了**，不是只调了个函数 |

**这一轮的输入**：房间里的一条真消息「顺丰到楼下了，明天去驿站取件」
**助手读出**：类型=代办 · 时间=明天 · 地点=驿站 · **提醒=提前 1 天** · 话术=「记得去驿站取顺丰快递」

---

## 3. 宿主侧改了什么（两项能力，官方 Rinx 没有）

**① `rinx.notify`（弹通知）**

1. `vendor/octosense-app-contract/src/manifest.rs`：`KNOWN_CAPABILITIES` 增收 `rinx.notify`
2. `src/miniapps/ui.rs`：`pump()` 里当场分发 → `fn notify()`（走与 `matrix.*` **同一张租约**）
3. `resources/android/java/org/octosense/rinx/MakepadAppExtension.java`：`command()` 加分支 → `showNotification()`（渠道 `rinx.remind`，安卓 13+ 运行时申请 `POST_NOTIFICATIONS`）
4. `resources/android/AndroidManifest.xml.template`：声明 `POST_NOTIFICATIONS`

**② `rinx.speak`（念出来）** —— 同一套四处：

1. 契约 `KNOWN_CAPABILITIES` 加 `rinx.speak`
2. `ui.rs`：`pump()` 分发 → `fn speak()`（同一张租约；非安卓是安全空操作）
3. `MakepadAppExtension.java`：加分支 → `speakText()`（**安卓自带 `TextToSpeech`**；payload 收纯文本或 `{"text":…}`；首次调用异步初始化，期间的话先排队）
4. 无需新权限（TTS 不要权限）

**未碰 octos 内核一行。**

---

## 4. 怎么复现

1. 装带这两项能力的 Rinx 构建 → **发现 → Mini apps → 导入应用**
2. bundle 填 `…/files/import-v083/bundle`（脚本应用 **0.8.3**，`capabilities` 含 `rinx.notify` + `rinx.speak`）→ Room 填绑定房间 → **Use this device** → **Review bundle** → **Run**
3. 从房间消息点一条**带时间的** → 等助手出卡（卡上会出现「提醒 · …」与「语音提醒：开」）
4. 点「**记下来**」→ 通知栏应出现一条，同时**念出来**；想静音就先把开关点成「关」

> ⚠️ 真机操作注意：这台机器上 Makepad 的**点击坐标与画面会随滚动位置漂移**（本次实测：某滚动位下按钮命中 y ≈ 画面 y；另一处约差 77px）⇒ 可靠做法是**扫描式点击**（同 x 扫 y、看画面/通知是否变化）。

---

## 5. 如实说明（边界）

- **当前宿主是"即时弹/即时念"**：提醒在**你确认后立刻**弹与念。**"提前 1 天"这个时间点本身还没有排程**（真正到点触发要么宿主侧排程，要么应用在前台自己计时）—— 本轮验的是**通道真的通、话真的念出来了**，不是"定时器也做好了"。
- **Rinx 侧不是官方发行件**：这是本地构建（1.1.0 + 上面几处改动）；官方 Rinx 上没有 `rinx.notify` / `rinx.speak`。
- **主提交（根 `bundle/` 0.8.0）不含这两项能力**：它跑在 OctoSense 宿主上；`rinx.*` 是 **Rinx 宿主专有**。两线不混说。
- **语音开关**是作品侧的（卡片上的按钮，存进本机记忆）；宿主不关它。
- `POST_NOTIFICATIONS` 需授予，否则通知弹不出来（本轮已授予）。

---

*整理：2026-10-11 ｜ 队伍 三三Claw ｜ 全部条目对实物取证（截图 + dumpsys 原文 + 音频日志）；没做的部分标"还没做"，不写成已完成。*
