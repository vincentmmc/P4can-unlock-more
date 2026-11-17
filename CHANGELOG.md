# Changelog

本仓库在固件基线 `v3.29.3` 之上做增量，版本号格式 `v3.29.3-<tag>`，
`tag` 为打包时的日期/批次标识，会写进 `FW_VERSION` 并显示在页面顶部。

## v3.29.3-more1117 — 2026-11-17

### 新增

- **「更多功能」页**（`data-page="feifan"`），8 组 141 项：
  驾驶辅助 24 / 灯光与喇叭 34 / 舒适与座椅 15 / 免打扰与 AP 34 /
  车身与开合 14 / 仪表与快捷 9 / 模块设置 11 / 集成清单
- 每条功能带证据等级（`A` 实锤 / `B` 推断 / `C` 本地）、落地状态与帧/位域追溯
- 44 个 TSL 配置位域的读写封装，统一走 `CMD 0xA3` 整块回写
- 一键快捷条：前爆闪 `0x5B`、后爆闪 `0x5E`、脉冲喇叭 `0x5A`、领航 `0x5F`、
  电池预热 `0x1D/0x1C`，每次点击在状态行回显实际发出的字节
- 固件更新面板增强：分区余量、当前版本、拖拽、文件预检、二次确认、
  进度与错误码中文释义
- 中英双语覆盖整页，技术标识（帧 ID / 位域 / API / FQBN）保持原样
- 本地模拟器 `sim/p4can-sim.html`：假 `/api/feifan/*`、假 OTA 进度、请求日志
- 工具链：`build_more.py` / `gen_feifan.py` / `integrate_feifan.py` /
  `patch_ota.py` / `pack_ota.py` / `build_sim.py` / `gen_docs.py`

### 修复

- 快捷按钮点了没反馈：原来只有 420 ms 的 `scale(.9)`，真机上很难察觉。
  改为按钮下方常驻状态行，三态（已发送 / 仅记录在本机 / 再点一次确认）
- 状态行永远不变色：CSS 选择器写 `[data-kind="ok"]`，JS 传 `sent`，已统一
- 中文回译撞车：「闪 2 次」被翻回「2 次」，删掉裸词条并区分次数标签
- 位域提示串漂移：加字段后旧的 `TECH_OVERRIDE` 把 `byte25 >>> 0 & 3` 盖成
  `0x3E9 · DAS`，只保留 `d2a` / `c1a` 两条覆盖
- `Nag Killer` 与看板已有词条重名，改为 `Nag Killer 抑制 / suppression`
- 系统升级入口从「更多功能」页移除，只保留在默认设置里，避免两处各刷一半
- OTA 前端异步竞态：`FileReader.onload` 晚于确认超时，导致误报"文件错误"，
  在 `onload` 里先解除待确认态

### 已知问题

- `web_api.h` 中 `/api/feifan/{status,config,action,gauge,blob}` **未实现**，
  页面写入只落 `localStorage`，不进 CAN
- 设计图的 `0x249 / 0x10C / 0x3E2 / 0x3E3` 在固件中不存在，相关功能已按位域重写
- 全部写入行为未经实车验证

## 基线

- `v3.29.3` — 上游 P4can-universal-unlock，本仓库从这一版开始改动
