# 生成器 MVP —— 「意图即卡」

> 状态：**跑通（2026-10-04）**。从一条消息出发，「识别 → 组装 → 排版 → 产包 →
> 渲染 → 过官方门禁」全链自动走通。这是复赛「任务自动化 + 技术突破」的地基，
> 也是本项目从「一张卡」往「一个会造卡的机器」走的第一步。

## 它做什么

输入一条聊天消息，输出一个**能过官方 `hub check` 的 L0 卡 bundle**：

```
build/gen_l0.py
   │
   ├─ 1) 识别      src/intent_card.py  → 时间 / 地点 / 类型 / 记忆命中 / 待问项 / 来源
   ├─ 2) 组装      按识别结果决定：渲染哪些行、每行说什么、问设备助手什么
   ├─ 3) 排版      行数变了，每个节点的 box(y) 跟着重排 —— 不重叠、不溢出
   ├─ 4) 产包      page.card + page.data.json + manifest.json + listing.json + bindings.json
   └─ 5) 自检      tools/l0_bindings_lint.py  → 不过关就非零退出
```

注意：**这不是"填模板"**。同一个引擎，换一条消息，长出来的行数、每行文案、
节点数、以及**问 AI 的那句话**都不一样。

## 为什么是"生成"而不是手写

官方文档（App Design Flow）自己就写着：**不要手写 L0**。手写是我们在初赛阶段的
权宜（也是我们吃透规则的方式）；复赛要的「任务自动化」，就是把这条手工链路换成
机器链路——而**识别的能力我们本来就有**（`src/intent_card.py` 早就写好），
缺的只是把它接到 L0 的产出上。这就是"能力换环境"。

## 证据（本地可复跑）

```
python build/gen_l0.py --samples --out build/_gen        # 三条样例消息
```

三条消息 → 三张**不同**的卡：

| 消息 | 识别 | 生成结果 |
|---|---|---|
| 下周三我得去趟深圳 | trip · 时间+地点 | 3 行字段 + **3 条记忆行**（不坐飞机/只给高铁/周三下午不排事）+ 问「排成一次行程」 |
| 明天下午三点跟老王在杭州碰一下 | meeting · 时间+地点 | 3 行字段 + **无记忆行** + 问「定成一次会面」 |
| 帮我把那个快递寄到上海 | errand · 仅地点 | **2 行字段（无时间）** + 追问行「这事安排在哪天？；「那个」指的是哪一个？」 + 问「把它办掉」 |

三张都：`l0-bindings-lint` **0 error**；官方 Linux `hub check` **PASSED**。

## 渲染与门禁（`build/shot_bundle.py`）

`card-host` 自带 instrument 端口，把它画的那一帧直接吐出来（`/g?raw=1`），
所以抓图不依赖 X11 截屏。跑一次即得真实截图：

```
python build/shot_bundle.py build/_gen/01/bundle         # → bundle/screenshots/01.png
```

截图进包后，`hub check` 从 REFUSED 变 **PASSED**。

> ⚠️ 一个坑：`hub stamp` 与 `hub check` **必须在同一平台**做。Windows 的 `hub`
> 与 Linux 的 `hub` 对同一 bundle 算出的 `bundle_blake3` **不同**（Windows 路径
> 处理的老问题，与我们报给官方的 #75 同源）。官方判据环境是 Linux，所以**最终
> 用 Linux 的 `hub` stamp + check**（本机走 WSL）。

## 边界（照实）

- 现在做的是**「结构化意图 → 组件库组装」**，不是"任意意图 → 任意 UI"。
  官方自己的 App Studio（ADR 0006）也分里程碑，没有一步到位。
- 覆盖的是**单屏确认卡**；五屏流转（`cards/`）仍是手写的，生成器尚未接管。
- 生成器**不产出提交物**：它是工具，产出物在 `build/_gen/`（已 ignore）。
  `bundle/`（冻结的初赛提交物）与 tag `v0.3.1` **一字节不动**。

## 文件

| 文件 | 作用 |
|---|---|
| `build/gen_l0.py` | 生成器：意图 → bundle |
| `build/shot_bundle.py` | 给任意 bundle 抓真实截图（card-host --remote） |
| `src/intent_card.py` | 识别引擎（生成器的大脑，早已存在） |
| `tools/l0_bindings_lint.py` | L0 卡校验（生成器的自检闸） |
