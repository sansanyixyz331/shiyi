# Rinx 宿主改造补丁包

> 生成：2026-10-13 03:4x
> 上游基线：`hagency-org/Rinx` @ `f18869e`；依赖 `OctoSense-org/makepad` @ `1f3b1ded`
> 用途：**官方原版 + 打上这三个补丁 = 复现我们演示时那套体验**（可审、可溯源、可回馈上游）

---

## 零、想复现的人怎么用（三条路，随便挑一条）

> **跑起来不需要打补丁。** 打补丁只在你想自己编译时才需要。

| 你想干什么 | 走哪条路 | 要几个动作 |
|---|---|---|
| **只想看到那个体验** | 用我们**已编译好的桌面成品**（免安装） | **解压 → 双击**（零配置、零编译、零打补丁） |
| 用**官方原版宿主**跑我们的作品 | 装官方 Rinx，导入作品包 | 功能全通 —— 只是界面还是官方原样（不好看、要手填路径和房间 ID） |
| 想自己编译 / 审我们改了什么 | 官方源码 + 本补丁包（01 + 02 + 03） | 打补丁 → 编译（费时，工具链要求高） |

**为什么成品和补丁都给**：成品让只是想看看的人零门槛；补丁让想审的人看得见我们到底改了什么。
**为什么不会有卡住的风险**：我们的作品在**官方原版宿主上照样能跑全部功能**，改造只是把上手难度从装不上降到双击就能用。所以——**不打补丁也跑得通，打了补丁才是我们演示的那个体验。**

---

## 一、三个补丁各是什么

| 文件 | 改什么 | 涉及文件 | 规模 |
|---|---|---|---|
| `01-rinx-windows-build-path.patch` | Windows 上的构建与运行路径说明 | `README.md`、`packaging/README-octos.md` | 58 行 |
| `02-rinx-host-usability-and-services.patch` | **① 可用性改造**（列表区分自带/导入、导入应用常驻可删可改、「打开 / 修改 / 删除」三个按钮、房间选择挪进应用界面、路径自适应、浅色主题、中英双标、资源查找）**② 三项宿主服务**（`rinx.schedule` 到点排程 / `rinx.notify` 系统通知 / `rinx.speak` 念出来）**③ 跨平台完整性摘要修复**（路径分隔符统一，避免同一份 bundle 在桌面与安卓算出两个摘要）**④ 安卓侧原生实现**（通知 + TTS + 清单权限） | 8 个 | 1,113 行 |
| `03-makepad-portable-resource-lookup.patch` | 便携包场景的资源查找兜底：图标、字体在「换一台机器解压运行」时也能找到 | `platform/src/script/res.rs`、`platform/src/cx_api.rs` | 61 行 |

**为什么分两层**：01/02 是 Rinx 仓库内的改动；03 改的是**它引用的 makepad 依赖**。只打 01/02 而漏了 03，编译出来的程序会**图标不显示、中文字体缺失**。

---

## 二、怎么打

```bash
# ① Rinx（在 Rinx 仓库根目录）
git checkout -b host-usability f18869e
git apply --ignore-whitespace 01-rinx-windows-build-path.patch
git apply --ignore-whitespace 02-rinx-host-usability-and-services.patch

# ② makepad（在 makepad 仓库根目录；Rinx 经 Cargo.toml 的 git rev 引用它）
git checkout -b portable-resource-lookup 1f3b1ded
git apply --ignore-whitespace 03-makepad-portable-resource-lookup.patch
```

> **为什么加 `--ignore-whitespace`**：上游仓库各文件行尾并不统一（部分 LF、部分 CRLF），该开关只忽略**行尾空白差异**，不改内容。若你手上的检出是纯 LF，也可以不加。
>
> 两个补丁已在**干净的上游检出**上实测 `git apply --check` 通过（01 默认模式通过；02、03 加 `--ignore-whitespace` 通过）。

---

## 三、打完能得到什么

1. **图标与中文字体**在换机器解压运行时正常加载（03）
2. 「小应用」页**区分自带应用与你导入的应用**；导入过的应用**常驻列表**、可「删除 / 修改」，点「打开」**直接进入应用**；读取哪个聊天**在应用界面里随时切换**（02）
3. **到点提醒**可弹系统通知、可用系统语音念出来（02 的三项宿主服务）
4. 同一份 bundle 在**桌面与安卓**上得到**一致的完整性摘要**（02 的路径分隔符规范化）

---

## 四、不想自己编译？

编译 Rinx（Rust + makepad）成本高。我们另外提供**已编译好的桌面成品**（免安装、解压即用），走发布附件单独分发，不占仓库体积。

---

## 五、许可与归属

- **Rinx** —— `hagency-org/Rinx`（包名 `org.octosense.rinx`），**Apache-2.0 与 MIT 双许可**
- **makepad** —— `OctoSense-org/makepad`
- 本补丁是在上述项目之上的**增量改动**，不改变其许可与署名；随附引用请保留原项目的 LICENSE 与 NOTICE。

---

## 六、生成方式（可复现）

三个补丁均对**上游基线**生成（`git diff --ignore-cr-at-eol`，只留实质改动、不混行尾噪声），并统一为纯 **LF**（跨平台 `git apply` 更稳）。
