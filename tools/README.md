# tools/ — 让 L0 卡在**进宿主之前**就被拦住

## `l0_bindings_lint.py`

一个**只读、无依赖**的检查器：给定一个 L0 卡 bundle，检查它的 `bindings.json` 契约是否会在宿主里
**fail closed**（整卡渲不出、或整个应用打不开）。跑法：

```sh
python3 tools/l0_bindings_lint.py <bundle_dir>     # 退出码 0=通过；1=有 ERROR
```

### 为什么需要它

L0 卡接宿主服务（`bindings.json`）有三条**会整卡失败**的坑，官方文档没有、只能靠踩：

1. **卡片引用的名字必须在 `page.data.json` 里预置** —— 首帧在任何调用返回之前就 lower 一遍，
   一条落到不存在名字上的路径会让**整张卡**失败（`unresolved or unsupported kit property`）。
   （注意：**只对"被引用的名字"成立**；一个只用于建会话、从不被卡片读的 target 不预置也无害。）
2. **读 `X.data.*` 的节点必须包在 `when X.is_ok { … }` 里** —— 调用失败时宿主写
   `{"is_ok": false, "error": "…"}`（**没有 `data`**），没有 guard 就**整卡**失败，不是少一行。
3. **`bindings.json` 的形状**：`service` 必须在 `manifest.capabilities`；`target` 必须是顶层数据名
   `[A-Za-z0-9_]`；`on_open ≤ 8` / `events ≤ 64`；`args` 必须是对象。
   其中 **`on_open` 里任一调用失败 → 整个应用打不开**（停在导入界面、无报错）。

### 检查什么

| 级别 | 条件 |
|---|---|
| **ERR** | 卡片引用（`X.data.*` 或 `when X.is_ok`）的名字在 `page.data.json` 里不存在 |
| **ERR** | 卡片读了某个 binding target 的 `.data.*` 却没用 `when X.is_ok` 包起来 |
| **ERR** | `service` 未在 `manifest.capabilities` 声明；`target` 非法；`args` 非对象；超上限；未知键 |
| **ok** | 上述都通过 |
| **warn** | binding 的 target 既没被引用也没预置（今天无害，但将来一旦被引用就会崩）；seed 成 `is_ok:false`（读它就必须 guard） |

### 前后对照（本机实测，见 [`证据/前后对照_20261004.txt`](证据/前后对照_20261004.txt)）

| 输入 | 结果 |
|---|---|
| 出货 `bundle/`（好卡） | `3 ok / 2 warn / **0 error**` → exit 0 |
| 同一张卡，`page.data.json` 删掉 `read` 预置 | `**1 error**`：点名 `read` 未预置 → exit 1 |
| 同一张卡，去掉 `when read.is_ok { … }` guard | `**1 error**`：点名未 guard 的读取 → exit 1 |

### 上游

这三条已作为 issue 报给官方（附实证与源码依据）：
**→ [OctoSense-org/OctoScript-App-Design-Flow#150](https://github.com/OctoSense-org/OctoScript-App-Design-Flow/issues/150)**

配套可复用说明：[`../rinx/L0卡接宿主服务_实战指南.md`](../rinx/L0卡接宿主服务_实战指南.md)。
本检查器可作为 `hub check` 的一条补充规则（**已向官方表态愿意上游**）；在此之前它先在本仓保障
「拾意」这类接宿主服务的 L0 卡不会在评审环境里因为助手缺失而打不开。
