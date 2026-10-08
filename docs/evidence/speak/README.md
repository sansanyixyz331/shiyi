# 拾意「会说话」真机证据 · 2026-10-08

> 设备：小米13 `f40f11dc`（fuxi）· 应用：`dev.makepad.octosense.shiyi`（自编 OctoSense Home APK，含 liboctos.so 内核 + 拾意 bundle）
> 干什么：**给拾意加"嘴巴"（输出侧语音播报）+ "到点自己醒"（定时提醒）** —— 本地做全、真机验证，未推仓。

## 一、这条证据证明什么

| 能力 | 结论 | 证据 |
|---|---|---|
| **D2 · 语音读卡** | ✅ 钉卡的**同时**，拾意用**系统 TTS**把卡念出来 | `tts_logcat.txt` 第 3-8 行；视频 ~17-21s |
| **D1 · 到点提醒** | ✅ 几秒后**自己**再弹一次"该动身了 · …"通知，**并再念一遍** | `tts_logcat.txt` 第 9-14 行；视频 ~24s |
| 出卡 | ✅ 卡钉进快览屏（原有能力） | 视频 ~21s；`key_frames/01_publish_notify.png` |

## 二、怎么证明"真出声了"（不是只调了个函数）

系统 TTS 引擎（`com.xiaomi.mibrain.speech`，pid 11795）**自己的日志**显示它**真的合成并播完了**：

```
speak: os.shiyi reads 周日早上九点去菜市场买菜。地点 · 菜市场           ← 我方触发
TtsEngineProcessor: speak sync Begin text=周日早上九点去菜市场买菜。地点 · 菜市场   ← 引擎收单
CloudTtsEngine: speakInternal: text=… eventId=3cba…                    ← 引擎去合成
TtsEngineProcessor: speak  sync  out                                    ← 播完（~3.5s）
```

→ 同一条链在到点时**又走了一遍**（text = `该动身了 · 周日早上九点去菜市场买菜。地点 · 菜市场`）。

## 三、⚠️ 诚实标注（别当成"都录进去了"）

1. **视频是无声的** —— Android `screenrecord` 不录内部音频（本机 Help 无 `--audio` 选项）。视频只录了**屏幕**：出卡、两条通知叠起来、app 里"到点提醒"那行字。**"出声"由上面的 TTS 引擎日志作证**，不是靠视频听出来的。
2. **演示用了压缩计时** —— 真产品按卡里的 `when`（"明早八点"）到点；演示为了让评委当场看到，钉卡后 **~5 秒**就触发一次。（`main.splash` 里 `pending_left` 的初值就是压缩系数。）
3. **TTS 是 Android 系统自带引擎**（本机 MIUI 的 `com.xiaomi.mibrain.speech`），**不是 33OS、也不依赖任何自有语音资产** ⇒ 不碰 33OS 红线、换机即用。
4. **复赛期已并入公开仓**（2026-10-09）：D1 进 `octos/apps/shiyi/bundle/main.splash`（`os.shiyi` 0.2.0→**0.2.1**），D2 进 `octos/host-extension/speak_host_extension.patch`。※ 本目录即证据原件的仓内副本（原件首录于 2026-10-08，彼时按令未推仓）。

## 四、文件

| 文件 | 是什么 |
|---|---|
| `d1_evidence.mp4` | 42s 无声录屏：冷启动→拾意→打字→造卡→出卡通知→**到点提醒通知** |
| `tts_logcat.txt` | 关键 logcat：两次 `speak:` + 引擎"收单/合成/播完"全过程 |
| `key_frames/01_publish_notify.png` | 钉卡那一刻：顶部"周日早上九点去菜市场买菜"通知 |
| `key_frames/02_reminder_notify.png` | 到点那一刻：顶部叠出"**该动身了 ·** …"通知（在原来那条之上） |

## 五、复现

```bash
# 装：自编 OctoSense Home APK（含 liboctos.so 内核 + 拾意 bundle）
adb install -r -d <OctoSense 构建树>/phone/target/android/makepad-android-apk/octosense_home/apk/octo_sense.apk
# 录：脚本把流程走一遍并抓 TTS 引擎日志（录屏脚本随宿主构建树提供）
MSYS_NO_PATHCONV=1 bash <宿主构建树>/_probe/speak/d1_record.sh
```
