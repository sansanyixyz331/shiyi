# octos/ — 助手「原地改卡」的宿主扩展（不碰官方内核）

这一目录**不进提交包**（不在 `bundle/` 里）。它装的是：让「拾意」的**卡片对话**从
**「只能聊」变成「能改卡」**所需的宿主侧文件，以及**双端真机已跑通的实证**。

> **一句话**：给拾意挂一个它自己的工具 **`shiyi.repin`**（官方预留的扩展点，`implemented_by:"host-service"`），
> 助手在卡的对话里就能把你钉的那张卡**原地改掉** —— 模型自己选工具、传参数，卡被替换成新内容。
> **没碰 octos 内核一行**（走的是官方 Calendar / News / Mail 成卡工具的**同一条路**）。

---

## 1. 为什么需要它（问题 → 做法）

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
| `apps/shiyi/bundle/main.splash` | 已有 | 拾意的造卡 app（**未改**，repin 复用活卡的 L0 源码） |
| `apps/shiyi/bundle/manifest.json` | 已有 | 系统 app 清单（`bundle_blake3` 留空，构建期由 `pack_system_app` 自动盖章） |
| `crates/shell/src/shiyi.rs` | **新增** | 拾意的 host service。`repin(app,args)`：从**活卡**取 L0 源码**原样复用**（模型只改数据、不改卡代码），只换 `rec` 数据 → `crate::glance::publish_for("os.shiyi", &publish)`。含 2 单测 |
| `crates/shell/src/lib.rs` | **修改** | 加 `pub mod shiyi;`（`:90`） |
| `crates/shell/src/apps.rs` | **修改** | `register_host_services()` 加 `crate::shiyi::register();`（`:228`，在 `glance_notice::serve_system_apps()` 兜底之前） |

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
octos/      ← 备件：接 OctoSense 本体、让助手「能改卡」的宿主扩展 ★本目录
```

**提交物最小、最能开；深度能力在备件里，随宿主就绪合入。**
