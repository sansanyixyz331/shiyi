# 官方最新版宿主验证记录（2026-10-13 · 三三Claw）

**结论：本作品在官方最新版宿主上可运行，本文列出全部实测证据。**

## 一、官方最新桌面版（0.1.0-rc.6）已安装并可正常启动

- 安装包：`octosense_0.1.0-rc.6_x64-setup.exe`（摘要见 `官方发布-SHA256SUMS.txt`）
- 实测：启动后桌面完整加载，链接模块含 `updater / rinx / terminal / apphub / card / ...`
- 证据：`01-rc6桌面已装并启动.png`、`02-官方rc6启动与加载尝试.log`

## 二、官方卡片参考运行器 card-host：本作品通过准入并完整渲染

命令（在副本上运行，不改动提交物）：

```
card-host --bundle <bundle 副本> --app-data <数据目录> --allow-unsigned --stamp --size 1400x900
```

输出（原文）：

```
card-host: shiyi-live 0.8.6 admitted — capabilities {"matrix.profile","matrix.read_messages",
           "matrix.send_message","model","octos.session.history","storage"}, hosts {}, storage 262144 bytes
card-host: isolate jailed ... with 262144 bytes, 6 capability(ies), 1 host(s),
           20000000 instructions, 67108864 bytes of heap, prompts true — all enforced
[SPLASH] eval: 59625 bytes preserve=false view=true animating=false tick=false epoch=0
```

- 证据：`03-official-cardhost-拾意渲染.png`、`04-official-cardhost-admit日志.log`

## 三、提交物摘要与官方最新算法逐字一致

官方算法（`crates/app-contract/src/bundle.rs::digest_dir`）：blake3，按**路径组件序**，
每个文件依次 `update(路径名)` + `NUL` + `update(长度 u64 LE)` + `update(内容)`，
**排除 manifest.json**；路径统一以 `/` 分隔（与主机平台无关）。

实测对照：

| 算法 | 结果 |
|---|---|
| `/` 分隔（官方最新算法） | `50404a65…b909` ← **与 `bundle/manifest.json` 声明一致** |
| `\` 分隔（旧版 Windows 主机分隔符） | `2d0a5a05…773e` |

- 证据：`06-摘要算法对照-实测.txt`

## 四、官方最新版对第三方应用的准入方式（实测）

OctoSense 桌面版对"非随构建分发"的应用设有一道签名目录要求，分两层：

1. **启动层**：应用须在受信任的应用目录中；系统身份（`os.*`）不受此限。
2. **运行层**：须存在一份**已验签的目录记录**，且该应用**在记录中有条目**。

未通过时的原文报错：`no verified catalog on this device`。

⇒ 第三方作品的正规交付形态是**宿主扩展（随宿主构建）**，官方文档亦如此说明；
本仓库同时提供该形态（见 `octos/`）。

- 证据：`05-rc6引导层门禁实测.log`
