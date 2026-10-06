# 快览屏（glance）—— 拾意做成 OctoSense 系统 app 的底层实证

> 这是**第三条交付面**（`octos/` 系统 app）**最底层**的一段：拾意被做成 OctoSense 的
> **原生 system app**（`os.shiyi`），卡**钉进系统快览屏（glance）**、和应用同生命周期。
> 上面还有个「助手原地改卡」的能力，见 [`../repin/`](../repin/README.md)。
> 全部为本机实测原始输出（2026-10-06，Windows）。**可逐条复跑核验。**

---

## 1 · 一句话

你说一句话，拾意当场做成一张**结构化卡片**钉到系统**快览屏**；多说几句就有多张卡常驻，
**关掉应用再打开还在**（落盘），随时可重钉或撤掉。

不是"演示概念"——它接的是 OctoSense **官方 shell 真实存在的 `glance` host service**
（`glance.publish / withdraw / list`），**不是自搭仿真**。

---

## 2 · 拾意已注册为**官方同级 system app**

启动日志：

```
[I] crates\shell\src\apps.rs:228:9 - glance: the notice service answers
    ["os.photos", "os.maps", "os.ai-providers", "os.youtube", "os.shiyi"]
[I] crates\shell\src\lib.rs:2614:9 - wm: launched shiyi as client 1 (in-process, card)
[I] ...appstore\src\cardapp.rs:111:9 - card: os.shiyi running under 2 capability(ies),
    1 host(s), 67108864 bytes of storage, 4000000000 instructions, 134217728 bytes of heap
[I] ...makepad\widgets\src\splash.rs:414:9 - [SPLASH] eval: 12631 bytes preserve=false view=true
```

- 与官方 `os.photos / os.maps / os.ai-providers / os.youtube` **并列**在同一个 notice 服务表里；
- **`running under 2 capability(ies)`** = 只声明了 `["storage","glance"]`，按官方能力表授权；
- `[SPLASH] eval: 12631 bytes` = 脚本（236 行）加载**无语法错误**。

---

## 3 · 端到端演示（一键脚本原始输出）

```
pin 下周三去深圳见客户      -> 已钉到快览屏 —— 按 F9 看
pin 明天上午10点和法务对合同 -> 已钉到快览屏 —— 按 F9 看
pin 周五下午3点给团队做分享  -> 已钉到快览屏 —— 按 F9 看
pinned : 快览屏上现在有 3 张（和我记的对得上）
rows   : [{'text': '下周三去深圳见客户',    'meta': '时间 · 下周三      地点 · 深圳        · 钉于 2026-10-6 12:42'},
          {'text': '明天上午10点和法务对合同', 'meta': '时间 · 明天上午10点  地点 · 这句话里没提 · 钉于 2026-10-6 12:42'},
          {'text': '周五下午3点给团队做分享',  'meta': '时间 · 周五下午3点  地点 · 这句话里没提 · 钉于 2026-10-6 12:42'}]
panel  : True | state: wm: glance panel open
```

**读法**：三句全部成功钉卡；应用**如实回报**"3 张（和我记的对得上）"；应用内 3 张卡的
**结构化字段**（时间 / 地点）都在；**时间戳为本地时间 `12:42`**；系统快览屏面板被打开。

---

## 4 · 落盘（应用自己的记账，持久）

`<OCTOSENSE_APP_DATA>/os.shiyi/picks.json`：

```json
{ "seq": 3,
  "picks": [
    { "id": "shiyi-p1", "text": "下周三去深圳见客户",     "when": "下周三",       "where": "深圳", "at": "2026-10-6 12:42" },
    { "id": "shiyi-p2", "text": "明天上午10点和法务对合同", "when": "明天上午10点", "where": "",     "at": "2026-10-6 12:42" },
    { "id": "shiyi-p3", "text": "周五下午3点给团队做分享",  "when": "周五下午3点",  "where": "",     "at": "2026-10-6 12:42" } ] }
```

`when_of()` / `where_of()` 从原句里**结构化地**抽出时间与地点——
`明天上午10点和法务对合同` 里确实没提地点 ⇒ **如实留空，不编**。

---

## 5 · 持久化：**关掉再开，还在**

重启 shell（同一 `OCTOSENSE_APP_DATA`）后：

```
重启后 pinned: 快览屏上现在有 0 张          ← 快览屏随之清空（宿主行为）
重启后 rows  : 3 张卡从 picks.json 读回，时间戳仍是 12:42
```

- **应用数据存活**：3 张卡从 `picks.json` 读回。
- **诚实**：快览屏空了就报 **0 张**，且**不加**"（和我记的对得上）"——**不谎报一致**。

---

## 6 · 同 id 再发 = 原地替换（不重复建卡）—— 宿主回执佐证

`glance` 按 `(app, card_id)` 键控。同一句话再钉时命中相同 key ⇒ 走 `publish(..., replaced=true)`：
**面板卡数不变、卡内容原地更新**，不新增第 4 张。

```
三张钉完 -> 3 card(s) shiyi@1031,98  shiyi@1031,283  shiyi@1031,468
重钉     -> 已更新（换掉了原来那张） —— 按 F9 看
重钉后   -> 3 card(s) shiyi@1031,98  shiyi@1031,283  shiyi@1031,468     ← 仍是 3 张
```

其中"**（换掉了原来那张）**"**不是我们自己写的**，而是**宿主回执字段**触发的：

```splash
host.request("glance.publish", args, fn(r){
    if r.is_ok {
        let rep = ""
        if r.data.replaced == true { rep = "（换掉了原来那张）" }   // ← 服务侧告诉我们"替换了"
        show(done_msg + rep + " —— 按 F9 看")
    } else { show("没能钉上：" + r.error) }
    refresh()
})
```

⇒ **是快览屏服务自己报告了"原地替换"**，不是应用单方面声称。

---

## 7 · 截图与录屏证据

| 文件 | 看什么 |
|---|---|
| `01-app-list-3cards.png` | 应用内：3 张常驻卡**完整可见**（标题＋时间/地点＋右侧「重钉/撤掉」同排），顶部回报"3 张（和我记的对得上）" |
| `02-glance-3cards.png` | 系统快览屏：`At a glance — 3 cards from your apps`，3 张卡带来源「拾意」＋时间戳＋两行字段 |
| `03-after-restart.png` | **重启后**列表仍 3 张（从 `picks.json` 读回） |
| `desktop_glance_end_to_end.mp4` | 桌面 shell **全流程录屏 53s**：空列表 → 3 句依次造卡 → 快览屏 `3 card(s)` → 同 id 重钉仍 3 张（原地替换）；卡上「钉于」为**本地时间** |
| `04-phone-app.png` | 小米13 真机：拾意应用界面 |
| `05-phone-grid.png` | 小米13 真机：app 网格 |
| `06-phone-2cards.png` | 小米13 真机：2 张卡常驻 |
| `phone_glance_demo.mp4` | 小米13 真机录屏 **26s** |

> **录屏口径（如实说明）**：`desktop_glance_end_to_end.mp4` 与本目录截图录于
> **2026-10-06 13:08**，早于当天 15:53 落码的「助手原地改卡」（那条线的真录屏见
> [`../repin/`](../repin/README.md)）。本段录的是 **glance 集成**这一段链路本身。

---

## 8 · 复现（从零）

**环境**：Windows + Rust 隔离工具链（见 [`../../octos/README.md`](../../octos/README.md) §2）。

```bash
# 1) 编官方 shell（含打包拾意为 system app）
cargo build --release -p octosense

# 2) 启动即打开拾意（开遥控口，便于取证）
OCTOSENSE_APP_DATA=<app 存储根> MAKEPAD_REMOTE=8399 ./target/release/octosense.exe --test-action launch-shiyi

# 3) 钉卡
#    F9 关掉快览屏面板 -> 点输入框 -> 打一句话 -> 点「造卡 · 钉到快览屏」
#    再钉两句 = 3 张常驻；同一句再钉 = 原地更新（不新增）
```

日志出现 `glance: os.shiyi published shiyi` 即成功。

---

## 9 · 诚实边界（一并交代）

- 桌面 shell 点卡只 `launch_app`、**不透传 `route`** ⇒ "点哪张卡 → 应用定位到哪条"目前走不通。
- 每 app 快览屏**上限 4 张卡**；发布**限流 6 次/60 秒**。
- 应用窗口尺寸由官方 shell 固定（`990×602`），**不可调**；界面按此尺寸做过紧凑化，
  **4 张卡刚好放得下**（把「重钉/撤掉」并进 meta 行，每卡 3 行→2 行）。
- 快览屏内容**随 shell 重启清空**（宿主行为）；**应用自己的记账是持久的**，
  重启后会如实报"快览屏 0 张"，**不谎称"对得上"**。
