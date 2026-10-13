# 安卓安装与试用（现成安装包）

本目录给的是**能直接装上试的安卓包**，以及配套的**拾意应用包**。

- 官方仓库的构建流水线**只产出桌面版**；安卓版需要自己编（步骤见 [`../docs/手机端复现说明.md`](../docs/手机端复现说明.md)）。
- 我们已经把它编出来了，并在**真机（小米 13 / Android 13 / arm64-v8a）上端到端跑通** —— 手机演示片就是用这个包跑的。
- 想省掉编译，走下面「一、最快路径」。

## 本目录文件

| 文件 | 是什么 |
|---|---|
| `shiyi-rinx-android-1.1.0-ai-arm64-v8a.apk.part1` / `.part2` | **宿主安装包**（Rinx 1.1.0，内含 AI 内核），分两卷 |
| `shiyi-live-0.8.6-rinx-bundle.zip` | **拾意应用包**（交给宿主导入） |
| `shiyi-live-rinx.manifest.json` | 上面那个应用包的清单（便于直接查看能力声明） |
| `SHA256SUMS.txt` | 校验值 |

---

## 一、最快路径（不编译，直接装）

### 1. 先把两卷合并成一个 APK

Linux / macOS：

```bash
cat shiyi-rinx-android-1.1.0-ai-arm64-v8a.apk.part1 \
    shiyi-rinx-android-1.1.0-ai-arm64-v8a.apk.part2 \
    > shiyi-rinx-android-1.1.0-ai-arm64-v8a.apk
sha256sum shiyi-rinx-android-1.1.0-ai-arm64-v8a.apk
```

Windows（命令提示符）：

```bat
copy /b shiyi-rinx-android-1.1.0-ai-arm64-v8a.apk.part1+shiyi-rinx-android-1.1.0-ai-arm64-v8a.apk.part2 shiyi-rinx-android-1.1.0-ai-arm64-v8a.apk
certutil -hashfile shiyi-rinx-android-1.1.0-ai-arm64-v8a.apk SHA256
```

**期望结果**（对不上就别装）：

- 大小 **128670020 字节**（122.71 MB）
- sha256 **`1d92030484bd2cedf8fc794afc2250d681e185b6a8f445f8a1306f5dd85e8fe3`**

> 权威校验清单以本目录 [`SHA256SUMS.txt`](SHA256SUMS.txt) 为准（含两卷各自的校验值）。

> **为什么是分卷**：安装包 122.7 MB，**超过 GitHub 单文件 100 MB 的上限**，不能作为整文件放进仓库。
> 因此切成两卷（64.00 MB + 58.69 MB），每一卷都在限制以内。合并后必须就是上面那个整包。

### 2. 装到手机

- 系统要求：**Android 8.0 及以上**（`minSdk 26`，`targetSdk 35`）
- 架构要求：**arm64-v8a**（x86 模拟器、32 位手机装不上）
- 允许「未知来源」安装（该包用**调试证书自签名**，会弹「未知发布者」提示，正常）
- 命令行安装：`adb install -r shiyi-rinx-android-1.1.0-ai-arm64-v8a.apk`
- 如果手机上**已经装过**同包名（`org.octosense.rinx`）且签名不同，会装不上 —— 先卸载旧的再装

### 3. 把应用包放进手机

把 `shiyi-live-0.8.6-rinx-bundle.zip` 解压，得到文件夹 `shiyi-live-0.8.6-rinx/`，
整个文件夹拷贝到手机上一个**应用读得到的位置**，例如：

```
/sdcard/Download/shiyi-live-0.8.6-rinx
```

### 4. 在宿主里导入并运行

1. 打开 **Rinx**
2. 进入 **Mini apps（小应用）→ 导入**
3. 路径一栏填上一步那个**文件夹的路径**（例如 `/sdcard/Download/shiyi-live-0.8.6-rinx`）
4. 点 **Review**：应显示 **10 项能力**，其中包含 `matrix.read_messages` / `matrix.profile` / `matrix.send_message` 与 `rinx.notify` / `rinx.speak` / `rinx.schedule`
5. 选一个**房间**绑定（拾意要读那个房间的消息）
6. 点 **Run**

### 5. 验收清单（该看到什么）

| # | 做什么 | 应该看到 |
|---|---|---|
| 1 | 打开应用 | 界面出现「自动读群消息：开」 |
| 2 | 往绑定房间里发一条带时间的话（如「明天上午九点开会」） | 界面出现「群里来了新消息，它自己读到，正在造卡」 |
| 3 | 稍候 | 长出一张卡：标题 / 时间 / 地点 / 提醒时间 / 到时那句话 / 依据，齐全 |
| 4 | 点「确认」 | 卡上出现「已排程 · 到点会念出来」与「已把结果发回群」；**群里真的多一条** |
| 5 | 等到点 | 通知栏弹出提醒 |
| 6 | 再说一句改期（如「那个改到周六」） | 那张卡被**原地改掉**，并留下改动痕迹 |

---

## 二、坑（都写在这里）

1. **单文件超限 ⇒ 分卷**
   整包 122.7 MB > GitHub 单文件 100 MB 上限。所以只能分卷放。**必须先合并、再校验**（校验的是合并后的整包，不是分卷本身）。

2. **只有 arm64-v8a**
   包里只有 `lib/arm64-v8a/`。x86 / x86_64 模拟器、32 位设备装不上。

3. **自签名证书**
   调试证书签名 ⇒ 安装时提示「未知发布者」；与其它签名的同包名应用**不能共存**，要先卸载。

4. **AI 内核在 APK 里**
   安卓版 Rinx 的 AI 走 **APK 内置的 `liboctos.so`**（宿主把它当可执行文件跑，走 stdin/stdout）。
   自己构建时若没把它打进去，应用会报 **`no octos kernel`**，AI 会**如实降级**为本机规则
   （仍能识别类型与时间、卡照出，但没有助手给的标题与提醒建议）。

5. **打包器与宿主必须同一版 makepad**
   否则会出现「**装得上、一碰屏就崩**」。这是我们踩过的坑：同一份源码，用宿主机自带的打包器打出来的包会崩，
   换成宿主自己 pin 的那版 makepad 编出来的打包器就正常。构建时务必对齐版本。

6. **通知与发声需要能力声明**
   安卓包要能弹通知、念出来，应用必须在清单里声明 `rinx.notify` / `rinx.speak` / `rinx.schedule`
   （本目录的 `shiyi-live-rinx.manifest.json` 已含）。首次运行记得授予通知权限。

7. **需要联网**
   读房间消息 / 发回群依赖连接到 Matrix 服务器；离线时「自己打一句话造卡」这条路仍可用（不依赖任何外部服务）。

8. **导入是复制**
   每次导入会在宿主里新建一份副本。改动应用内容后要**重新导入**才会生效。

9. **应用数据位置**
   在 `/data/data/org.octosense.rinx/files/` 下（查看需 root 或 `adb run-as`）。

---

## 三、和仓库根 `bundle/` 的关系（避免误读）

本目录的 `shiyi-live-0.8.6-rinx-bundle.zip` 与仓库根 `bundle/` **是同一份应用、同一份代码**：

- `main.splash`、`listing.json`、图标、截图 —— **逐字节相同**
- 唯一差别在 `manifest.json` 的**能力声明**：
  - 仓库根 `bundle/`：6 项（`storage` / `model` / `octos.session.history` / `matrix.read_messages` / `matrix.profile` / `matrix.send_message`）
  - 本目录这版：多 **4 项** —— `octos.turn.start` + `rinx.notify` / `rinx.speak` / `rinx.schedule`

原因：后面这 4 项由 **Rinx 宿主**提供，**OctoSense 宿主不提供**，所以主提交里不声明。
**主提交**给 OctoSense 宿主用；**本目录这份**给 Rinx 宿主用（也就是官方 Rinx 赛道"本地导入"那条路）。

---

## 四、自己构建

不用现成包、想自己编：见 [`../docs/手机端复现说明.md`](../docs/手机端复现说明.md)。
要点重复一遍：**必须带 AI 内核**、**打包器与宿主同版 makepad**。

---

## 五、版本台账

| 项 | 值 |
|---|---|
| 宿主 | Rinx **1.1.0**（`versionCode 2026101110`，`minSdk 26`，`targetSdk 35`） |
| 宿主内 AI 内核 | `liboctos.so`（aarch64 ELF PIE） |
| 应用 | `shiyi-live` **0.8.6**（`bundle_blake3` = `50404a65871a4fbe50f9b7740b7932d6fdae855164962a7b6b20d76a0f5cb909`） |
| 实测机 | 小米 13（Android 13 / SDK 33 / arm64-v8a） |
| 实测时间 | 2026-10-11 |
