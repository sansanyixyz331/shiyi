# 拾意 · OctoSense 宿主扩展（host-extension）

本目录把「拾意」对 OctoSense 宿主的**全部改动**收成一个补丁 + 一键构建脚本，
任何人都能在**官方干净源**上复现"会说话、手机通知不遮控件"的宿主。

## 文件

| 文件 | 作用 |
|---|---|
| `speak_host_extension.patch` | 宿主扩展补丁（6 个文件；含语音 / repin / 时区 / 手机通知修复） |
| `build_host.sh` | 一键：apply 补丁 → 编桌面宿主（可选 `--apk` 重打安卓包） |

## 基线（补丁针对哪个官方版本）

- 官方源码：`OctoSense-org/OctoSense`。
- 补丁针对**官方源码的一次快照**（2026-10-06）。快照 tar 请按你的 checkout 位置自行准备，本仓不携带。
- 若行号漂移导致 apply 失败，请用 `git apply --3way` 或按补丁逐处手动对照；
  补丁每一处的锚点都是稳定代码（见下）。

## 补丁内容（4 类扩展，共 6 个文件）

1. **语音（D2，"拾意会说话"）**
   - `crates/shell/src/glance.rs`：`GlanceNote` 加 `speak: bool`（默认 true，`glance.publish` 可传 `speak:false` 静音单张）。
   - `crates/shell/src/lib.rs`：`glance_notify` 里 `if note.app=="os.shiyi" && note.speak { self.android_speak(...) }`。
   - `crates/shell/src/android_integration.rs`：新增 `android_speak`（非 Android 是空操作 ⇒ 桌面不发声）。
   - `phone/resources/android/java/dev/makepad/octosense/MakepadAppExtension.java`：新增 `speakText`（`android.speech.tts.TextToSpeech`，只用输出侧、不进 33OS）。
2. **repin host-service（"拾意原地改卡"）**
   - `crates/shell/src/shiyi.rs`：**新增文件**（`shiyi.repin` 工具，让宿主 AI 能原地改卡）。
   - `crates/shell/src/lib.rs`：`pub mod shiyi;`
   - `crates/shell/src/apps.rs`：`crate::shiyi::register();`
3. **本地时区修复**
   - `crates/shell/src/lib.rs`：`local_utc_offset_secs()` + 在 `shell_script_mod` 里
     `set_script_local_utc_offset_secs(...)`。不修则 `std.local_time` 恒为 UTC，卡片盖 UTC 时间戳。
4. **手机端通知修复（0.3.6）**
   - `crates/shell/src/lib.rs`：`glance_notify` 把桌面式 toast 的 `post` 包进
     `if !crate::mobile_navigation::ENABLED { ... }` ⇒ **桌面弹 toast、手机不弹**。
   - 原因：手机屏窄，380 宽、贴右上角的桌面 toast 会几乎铺满顶栏、压住控件，
     误触还会跳进卡片详情页（0.3.5 手机端复测撞到的"通知叠到详情页遮控件"）。
   - 手机的通知本体是下方**系统通知中心**（`mobile_shade.rs` 的 shade），
     下拉可见、点开同一张卡（`mobile_app.rs`），语音播报照旧。

## 复现（命令）

```bash
# 1) 取官方干净源到一个 git 仓库目录
#    （例如 git clone 官方 OctoSense-org/OctoSense，或用上面 tar 的快照）
# 2) 一键构建
bash build_host.sh /path/to/OctoSense            # 桌面宿主
bash build_host.sh /path/to/OctoSense --apk      # 额外重打安卓 APK
```

> 说明：脚本用 `git -c core.autocrlf=false apply`，保证行尾与作者构建树一致（LF）。

## 验证过的一致性（2026-10-10）

在官方 tar 快照上 `git apply` 本补丁后，与作者构建树**逐字节一致**
（`diff -rq crates/shell/src` + Java 文件，忽略构建树里的临时 `.bak`）。

## 边界

- 只改宿主外壳，**不碰内核一行**（无 `liboctos.so`、无模型调用）。
- 语音是**输出侧、只说不听**；用手机自带 TTS，不引入任何外部语音资产。
- 本目录是**可复现材料**，不随作品提交包（`bundle/`）一起交付。
