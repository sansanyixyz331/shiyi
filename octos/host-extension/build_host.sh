#!/usr/bin/env bash
# 拾意 · OctoSense 宿主扩展 —— 一键构建脚本（可构建版本 + 复现说明）
#
# 目的：把本作品对 OctoSense 宿主的三处扩展（D2 语音；另含 repin host-service）
#       一键应用到官方源码，并编译出「会说话」的宿主（桌面 exe / 安卓 APK）。
#
# 基线：官方 OctoSense-org/OctoSense（干净源）。
# 用法：
#   bash build_host.sh /path/to/OctoSense            # 桌面：打补丁 + 编 octosense.exe
#   bash build_host.sh /path/to/OctoSense --apk      # 额外：重打安卓 APK（含内核）
#
# 说明：
#   - 补丁 host-extension/speak_host_extension.patch 里【只含语音】（D2）；
#     repin host-service（crates/shell/src/shiyi.rs + 两处注册）随本目录一并附上，
#     由 --with-repin 选择一起应用（默认开启，因作品完整形态含它）。
#   - 脚本【不修改】官方仓库任何历史，只在工作区 apply 补丁。
#   - 若 patch 已应用，脚本跳过并继续。
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OCTOS="${1:-}"
WITH_APK=0
WITH_REPIN=1
for a in "$@"; do [ "$a" = "--apk" ] && WITH_APK=1; [ "$a" = "--speak-only" ] && WITH_REPIN=0; done

if [ -z "$OCTOS" ] || [ ! -d "$OCTOS/crates/shell" ]; then
  echo "用法: bash build_host.sh /path/to/OctoSense [--apk] [--speak-only]" >&2
  echo "错误: 未给出官方 OctoSense 源码目录（应含 crates/shell/）" >&2
  exit 2
fi

echo "==> [1/4] 校验补丁可干净应用：$OCTOS"
if git -C "$OCTOS" apply --check "$HERE/speak_host_extension.patch" 2>/dev/null; then
  echo "    补丁可应用 —— 开始应用"
  git -C "$OCTOS" apply "$HERE/speak_host_extension.patch"
  echo "    ✅ 语音扩展（D2）已应用"
elif git -C "$OCTOS" apply --check --reverse "$HERE/speak_host_extension.patch" 2>/dev/null; then
  echo "    补丁似乎已应用（反向可应用）—— 跳过"
else
  echo "    ❌ 补丁既不能应用也不能反向应用：源版本可能不符（请用官方 HEAD 或说明的修订）" >&2
  exit 3
fi

if [ "$WITH_REPIN" = "1" ]; then
  echo "==> [2/4] 应用 repin host-service（拾意原地改卡）"
  mkdir -p "$OCTOS/crates/shell/src"
  cp "$HERE/shiyi.rs" "$OCTOS/crates/shell/src/shiyi.rs"
  echo "    ✅ 已放入 crates/shell/src/shiyi.rs（请确认 lib.rs 的 'pub mod shiyi;' 与 apps.rs 的注册已随语音补丁一并生效）"
else
  echo "==> [2/4] 跳过 repin（--speak-only）"
fi

echo "==> [3/4] 编译桌面宿主 octosense（含 os.shiyi 系统 app）"
( cd "$OCTOS" && cargo build --release -p octosense )
echo "    ✅ 桌面产物：$OCTOS/target/release/octosense(.exe)"
echo "    运行：MAKEPAD_REMOTE=8399 OCTOSENSE_HOME=<data> $OCTOS/target/release/octosense(.exe)"

if [ "$WITH_APK" = "1" ]; then
  echo "==> [4/4] 重打安卓 APK（含内核 liboctos.so + shiyi）"
  if [ -x "$OCTOS/phone/build_octosense_apk_kernel.sh" ]; then
    ( cd "$OCTOS" && ./phone/build_octosense_apk_kernel.sh )
    echo "    ✅ APK 见 $OCTOS/phone/target/android/.../octo_sense.apk"
  else
    echo "    ⚠️ 未找到 phone/build_octosense_apk_kernel.sh —— 请确认 phone/ 子工程存在（官方手机变体）"
  fi
else
  echo "==> [4/4] 跳过 APK（未传 --apk）"
fi

echo
echo "完成。语音链路：os.shiyi 通知 → glance_notify() → android_speak → Java TextToSpeech。"
echo "边界：输出侧只说不听；用 Android 系统 TTS；不改内核一行。"
