#!/usr/bin/env bash
# 拾意 · OctoSense 宿主扩展 —— 一键构建脚本（可构建版本 + 复现说明）
#
# 目的：把本作品对 OctoSense 宿主的扩展一键应用到官方源码，并编译出
#       「会说话、手机通知不遮控件」的宿主（桌面 exe / 安卓 APK）。
#
# 基线：官方 OctoSense-org/OctoSense（干净源，见本目录 README.md 的修订说明）。
# 用法：
#   bash build_host.sh /path/to/OctoSense            # 桌面：打补丁 + 编 octosense
#   bash build_host.sh /path/to/OctoSense --apk      # 额外：重打安卓 APK（含内核）
#
# 补丁 speak_host_extension.patch 现含【全部宿主扩展】（共 6 个文件）：
#   ① 语音（D2，"拾意会说话"）
#        glance.rs            —— GlanceNote 加 speak 字段（默认 true，可从 args 关）
#        lib.rs               —— glance_notify 里对 os.shiyi 调 android_speak
#        android_integration.rs —— 新增 android_speak（非 Android 空操作）
#        MakepadAppExtension.java —— 新增 speakText（Android 系统 TextToSpeech）
#   ② repin host-service（"拾意原地改卡"）
#        crates/shell/src/shiyi.rs（新增文件，一次 apply 即建）
#        lib.rs               —— `pub mod shiyi;`
#        apps.rs              —— `crate::shiyi::register();`
#   ③ 本地时区修复
#        lib.rs               —— local_utc_offset_secs()（否则卡片盖 UTC 时间戳）
#   ④ 手机端通知修复（0.3.6）
#        lib.rs               —— glance_notify 只在桌面弹 toast；手机屏窄，桌面式
#                                toast 会压住控件，改走系统通知中心（shade）
#   ⇒ 一次 apply 即得到与作者构建树【逐字节一致】的宿主源码。
#
# 说明：
#   - 脚本【不修改】官方仓库任何历史，只在工作区 apply 补丁。
#   - 用 `git -c core.autocrlf=false apply`：否则 Windows 上 git 会把行尾转成
#     CRLF，与作者构建树（LF）不一致。
#   - 若 patch 已应用，脚本跳过并继续。
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OCTOS="${1:-}"
WITH_APK=0
for a in "$@"; do [ "$a" = "--apk" ] && WITH_APK=1; done

if [ -z "$OCTOS" ] || [ ! -d "$OCTOS/crates/shell" ]; then
  echo "用法: bash build_host.sh /path/to/OctoSense [--apk]" >&2
  echo "错误: 未给出官方 OctoSense 源码目录（应含 crates/shell/）" >&2
  exit 2
fi

echo "==> [1/3] 校验并应用宿主扩展补丁：$OCTOS"
if git -C "$OCTOS" -c core.autocrlf=false apply --check "$HERE/speak_host_extension.patch" 2>/dev/null; then
  echo "    补丁可应用 —— 开始应用"
  git -C "$OCTOS" -c core.autocrlf=false apply "$HERE/speak_host_extension.patch"
  echo "    ✅ 宿主扩展（语音 + repin + 时区 + 手机通知修复）已应用"
elif git -C "$OCTOS" -c core.autocrlf=false apply --check --reverse "$HERE/speak_host_extension.patch" 2>/dev/null; then
  echo "    补丁似乎已应用（反向可应用）—— 跳过"
else
  echo "    ❌ 补丁既不能应用也不能反向应用：源版本可能不符（请用本目录 README 说明的官方修订）" >&2
  exit 3
fi

echo "==> [2/3] 编译桌面宿主 octosense（含 os.shiyi 系统 app）"
( cd "$OCTOS" && cargo build --release -p octosense )
echo "    ✅ 桌面产物：$OCTOS/target/release/octosense(.exe)"
echo "    运行：MAKEPAD_REMOTE=8399 OCTOSENSE_HOME=<data> $OCTOS/target/release/octosense(.exe)"

if [ "$WITH_APK" = "1" ]; then
  echo "==> [3/3] 重打安卓 APK（含内核 liboctos.so + shiyi）"
  if [ -x "$OCTOS/phone/build_octosense_apk_kernel.sh" ]; then
    ( cd "$OCTOS" && ./phone/build_octosense_apk_kernel.sh )
    echo "    ✅ APK 见 $OCTOS/phone/target/android/.../octo_sense.apk"
  else
    echo "    ⚠️ 未找到 phone/build_octosense_apk_kernel.sh —— 请确认 phone/ 子工程存在（官方手机变体）"
  fi
else
  echo "==> [3/3] 跳过 APK（未传 --apk）"
fi

echo
echo "完成。链路：os.shiyi 通知 → glance_notify() → 桌面弹 toast / 手机 TTS + 通知中心。"
echo "边界：输出侧只说不听；用 Android 系统 TTS；不改内核一行；手机端不弹桌面式 toast。"
