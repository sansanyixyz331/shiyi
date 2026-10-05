# 真机连续录屏 · Rinx 端到端（拾意 · 现场造卡 0.7.2）

`rinx-live-end-to-end.mp4` —— **一段连续的真实屏幕录制**（不是帧拼），20.7 秒，
1316×1436、H.264、15fps。拍摄对象是**真机上的 Rinx 宿主窗口**，全程由
`MAKEPAD_REMOTE` 遥控接口驱动，无人手介入。

## 这段里发生了什么（时间轴）

| 时间 | 画面 |
|---|---|
| 0–2s | 导入表单：`path` 指向本仓库 `apps/shiyi-live/bundle`，`room` 绑定测试房 |
| 2–6s | 点 **Review bundle** —— 宿主列出本应用声明的**五个服务**并接受 |
| 6–11s | 点 **Run** —— 应用在真机跑起来 |
| 11–13s | 点 **忘掉** —— 把长期记忆清零（准备演示 0→1） |
| 13–15s | 在「从聊天拾意」区**点一条真实房间消息** —— 它被填进输入框 |
| 15–18s | 点 **造卡** —— 卡片当场长出来（出行 · 下周三 · 10月14日 · 深圳） |
| 18–20s | 点 **确认行程** —— 长期记忆 **0 → 1 张卡**（「常去：深圳 · 去过 1 次」） |

关键帧：`frame-0.5.png`（表单）/ `frame-5.png` / `frame-12.png` / `frame-19.5.png`（记忆 1）。

## 为什么它能被"遥控"（宿主能力）

Rinx 支持 `MAKEPAD_REMOTE=<port>` 环境变量，启动后开一个**本地 HTTP 遥控口**
（makepad 自带，`src/` 内测试 `standalone_remote.rs` 即其契约）：

- `GET /s` —— 窗口几何（**layout 点** vs 物理像素，含 DPI）
- `GET /snap?q=` —— **所有可点控件的 id/type/矩形/文本**（"ready to click"）
- `GET /m?k=move|down|up|click|scroll` —— 鼠标；`/click?x=&y=` 为别名
- `GET /k?t=`——打字；`/g?raw=1` 抓帧；`/d` 导出整棵控件树
- 收尾：`/gq`（抓帧后优雅退出）或 `/quit`

**坐标是"layout 点"（窗口局部，y 向下），不是屏幕像素。** 本机 DPI=1.25，
早前拿物理像素去点全落空——这是踩过的坑。

## 复现步骤

1. 起宿主：`MAKEPAD_REMOTE=8799 rinx.exe`（本机为 `F:/gosim_build/rinx_target/debug/rinx.exe`）
2. 遥控导航到导入表单，填 `path`（本仓库 `apps/shiyi-live/bundle`）与 `room`
3. 驱动脚本：`00_docs/_full_demo.py`（Review → Run → 清记忆 → 点消息 → 造卡 → 确认）
4. 录屏：`ffmpeg -f gdigrab -framerate 15 -offset_x <win.x> -offset_y <win.y> -video_size 1316x1436 -i desktop out.mp4`
   —— 宽高必须是偶数（`yuv420p` 要求），故高度取 1436 而非 1377。
   录制让 `-t <秒>` 自然结束，**切勿中途强杀**（否则 moov 写不完，文件只剩 48 字节）。

## 两个实测命门（已固化进技能）

1. **窗口几何会自己变**：Rinx（makepad）在页面切换/内容变化时会重排窗口尺寸，
   旧坐标随即失效 → 每步操作前**重新 `/snap` 取坐标**，别缓存。
2. **app 内容高于窗口时，底部按钮会被裁掉**：`snap` 默认只列**可见**控件，
   被裁的按钮查不到、也点不中。本例把窗口加高到 1436px 后
   「确认行程」才完整露出（[881,1077,65,36]）。
