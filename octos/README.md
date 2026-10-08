# octos/ — 拾意做成 OctoSense 系统 app（快览屏 / 原地改卡 / 会说话）

这一目录**不进提交包**（不在 `bundle/` 里）。它装的是「拾意」跑在 **OctoSense 本体**上的三段能力所需文件与实证：

1. **快览屏（glance）集成** —— 拾意作为官方同级 **system app**（`os.shiyi`），把卡钉进**系统快览屏**、和应用同生命周期（**底层**）。
2. **助手「原地改卡」** —— 给拾意挂一个它自己的工具 **`shiyi.repin`**，助手在卡的对话里就能把钉的那张卡**原地改掉**（**建在第 1 条之上**）。
3. **拾意「会说话」** —— 给拾意加一张**嘴**：钉卡时用**系统 TTS** 把卡念出来（D2），到点**自己再弹一次提醒 + 再念一遍**（D1）。**输出侧、只说不听**，不碰 33OS。

> 第 1 条（快览屏）的完整实证见 [`../docs/evidence/glance/`](../docs/evidence/glance/README.md)；
> 第 2 条（改卡）见 [`../docs/evidence/repin/`](../docs/evidence/repin/README.md)；
> 第 3 条（会说话）见 [`../docs/evidence/speak/`](../docs/evidence/speak/README.md)。
> **三条都走官方预留扩展点、没碰 octos 内核一行。**

---

## 0. 快览屏（glance）集成 —— 底层

拾意注册为官方同级 system app，与官方 `os.photos / os.maps / os.ai-providers / os.youtube`
**并列**在同一个 notice 服务表里（`apps.rs:228`）；只声明 `["storage","glance"]` 两个能力。

- **真接官方宿主**：用的是 OctoSense **官方 shell** 里真实存在的 `glance` host service（`glance.publish / withdraw / list`），不是自搭仿真。
- **多卡常驻 + 持久化**：每 app 上限 4 张；本地 `picks.json` 落盘，**重启后读回**。
- **同 id 再发 = 原地替换**：`glance` 按 `(app, card_id)` 键控；同句重钉面板卡数不变、卡原地更新（宿主回执 `replaced`）。
- **诚实**：快览屏内容随 shell 重启清空（宿主行为）；拾意**如实报"0 张"**，不谎称"对得上"。

复现、原始日志、截图与录屏见 [`../docs/evidence/glance/`](../docs/evidence/glance/README.md)。

---

## 1. 为什么需要「改卡」（问题 → 做法）

**问题**：点开一张卡能跟助手聊（真模型回话），但助手**改不了卡片本身**。
卡的对话里，宿主提示词（`l0-chat/src/lib.rs:539`）明写
*"Only claim a change after an executable tool confirms it"*——
**"能不能改"完全取决于 app 挂没挂工具**。没挂 ⇒ 助手只能"聊"。

**做法（官方正路）**：官方从不让模型"直接摸卡"。它给的入口是
**app 声明一个工具 → 助手调它 → 用同一个 `card_id` 重发 = 原地替换**。
卡按 `(app, card_id)` 键控（`glance.rs:390/455`，返回 `{"replaced": …}`），
官方 Calendar（`calendar.notify`）/ News / Mail（`mail.publish_card`）全都这么做。

⇒ 拾意缺的只是一个 `tools.json` + 一个宿主服务。补上即可，**不动内核**。

---

## 2. 代码落点（相对官方 OctoSense 仓库 `OctoSense-org/OctoSense`）

| 文件 | 状态 | 说明 |
|---|---|---|
| `apps/shiyi/bundle/tools.json` | **新增** | 拾意工具清单（此前不存在）。声明唯一工具 `shiyi.repin`，`risk:"act"`、`background:false`、`implemented_by:"host-service"`；input `card_id`(必填)/`title`(必填,1-80)/`when`/`where`/`as_of`；output `{card_id,replaced,expires_at}` |
| `apps/shiyi/bundle/main.splash` | **修改** | 拾意的造卡 app。**D1 到点提醒**：+38 行（`arm()/fire()/tick()`；到点**复用已授权的 `glance.publish` + `notify:true`** 把同一张卡再发一次 = 原地更新 + 再弹一次通知）。repin 复用活卡的 L0 源码 |
| `apps/shiyi/bundle/manifest.json` | 已有 | 系统 app 清单（`bundle_blake3` 留空，构建期由 `pack_system_app` 自动盖章）。**版本 0.2.0 → 0.2.1**（加语音） |
| `crates/shell/src/shiyi.rs` | **新增** | 拾意的 host service。`repin(app,args)`：从**活卡**取 L0 源码**原样复用**（模型只改数据、不改卡代码），只换 `rec` 数据 → `crate::glance::publish_for("os.shiyi", &publish)`。含 2 单测 |
| `crates/shell/src/lib.rs` | **修改** | ① 加 `pub mod shiyi;`（`:90`）；② **`glance_notify()` 里 `note.app == "os.shiyi"` → `android_speak`**（**D2·输出侧、只说不听**；`spoken_title` 先 clone 规避 move）；③ `local_utc_offset_secs()`（**#343 时区修复**，另述） |
| `crates/shell/src/apps.rs` | **修改** | `register_host_services()` 加 `crate::shiyi::register();`（`:228`，在 `glance_notice::serve_system_apps()` 兜底之前） |
| `crates/shell/src/android_integration.rs` | **修改** | **D2**：新增 `android_speak(cx, text)` → `android_command(cx,"bridge","speak",[("text",…)])`（非 Android 平台 = 空操作） |
| `phone/resources/android/java/…/MakepadAppExtension.java` | **修改** | **D2**：`bridgeCommand` 开头**特判 `operation=="speak"`** → 本地 `speakText()`（`android.speech.tts.TextToSpeech`，**绕开 system-bridge，单 APK 即可**） |

> **D2 的三处框架改动，已收成一份可应用补丁**：[`host-extension/speak_host_extension.patch`](host-extension/speak_host_extension.patch)
> —— 基线 = 官方 `OctoSense-org/OctoSense`；`git apply --check` **干净通过**；
> 补丁里**只含语音**（lib.rs 的 repin / 时区两处既有改动**不在内**）。

### 2.1 拾意「会说话」—— D1 到点提醒 + D2 语音读卡

**问题**：拾意原来只会"把卡贴出来"——**你不看就不知道**。复赛要让它在**任务完成 / 人机协作**上更进一步：
**从"你看了才知道" → "它到点主动喊你、还把卡念给你听"**。

| | 是什么 | 落在哪 | 靠什么 |
|---|---|---|---|
| **D1 · 到点提醒** | 钉卡后计时到点 → **自己再弹一次**"该动身了 · …" | **bundle**（`main.splash`） | 复用**早已授权**的 `glance.publish` + `notify:true`（每次成功都弹一次通知）——**零新能力** |
| **D2 · 语音读卡** | 出卡 / 到点通知时，用**系统 TTS**把卡念出来 | **宿主**（3 处框架改动，见上表） | `glance_notify()` 里对 `os.shiyi` 的通知调 `android_speak` → Java `TextToSpeech` |

**链路**：

```
拾意 bundle（钉卡→arm→tick 到点）
  → host.request("glance.publish", {… notify:true})   [已授权能力]
  → shell glance_notify()                              [lib.rs]
  → note.app=="os.shiyi" → self.android_speak(cx, 文字)
  → android_command(cx,"bridge","speak",…)             [android_integration.rs]
  → MakepadAppExtension.bridgeCommand 特判 "speak" → 本地 speakText()
  → Android 系统 TextToSpeech 出声
```

**为什么不算越界（划得清）**：

- **输出侧、只说不听**：只往扬声器写，**不收麦克风**——不碰任何"对话/识别"。
- **用 Android 系统 TTS**（本机 MIUI 的 `mibrain`），**与 33OS 无关**，不依赖任何自有语音资产。
- **不改内核**：走 `glance_notify` 这个**已有钩子** + `android_command` 这条**已有通道**，与官方既有通知同构。

**⚠️ 诚实边界（必须讲清）**：

1. **"出声"这半在宿主里、不在作品里**：官方 OctoSense 宿主**没有**"让 app 说话"的服务（见 `OctoSense/docs/ai-services.zh-CN.md`：给 app 的服务只有 `octos.* / model.* / glance.*`）。
   ⇒ **D1（到点提醒）是纯 bundle，任何宿主都能跑**；**D2（真出声）靠的是"我方给宿主加了这张嘴"**——
   对外要讲成**"对 OctoSense 宿主的一个扩展贡献"**，**不能**说成"bundle 自带语音"。
2. **真机证据**：[`../docs/evidence/speak/`](../docs/evidence/speak/README.md)——小米13 `f40f11dc`，
   `tts_logcat.txt` 里有系统 TTS 引擎自己"收单/合成/播完"的日志（**"真出声"由引擎日志作证，不是靠视频听出来的**；`screenrecord` 不录内部音频）。
3. **演示用压缩计时**：真产品按卡里的 `when` 到点；演示为让评委当场看到，钉卡后 ~5 秒触发一次。

> **为什么落这儿**：`apps/shiyi/`（"拾意"）是**我们自己的系统 app**（官方原生 `native-apps.json` 里**没有** shiyi，
> 是我们把它加进 `phone/system-apps.json` / `desktop/system-apps.json`、**随内核一起编**的）。
> 系统 app 的 own namespace（`os.shiyi` → family `shiyi`）由 `script_apps.rs:243` **自动放行**——
> 所以**免 grant**；bundle 摘要由构建期**自动盖章**——所以**免手动签名**。

## 3. 两个"白捡"的便利（比预想省）

- **免 grant**：`crates/shell/src/script_apps.rs:243` 判定 `app.strip_prefix("os.") == Some(family)` 时**自动放行 own namespace**；`os.shiyi` 是系统 app、family=`shiyi` ⇒ **连 manifest 的 capabilities 都不用动**。
- **digest 自动盖章**：系统 app 的 bundle 由构建期 `pack_system_app` **自动重算摘要并盖章**（源 manifest 的 `integrity.bundle_blake3` 留空 `""`）⇒ **无需手动签名**。

## 4. 🚨 一个真坑：`build.rs` 只监听"已存在文件"

- **现象**：首次 `cargo build --release` 后，release 制品 `system-shiyi.pack.json` 仍只有 `main.splash`+`manifest.json`（旧版）；debug 版却含 `tools.json`。
- **根因**：`build.rs` 的 `watch()` **只监听"上次构建时已存在的文件"** ⇒ **新增的 `tools.json` 不在监听列表** ⇒ cargo 不重跑 build.rs ⇒ pack 不含它。
- **修复**：`touch apps/shiyi/bundle/manifest.json` 强制重跑 build.rs → 重编 → pack 现含 `['main.splash','manifest.json','tools.json']`；二进制/包内 base64 解出含 `shiyi.repin`。
- **⚠️ 桌面、手机同一个坑**（手机 pack 15:09 < tools.json 15:53 ⇒ 同样只含两文件）。

## 5. 怎么验证（复现）

**桌面（Windows）**：编 `octosense.exe`（`cargo build --release -p octosense`）→
`MAKEPAD_REMOTE=8399 OCTOSENSE_HOME=… octosense.exe` → F9 开快览屏 → 点卡 → Chat → 说"把这张卡改成…"。
**手机（小米13）**：`phone/system-apps.json` 含 `shiyi` ⇒ `./build_octosense_apk_kernel.sh` 重打 APK（含 `liboctos.so`）→ 装机 → 真机点卡改卡。

**实测证据**（双端均跑通）：见 [`../docs/evidence/repin/`](../docs/evidence/repin/)——
会话 jsonl（模型自己发的 `shiyi_repin` tool_call + 工具真返回 `{"replaced":true}`）、
工具审计（`risk:"act"`、`outcome:"ok"`）、改卡前后截图、README 说明。

## 6. 边界（fail-closed，划得清）

- **不改内核**：走官方预留扩展点（`tools.json` + host-service），与官方成卡工具同构。
- **路 B 未走**：让 `main.splash` **自己实现**工具（`implemented_by:"app"`）**被宿主硬拒**——
  `script_apps.rs:237` 回 *"…declares a script implementation, but this host does not support script tool dispatch"*。
  这条**要动宿主分发链**，属上游功能缺口，**我们没走**。
- **只改数据，不改卡代码**：`repin()` 从活卡取 L0 源码**原样复用**，只换 `rec` 数据 ⇒ 卡永远是 app 自己那张卡。
- **该拒就拒**：卡不存在 / 不是 L0 卡 / 标题空或超长 ⇒ `shiyi.repin` 直接拒（带模型能照办的错误原因），**绝不动别的卡**。

## 7. 与提交物的关系

```
bundle/     ← 提交物（主）：L0 卡片包，任何 Shell 都能开（保命版）
apps/shiyi-live/  ← 提交物（附）：脚本应用，一句话现场造卡
ai/         ← 备件：接设备助手（model / octos.*）的契约
rinx/       ← 备件：接宿主执行（matrix.send_message）的适配 + 实证
octos/      ← 备件：接 OctoSense 本体、让助手「能改卡」+ 拾意「会说话」的宿主扩展 ★本目录
```

**本目录三段能力（都不进提交包、随宿主就绪合入）**：
① 快览屏（glance）· ② 助手原地改卡（`shiyi.repin`）· ③ **拾意会说话（D1 到点提醒 + D2 语音读卡）**。

**提交物最小、最能开；深度能力在备件里，随宿主就绪合入。**
