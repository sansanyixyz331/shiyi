# 文件索引

> 本索引列出本仓**会提交的全部文件**（按目录分组，逐条列出）。
> 材料按用途归类见 [`../MATERIALS.md`](../MATERIALS.md)；目录结构速查见 [`STRUCTURE.md`](STRUCTURE.md)；按官方材料要求逐项对照见 [`../SUBMISSION.md`](../SUBMISSION.md)。

**合计 283 个文件 / 175.9 MB。**

## 目录速览

| 目录 | 文件数 | 体积 | 是什么 |
|---|---|---|---|
| `根目录` | 13 | 0.13 MB | 仓库门面：作品说明、材料清单、结构速查、交付说明书、隐私 / 支持 / 归属、许可、官方要求的配置文件 |
| `bundle/` | 5 | 0.13 MB | ★ 主提交 —— 脚本应用「拾意 · 现场造卡」 |
| `apps/` | 13 | 0.26 MB | 第二形态：L0 卡片包，以及脚本应用的详细说明文档 |
| `octos/` | 8 | 0.12 MB | 第三形态：OctoSense 系统 app 源码 + 宿主扩展（技术深度证据） |
| `android/` | 6 | 122.78 MB | 安卓现成安装包（宿主 APK 分卷 + 拾意应用包 + 安装 / 验收 / 坑清单） |
| `docs/（说明文档）` | 16 | 1.40 MB | 设计、数据来源与限制、失败场景、对比口径、复现与答辩材料 |
| `docs/evidence（每条能力一组）` | 115 | 47.31 MB | 能力取证：截图 / 录屏 / 日志，每组一个 README |
| `ai/` | 21 | 0.40 MB | AI 接入方案与真实调用的证据 |
| `rinx/` | 15 | 2.35 MB | 手机线（Rinx 宿主）的说明与证据 |
| `build/` | 39 | 0.60 MB | 构建、渲染、录制与校验脚本，以及失败态留证 |
| `cards/` | 20 | 0.26 MB | 五屏卡片源码（卡片包形态的源） |
| `src/` | 5 | 0.06 MB | 流程与服务逻辑源码 |
| `tools/` | 3 | 0.01 MB | 辅助工具说明 |
| `review/` | 3 | 0.07 MB | 门禁报告、官方 scan 问答包 |
| `.github/` | 1 | 0.02 MB | 发布工作流 |

## 逐条清单

### 根目录（13 个）

- `.gitattributes`  — 0 KB
- `.gitignore`  — 1 KB
- `../AGENTS.md`  — 3 KB
- `FILE-INDEX.md`  — 17 KB
- `LICENSE`  — 11 KB
- `../MATERIALS.md`  — 7 KB
- `NOTICE`  — 1 KB
- `../PRIVACY.md`  — 2 KB
- `../README.md`  — 24 KB
- `STRUCTURE.md`  — 5 KB
- `../SUBMISSION.md`  — 46 KB
- `../SUPPORT.md`  — 2 KB
- `评审速览.md`  — 11 KB

### bundle/（5 个）

- `bundle/assets/icon.svg`  — 0 KB
- `bundle/listing.json`  — 2 KB
- `bundle/main.splash`  — 58 KB
- `bundle/manifest.json`  — 1 KB
- `bundle/screenshots/01.png`  — 67 KB

### apps/（13 个）

- `apps/shiyi-card/bundle/assets/icon.svg`  — 0 KB
- `apps/shiyi-card/bundle/bindings.json`  — 1 KB
- `apps/shiyi-card/bundle/kit/native/light/kit.json`  — 6 KB
- `apps/shiyi-card/bundle/listing.json`  — 2 KB
- `apps/shiyi-card/bundle/manifest.json`  — 1 KB
- `apps/shiyi-card/bundle/page.card`  — 8 KB
- `apps/shiyi-card/bundle/page.data.json`  — 5 KB
- `apps/shiyi-card/bundle/screenshots/01-read.png`  — 58 KB
- `apps/shiyi-card/bundle/screenshots/02-ask.png`  — 39 KB
- `apps/shiyi-card/bundle/screenshots/03-plan.png`  — 46 KB
- `apps/shiyi-card/bundle/screenshots/04-memo.png`  — 35 KB
- `apps/shiyi-card/bundle/screenshots/05-done.png`  — 38 KB
- `../apps/shiyi-live/README.md`  — 24 KB

### octos/（8 个）

- `../octos/README.md`  — 13 KB
- `octos/apps/shiyi/bundle/main.splash`  — 67 KB
- `octos/apps/shiyi/bundle/manifest.json`  — 0 KB
- `octos/apps/shiyi/bundle/tools.json`  — 2 KB
- `octos/crates/shell/src/shiyi.rs`  — 8 KB
- `../octos/host-extension/README.md`  — 6 KB
- `octos/host-extension/build_host.sh`  — 4 KB
- `octos/host-extension/speak_host_extension.patch`  — 21 KB

### android/（6 个）

- `../android/README.md`  — 7 KB
- `android/SHA256SUMS.txt`  — 1 KB
- `android/shiyi-live-0.8.6-rinx-bundle.zip`  — 83 KB
- `android/shiyi-live-rinx.manifest.json`  — 1 KB
- `android/shiyi-rinx-android-1.1.0-ai-arm64-v8a.apk.part1`  — 64.0 MB
- `android/shiyi-rinx-android-1.1.0-ai-arm64-v8a.apk.part2`  — 58.7 MB

### docs/（说明文档）（16 个）

- `AI接入方案.md`  — 6 KB
- `Agent任务演示.md`  — 11 KB
- `Rinx宿主改造说明.md`  — 6 KB
- `作品让项目多了什么_2分钟陈述.md`  — 4 KB
- `作品设计_拾意.md`  — 8 KB
- `可独立复跑_发回群闭环_步骤说明.md`  — 11 KB
- `回归清单.md`  — 10 KB
- `复赛结构变更说明_20261010.md`  — 5 KB
- `失败场景与回退_系统留证.md`  — 9 KB
- `对标官方场景与评审口径.md`  — 8 KB
- `小程序机制笔记.md`  — 9 KB
- `手机端复现说明.md`  — 6 KB
- `docs/拾意_复赛答辩幻灯片.pptx`  — 1.3 MB
- `数据来源与限制.md`  — 12 KB
- `生成器MVP_意图即卡.md`  — 9 KB
- `造App的机器_一页.md`  — 13 KB

### docs/evidence（每条能力一组）（115 个）

- `docs/evidence/act/01-review-six-services.png`  — 105 KB
- `docs/evidence/act/02-app-opened.png`  — 185 KB
- `docs/evidence/act/03-card-built.png`  — 217 KB
- `docs/evidence/act/04-confirm-sent.png`  — 257 KB
- `docs/evidence/act/05-room-message.png`  — 140 KB
- `evidence/act/README.md`  — 3 KB
- `docs/evidence/act/rinx-act-end-to-end.mp4`  — 446 KB
- `docs/evidence/assist-memory/00-default-unchanged.png`  — 92 KB
- `docs/evidence/assist-memory/01-assist-memory-4-rows.png`  — 118 KB
- `docs/evidence/assist-memory/02-assist-memory-unavailable.png`  — 97 KB
- `docs/evidence/assist-memory/03-model-fallback-with-card.png`  — 120 KB
- `docs/evidence/assist-memory/04-rinx-real-service.png`  — 117 KB
- `docs/evidence/chat-read/00-rinx-reads-room.png`  — 115 KB
- `docs/evidence/chat-read/01-picked-into-input.png`  — 120 KB
- `docs/evidence/chat-read/02-card-built-from-message.png`  — 139 KB
- `docs/evidence/chat-read/03-confirmed.png`  — 149 KB
- `docs/evidence/chat-read/04-memory-5-cards.png`  — 120 KB
- `evidence/chat-read/README.md`  — 3 KB
- `docs/evidence/chat-read/cardhost/00-default-unchanged.png`  — 92 KB
- `docs/evidence/chat-read/cardhost/01-stub-reads-3.png`  — 127 KB
- `docs/evidence/chat-read/cardhost/02-unavailable.png`  — 98 KB
- `docs/evidence/demo-desktop-mail-20261011/01-mail-and-shiyi.png`  — 1.2 MB
- `docs/evidence/demo-desktop-mail-20261011/02-glance-cards.png`  — 491 KB
- `docs/evidence/demo-desktop-mail-20261011/03-autoread-and-speak.png`  — 613 KB
- `evidence/demo-desktop-mail-20261011/README.md`  — 3 KB
- `docs/evidence/demo-desktop-mail-20261011/字幕.srt`  — 1 KB
- `docs/evidence/demo-desktop-mail-20261011/拾意_桌面_工作场景_演示.mp4`  — 1.2 MB
- `docs/evidence/demo-phone-groupmsg-20261012/01-selfread-status.png`  — 372 KB
- `docs/evidence/demo-phone-groupmsg-20261012/02-card.png`  — 387 KB
- `docs/evidence/demo-phone-groupmsg-20261012/03-confirmed-sentback-scheduled.png`  — 337 KB
- `docs/evidence/demo-phone-groupmsg-20261012/04-fired-notification.png`  — 950 KB
- `evidence/demo-phone-groupmsg-20261012/README.md`  — 4 KB
- `docs/evidence/demo-phone-groupmsg-20261012/字幕.srt`  — 1 KB
- `docs/evidence/demo-phone-groupmsg-20261012/拾意_手机_群消息_演示.mp4`  — 1.9 MB
- `docs/evidence/generator/generator-at-work.mp4`  — 353 KB
- `docs/evidence/glance/01-app-list-3cards.png`  — 1.6 MB
- `docs/evidence/glance/02-glance-3cards.png`  — 1.2 MB
- `docs/evidence/glance/03-after-restart.png`  — 1.6 MB
- `docs/evidence/glance/04-phone-app.png`  — 261 KB
- `docs/evidence/glance/05-phone-grid.png`  — 187 KB
- `docs/evidence/glance/06-phone-2cards.png`  — 328 KB
- `evidence/glance/README.md`  — 8 KB
- `docs/evidence/glance/desktop_glance_end_to_end.mp4`  — 1.7 MB
- `docs/evidence/glance/phone_glance_demo.mp4`  — 2.0 MB
- `docs/evidence/group-update/01-before-update.jpg`  — 238 KB
- `docs/evidence/group-update/02-bug-time-in-where.jpg`  — 229 KB
- `docs/evidence/group-update/03-v0.3.10-installed.jpg`  — 234 KB
- `docs/evidence/group-update/04-after-fix.jpg`  — 236 KB
- `evidence/group-update/README.md`  — 5 KB
- `docs/evidence/identify/card-model.png`  — 53 KB
- `docs/evidence/identify/card-rules-vs-model.png`  — 117 KB
- `docs/evidence/identify/card-rules.png`  — 52 KB
- `docs/evidence/identify/identify_cmp.json`  — 2 KB
- `docs/evidence/live-app/01-default-in-rinx.png`  — 106 KB
- `docs/evidence/live-app/02-card-built-in-rinx.png`  — 114 KB
- `docs/evidence/live-app/03-confirmed-in-rinx.png`  — 105 KB
- `docs/evidence/live-app/04-habit-card-in-rinx.png`  — 116 KB
- `docs/evidence/live-app/05-cardhost-admitted.png`  — 92 KB
- `docs/evidence/live-app/06-rinx-running.png`  — 109 KB
- `docs/evidence/live-app/07-card-built.png`  — 115 KB
- `docs/evidence/live-app/08-confirmed.png`  — 110 KB
- `docs/evidence/live-app/09-memory-3.png`  — 115 KB
- `evidence/live-run/README.md`  — 3 KB
- `docs/evidence/live-run/frame-0.5.png`  — 134 KB
- `docs/evidence/live-run/frame-12.png`  — 264 KB
- `docs/evidence/live-run/frame-19.5.png`  — 302 KB
- `docs/evidence/live-run/frame-5.png`  — 179 KB
- `docs/evidence/live-run/live-app-in-rinx.mp4`  — 342 KB
- `docs/evidence/live-run/rinx-live-end-to-end.mp4`  — 375 KB
- `docs/evidence/model-path/fallback-in-card-host.png`  — 99 KB
- `docs/evidence/model-path/model-standin-in-card-host.png`  — 100 KB
- `docs/evidence/model-path/payload-sent-to-model.json`  — 1 KB
- `docs/evidence/phone-live-20261008/01-input.png`  — 718 KB
- `docs/evidence/phone-live-20261008/02-card-created.png`  — 797 KB
- `docs/evidence/phone-live-20261008/03-glance-cards.png`  — 579 KB
- `docs/evidence/phone-live-20261008/phone-input-card-glance.mp4`  — 2.4 MB
- `docs/evidence/phone-live-20261008/picks.json`  — 1 KB
- `docs/evidence/phone-live-20261011/01-read-group.png`  — 345 KB
- `docs/evidence/phone-live-20261011/02-ai-card-created.png`  — 339 KB
- `docs/evidence/phone-live-20261011/03-ai-card-pinned.png`  — 339 KB
- `docs/evidence/phone-live-20261011/04-ai-source-device-assistant.png`  — 367 KB
- `docs/evidence/phone-live-20261011/05-sent-back-to-group.png`  — 348 KB
- `evidence/phone-live-20261011/README.md`  — 3 KB
- `docs/evidence/phone-live-20261011/kernel-log-ai-call.txt`  — 1 KB
- `docs/evidence/phone-notify-20261011/01-card-remind-lead-hour.png`  — 330 KB
- `docs/evidence/phone-notify-20261011/02-system-notification.png`  — 914 KB
- `docs/evidence/phone-notify-20261011/03-notify-speak-system-notification.png`  — 921 KB
- `docs/evidence/phone-notify-20261011/04-card-notify-and-spoke.png`  — 75 KB
- `docs/evidence/phone-notify-20261011/05-switch-off.png`  — 34 KB
- `docs/evidence/phone-notify-20261011/06-switch-on-with-remind.png`  — 332 KB
- `evidence/phone-notify-20261011/README.md`  — 6 KB
- `docs/evidence/phone-notify-20261011/notification-dump.txt`  — 1 KB
- `docs/evidence/phone-notify-20261011/tts-logcat.txt`  — 2 KB
- `docs/evidence/phone-schedule-20261011/01-system-notification.png`  — 908 KB
- `docs/evidence/phone-schedule-20261011/02-card-scheduled.png`  — 69 KB
- `docs/evidence/phone-schedule-20261011/notification-dump.txt`  — 1 KB
- `docs/evidence/phone-schedule-20261011/tts-audio-logcat.txt`  — 1 KB
- `docs/evidence/profile/01-profile-rinx-live.png`  — 120 KB
- `docs/evidence/profile/02-chat-with-you-tag.png`  — 23 KB
- `docs/evidence/profile/03-review-five-services.png`  — 100 KB
- `evidence/repin/README.md`  — 9 KB
- `docs/evidence/repin/card_after_repin.png`  — 1.4 MB
- `docs/evidence/repin/desktop_card_chat.jsonl`  — 6 KB
- `docs/evidence/repin/desktop_repin_end_to_end.mp4`  — 1.8 MB
- `docs/evidence/repin/phone_assistant_replied.png`  — 201 KB
- `docs/evidence/repin/phone_card_after.png`  — 183 KB
- `docs/evidence/repin/phone_card_before.png`  — 202 KB
- `docs/evidence/repin/phone_card_chat.jsonl`  — 4 KB
- `docs/evidence/repin/phone_repin_end_to_end.mp4`  — 5.8 MB
- `docs/evidence/repin/phone_tool_audit.jsonl`  — 0 KB
- `evidence/speak/README.md`  — 3 KB
- `docs/evidence/speak/d1_evidence.mp4`  — 3.1 MB
- `docs/evidence/speak/key_frames/01_publish_notify.png`  — 775 KB
- `docs/evidence/speak/key_frames/02_reminder_notify.png`  — 695 KB
- `docs/evidence/speak/tts_logcat.txt`  — 2 KB

### ai/（21 个）

- `../ai/AGENT.md`  — 5 KB
- `../ai/README.md`  — 3 KB
- `ai/manifest.ai.json`  — 1 KB
- `ai/templates/bindings_octos_turn.json`  — 0 KB
- `ai/templates/page.data.加reply占位.json`  — 0 KB
- `ai/templates/显示AI回复的卡.page.card`  — 2 KB
- `ai/tools.json`  — 3 KB
- `../ai/本地跑通_20261004.md`  — 6 KB
- `ai/证据/4轮问答_汇总.jsonl`  — 3 KB
- `ai/证据/AI_会话_g1.jsonl`  — 1 KB
- `ai/证据/AI_会话_g2.jsonl`  — 1 KB
- `ai/证据/AI_会话_g3.jsonl`  — 1 KB
- `ai/证据/AI_会话_g4.jsonl`  — 2 KB
- `ai/证据/B_出货版_助手行上卡.png`  — 82 KB
- `ai/证据/B_助手失败时兜底_无报错.png`  — 91 KB
- `ai/证据/Review通过_octos能力.png`  — 89 KB
- `ai/证据/内核profile_脱敏.json`  — 1 KB
- `ai/证据/内核日志_4轮LLM调用.txt`  — 2 KB
- `ai/证据/卡片显示回复_1.png`  — 36 KB
- `ai/证据/卡片显示回复_2.png`  — 37 KB
- `ai/证据/卡片显示回复_3.png`  — 37 KB

### rinx/（15 个）

- `../rinx/L0卡接宿主服务_实战指南.md`  — 6 KB
- `../rinx/README.md`  — 6 KB
- `rinx/bindings.json`  — 0 KB
- `rinx/manifest.send.json`  — 0 KB
- `rinx/证据/01_Review通过_显示能力与房间绑定.png`  — 94 KB
- `rinx/证据/02_Run后卡片渲染.png`  — 76 KB
- `rinx/证据/03_首次导入_Review通过.png`  — 85 KB
- `rinx/证据/04_首次导入_Run成功.png`  — 74 KB
- `rinx/证据/复赛_真读真发_20261008/01-life-room-import-run-card-confirm.mp4`  — 588 KB
- `rinx/证据/复赛_真读真发_20261008/02-other-room-same-app.mp4`  — 536 KB
- `rinx/证据/复赛_真读真发_20261008/03-receipt-lands-in-room.mp4`  — 222 KB
- `rinx/证据/复赛_真读真发_20261008/04-receipt-still.png`  — 364 KB
- `rinx/证据/房间消息_关键事件.json`  — 1 KB
- `rinx/证据/房间消息_原始响应.json`  — 4 KB
- `rinx/证据/演示视频_Rinx执行链_拾意.mp4`  — 349 KB

### build/（39 个）

- `build/_evidence/flow_run.json`  — 7 KB
- `build/_evidence/host_shiyi-01-read.log`  — 3 KB
- `build/_evidence/host_shiyi-02-ask.log`  — 2 KB
- `build/_evidence/host_shiyi-03-plan.log`  — 2 KB
- `build/_evidence/host_shiyi-04-memo.log`  — 2 KB
- `build/_evidence/host_shiyi-05-done.log`  — 2 KB
- `build/_evidence/neg_tampered.log`  — 2 KB
- `build/_evidence/neg_tampered.png`  — 33 KB
- `build/_evidence/neg_unsigned.log`  — 1 KB
- `build/_evidence/neg_unsigned.png`  — 21 KB
- `build/_evidence/shots/shiyi-01-read.png`  — 83 KB
- `build/_evidence/shots/shiyi-02-ask.png`  — 55 KB
- `build/_evidence/shots/shiyi-03-plan.png`  — 65 KB
- `build/_evidence/shots/shiyi-04-memo.png`  — 50 KB
- `build/_evidence/shots/shiyi-05-done.png`  — 55 KB
- `build/builtin_font.py`  — 4 KB
- `build/crop_png.py`  — 3 KB
- `build/demo_identify.py`  — 4 KB
- `build/font_check.py`  — 4 KB
- `build/gen_l0.py`  — 33 KB
- `build/gen_screens.py`  — 24 KB
- `build/make_font.py`  — 4 KB
- `build/make_narration.py`  — 6 KB
- `build/pipeline.py`  — 6 KB
- `build/record_demo.py`  — 22 KB
- `build/record_generator.py`  — 9 KB
- `build/record_live_app.py`  — 4 KB
- `build/record_rinx_app.py`  — 9 KB
- `build/record_rinx_live.py`  — 10 KB
- `build/render_cards.py`  — 8 KB
- `build/restamp_bundle.sh`  — 3 KB
- `build/review.json`  — 17 KB
- `build/scrub_evidence.py`  — 2 KB
- `build/shot_bundle.py`  — 6 KB
- `build/swap_locale.py`  — 1 KB
- `build/sync_bundle.py`  — 3 KB
- `build/verify_flow.py`  — 26 KB
- `build/verify_update_logic.py`  — 15 KB
- `build/visual_review.py`  — 6 KB

### cards/（20 个）

- `cards/shiyi-01-read/page.card`  — 8 KB
- `cards/shiyi-01-read/page.data.json`  — 5 KB
- `cards/shiyi-01-read/screenshots/01.png`  — 58 KB
- `cards/shiyi-01-read/service-actions.json`  — 1 KB
- `cards/shiyi-02-ask/page.card`  — 5 KB
- `cards/shiyi-02-ask/page.data.json`  — 4 KB
- `cards/shiyi-02-ask/screenshots/01.png`  — 39 KB
- `cards/shiyi-02-ask/service-actions.json`  — 1 KB
- `cards/shiyi-03-plan/page.card`  — 5 KB
- `cards/shiyi-03-plan/page.data.json`  — 3 KB
- `cards/shiyi-03-plan/screenshots/01.png`  — 46 KB
- `cards/shiyi-03-plan/service-actions.json`  — 1 KB
- `cards/shiyi-04-memo/page.card`  — 4 KB
- `cards/shiyi-04-memo/page.data.json`  — 2 KB
- `cards/shiyi-04-memo/screenshots/01.png`  — 35 KB
- `cards/shiyi-04-memo/service-actions.json`  — 1 KB
- `cards/shiyi-05-done/page.card`  — 4 KB
- `cards/shiyi-05-done/page.data.json`  — 2 KB
- `cards/shiyi-05-done/screenshots/01.png`  — 38 KB
- `cards/shiyi-05-done/service-actions.json`  — 1 KB

### src/（5 个）

- `src/host_local.py`  — 6 KB
- `src/intent_card.py`  — 11 KB
- `src/intent_model.py`  — 17 KB
- `src/memory_store.py`  — 10 KB
- `src/shiyi_flow.py`  — 17 KB

### tools/（3 个）

- `../tools/README.md`  — 3 KB
- `tools/l0_bindings_lint.py`  — 8 KB
- `tools/证据/前后对照_20261004.txt`  — 2 KB

### review/（3 个）

- `../review/ANSWERS.md`  — 9 KB
- `review/GATE.txt`  — 1 KB
- `review/scan-packet.json`  — 66 KB

### .github/（1 个）

- `.github/workflows/publish-app.yml`  — 16 KB
