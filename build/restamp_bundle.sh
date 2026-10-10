#!/usr/bin/env bash
# 一键重盖章：重算 bundle_blake3 + 重新签名 + 门禁校验
#
#   用法:  bash build/restamp_bundle.sh <bundle-dir>
#
# 为什么要有这个脚本（2026-10-08）:
#   ① 官方把 bundle 摘要算法改成了跨平台可移植（PR #79，已合并 10-07）。
#      旧的 "legacy Windows digest" 会被 gate 故意拒收。我方一直用 WSL 里的
#      官方 Linux hub 盖章，算法本就正确 —— 但要把这条流程固定下来，别靠记忆。
#   ② 规矩：**每次改完 bundle 内容，必须重盖章、重签名**（AGENTS.md 亦如此要求）。
#      内容改过而摘要不重算 = 包校验对不上 = 提交会被拒。
#   ③ 血的教训：任何临时文件（如 manifest.json.bak）**绝不能放进 bundle 目录**，
#      否则 hub check 直接 REFUSED（"bundle may not hold"）。本脚本先做游离文件自检。
#
# 签名私钥**不入库**：请自行保管，用环境变量 KEY 指过来（见下）。
set -euo pipefail

# 两个环境变量都必须由使用者提供，脚本里不写死任何本机路径 ——
#   HUB = 官方 App Hub 工具（hub / hub.exe）的路径
#   KEY = 你的签名私钥路径（**不入库**）
HUB="${HUB:?请设置 HUB=/path/to/hub（官方 App Hub 工具）}"
KEY="${KEY:?请设置 KEY=/path/to/your_signing_key（私钥，自行保管）}"
KEY_ID="${KEY_ID:-sansanyixyz331}"

B="${1:-}"
[ -n "$B" ] && [ -d "$B" ] || { echo "用法: restamp_bundle.sh <bundle-dir>"; exit 1; }
[ -f "$KEY" ] || { echo "找不到私钥: $KEY"; exit 1; }
[ -x "$HUB" ] || [ -f "$HUB" ] || { echo "找不到 hub: $HUB"; exit 1; }

# 0) bundle 目录只许放规范内文件：站外的临时文件会让 check 直接拒
ALLOW='-name manifest.json -o -name listing.json -o -name page.card -o -name page.data.json -o -name main.splash -o -name tools.json'
STRAY=$(find "$B" -maxdepth 1 -type f ! \( $ALLOW \) -print || true)
if [ -n "$STRAY" ]; then
  echo "[STOP] bundle 目录里有规范外文件，先挪出去再盖："
  echo "$STRAY" | sed 's/^/   /'
  exit 2
fi

export MSYS_NO_PATHCONV=1
OLD=$(grep -o '"bundle_blake3": "[^"]*"' "$B/manifest.json" | head -1 || true)
echo "== restamp: $B"
echo "   旧摘要: ${OLD:-（空）}"

echo "-- 1/3 stamp"
"$HUB" stamp "$B"
NEW=$(grep -o '"bundle_blake3": "[^"]*"' "$B/manifest.json" | head -1)
echo "   新摘要: $NEW"

echo "-- 2/3 sign-manifest ($KEY_ID)"
"$HUB" sign-manifest "$B" --key "$KEY" --key-id "$KEY_ID"

echo "-- 3/3 check"
PUB=$("$HUB" pubkey "$KEY" | tr -d '\r\n')
"$HUB" check "$B" --publisher-key "$KEY_ID=$PUB"

echo "== done. 若要回滚：manifest.json 的 integrity 段改回上面的旧摘要即可。"
