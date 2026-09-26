# Developing this Hub app

Before changing this app, read the shared guides in a local Hub checkout and
record its revision; do not invent missing requirements:

- `docs/FIRST-APP.md` — build your first Hub app
- `docs/PUBLISHING.md` — manifest / listing / signing / submitting contract
- `docs/ICONS.md` — icon guidelines
- `docs/DEVELOPMENT.md` — development guide map

## 本仓库约定

- **本仓库拥有这个 app**；`bundle/` 是唯一的发布产物目录。开发说明、源码工具、
  密钥、测试证据一律留在 `bundle/` 之外。
- UI 产物走 **Image-to-AppCard 工作流**（`OctoScript-AppCard/lab/image-to-appcard-flow`），
  参考产物形态看 `OctoScript-AppCard/apps/aircon/`。
  **不要手写 L0**，除非 app 拥有者明确要求。
- 数据/状态/事件语义用 **L0 规范**（`a2app-l0/framework/l0.md`）。
- 图标只维护**一份**，路径与 `listing.json` 中声明的一致；不要另建启动器/商店图副本。
- **只申请已实现功能需要的能力**（capabilities）。当前骨架零网络、零存储、零助手授权。
- 替换掉所有占位值（app id / 名称 / publisher / URL / 平台声明 / 许可）。
  商店截图必须来自**真实原生捕获**，不能用设计稿。
- 原生行为与外观验证**独立于** bundle 门禁；如实报告测过哪些平台与流程。
- 每次改 `bundle/` 后 `hub stamp` → `hub check`；审查包放在 bundle 外；
  只在**最终字节**上签名，签后任何修改都要重盖公章并重签。发布密钥不入库。

## 本 app 特有的要求

- **no-facts 是硬约束**：时间/地点/天气/班次/金额等事实必须来自真实数据源并标注来源。
  模型只做识别与组织，禁止编造执行结果。
- 意图识别结果必须**以"待确认卡片"呈现**，用户确认后才执行；所有动作可撤回、可接管。
- 长期记忆命中时必须**在卡片上显式说明**"命中哪条偏好、因此改变了什么建议"。

## 构建与测试

（随实现补充：构建命令、测试命令、原生验证步骤。）
