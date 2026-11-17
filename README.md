# P4can-unlock-more

> [!WARNING]
> **只适用于 32 MB Flash 的板子**（微雪 ESP32-P4-WIFI6 / rev3.2）。
> **16 MB 版本刷这个包会直接变砖** —— 分区表 `app5M_fat24M_32MB` 与 16 MB flash 不匹配，烧进去连 bootloader 都起不来，只能用 USB 重新救回来。
> 16 MB 需要自己改 `large_fat_32MB.csv` 一类分区表、把 FQBN 里的 `FlashSize=32M` 换成 `16M`、`PartitionScheme` 换成 16 MB 方案，然后重新编译。仓库里没有现成的 16 MB 配置。

给 **Waveshare ESP32-P4 WiFi6 3×TWAI** 板子的特斯拉 CAN 工具固件。
在 [P4can-universal-unlock](https://github.com/06066060606060/P4can-universal-unlock) `v3.29.3` 的看板上，新增一页**「更多功能 / More features」**，并把固件更新面板补成能真正用的一次性流程。

**界面默认中文**，右上角语言开关可切英文，选择记在 `localStorage`，重启后保持。

<img src="docs/img/more-home.png" width="320" alt="更多功能页 / More features">

---

## 先说清楚现状

| | 状态 | 说明 |
|---|---|---|
| 「更多功能」页面 | ✅ 可用 | 8 组 141 项，中英双语，全部置位/开关/动作按钮均已自测 |
| 固件更新（OTA） | ✅ 可用 | 网页上传 `.bin`，双分区 A/B，失败可回滚 |
| 本地模拟预览 | ✅ 可用 | `sim/p4can-sim.html`，双击即开，不需要板子 |
| **`/api/feifan/*` 后端端点** | ❌ **未实现** | 页面的读写动作目前只落在浏览器 `localStorage`，**还没有真的发到 CAN** |

最后一条是关键：这一版把**前端**完整接进了官方看板，`web_api.h` 里那 5 个端点仍是 TODO。
所以现在刷进去点开关，界面会记住状态，但车不会动。要真正生效见 [docs/PROTOCOL.md](docs/PROTOCOL.md)
里给出的帧与位域定义，按它补端点即可 —— 数据、页、打包链路都已经就位。

---

## 它做了什么

### 1. 更多功能页（8 组 / 141 项）

| 分组 | 项数 | 内容 |
|---|---|---|
| 驾驶辅助 | 24 | 自动换挡、打灯变道、AP 恢复策略、限速识别、驾驶员监控抑制 |
| 灯光与喇叭 | 34 | 脉冲远光/前雾/后雾、脉冲喇叭、动态刹车灯、迎宾灯效、氛围灯 |
| 舒适与座椅 | 15 | 座椅加热/通风/记忆、空调烘干、后视镜、方向盘加热 |
| 免打扰与 AP | 34 | Nag Killer 抑制、提示音、AP 自动开启/退出、超车加速 |
| 车身与开合 | 14 | 前备箱、后备箱、四门、充电口、后视镜折叠 |
| 仪表与快捷 | 9 | 仪表盘数据、滚轮按键、首页一键快捷 |
| 模块设置 | 11 | 总线速率、广播、日志、恢复默认 |
| 集成清单 | — | 追溯表：每一项来自哪个源、证据等级、对应帧/位域 |

每一项都标注了**证据等级**与**落地方式**：

- `A` — 实锤：位域偏移、掩码、命令字节直接读自反编译的 `SETTINGS` 数组
- `B` — 推断：来自界面设计图的命名与分组，未在固件中命中对应帧
- `C` — 本地：纯前端行为，无硬件依赖

写操作统一走 TSL 配置块：读 `byte[offset] >>> shift & mask`，清位后置值，
整块用 `CMD 163 (0xA3)` 回写。快捷键类动作走 `CMD 187 (0xBB)` 单字节值。

### 2. 固件更新面板

上游已经有可用的 `POST /update` + `GET /api/ota/status`，缺的是前端：
现在补上了分区余量、当前版本、拖拽选文件、大小/魔数预检、二次确认、
上传进度与 `Update.errorString()` 的错误码翻译。

### 3. 中英双语

页面顶部语言开关联动整站。动态拼接的文案（`Uploading 42%`）用
`MutationObserver` 兜底，中文模式下技术标识（帧 ID、位域、API、FQBN）保持原样。

---

## 刷机

到 [Releases](../../releases) 下载，两种包，按需选：

### 升级包 `*-ota.bin`（约 1.4 MB）—— 平时更新用

1. 手机/电脑连上 P4 的热点
2. 打开 `http://192.168.4.1` → **设置 → 固件更新**
3. 选 `P4can-unlock-more-v3.29.3-more1117-ota.bin`
4. 点一下，再点一下确认，等进度条走完自动重启

OTA 只写 app 分区，**改不了 bootloader、分区表和 flash 参数**。

### 完整包 `*-full.bin`（32 MB）—— 首次烧录 / 救砖用

```bash
esptool.py --chip esp32p4 -p <PORT> -b 460800 write_flash 0x0 P4can-unlock-more-v3.29.3-more1117-full.bin
```

整片镜像布局（ESP32-P4 与 S3 不同，`0x0` 是空白 `0xFF`）：

| 偏移 | 内容 |
|---|---|
| `0x2000` | bootloader（magic `E9`） |
| `0x8000` | 分区表（magic `AA50`） |
| `0x10000` | 应用镜像（magic `E9`） |

每个 Release 都附 `manifest.json`，含两个包的 sha256、大小、分区余量、
FQBN 与页面指纹，刷完可以对照页面上的版本号核对。

---

## 从源码编译

需要 **Arduino-ESP32 core 3.3.12** 与 `arduino-cli`（或 Arduino IDE 2.x）。

```text
esp32:esp32:esp32p4:ChipVariant=postv3,FlashSize=32M,PartitionScheme=app5M_fat24M_32MB,PSRAM=enabled,USBMode=hwcdc,CDCOnBoot=cdc,FlashMode=qio
```

`firmware/P4can-unlock-more/` 就是 sketch 目录，直接用 IDE 打开即可编译。

### 一条命令出两个包

```bash
python tools/more/pack_ota.py            # 重建页面 → 编译 → 出包 → 校验
python tools/more/pack_ota.py --no-html  # 页面没改，跳过 gzip 重建
python tools/more/pack_ota.py --dry-run  # 只检查环境
```

脚本会做 7 步，任一步不合规直接中止：

1. 重跑 `gen_feifan.py` → `integrate_feifan.py` → `patch_ota.py`，再 gzip 成 `index_html.h`
2. 同步源码到 `build/` 编译副本，改写 `FW_VERSION` 打版本标
3. `arduino-cli compile`
4. 提取 `.ino.bin`，校验大小 ≤ `0x480000`、首字节 `0xE9`
5. 提取 `.merged.bin`，校验 32 MB 与三个关键偏移
6. **逐字节比对**镜像内嵌 gzip 与 `dashboard_source.html`（防止页面没同步进去）
7. 写 `dist/manifest.json`

`arduino-cli` 找不到时按 `ARDUINO_CLI` 环境变量 → `PATH` → `tools/` 顺序查找。

---

## 本地预览（不刷板）

```bash
python tools/more/build_sim.py
```

从 `index_html.h` 解出页面，注入假后端，输出 `sim/p4can-sim.html`。
双击打开即可点完整流程：假 `/api/feifan/*`、假 OTA 进度、右下角 SIM 面板
能看到每个请求的方法、路径、payload 与最近动作。

> 这是调试页面用的，不能替代真机验证。

---

## 目录结构

```text
firmware/P4can-unlock-more/     固件 sketch（.ino + 头文件 + 页面）
  dashboard_source.html         可编辑的看板源码（注入块标了 P4CAN-* 注释）
  index_html.h                  由它 gzip 生成的嵌入头，不要手改
  tools/                        上游自带的构建脚本
tools/more/
  build_more.py                 合并三路来源 → data/feifan-menu-data.json
  gen_feifan.py                 生成页面/CSS/JS/翻译片段
  integrate_feifan.py           5 处注入看板（幂等，先删旧块）
  patch_ota.py                  固件更新面板增强（幂等）
  pack_ota.py                   编译 + 出包 + 校验
  build_sim.py                  生成本地模拟页
data/feifan-menu-data.json      141 项功能 + 44 个位域 + 命令/API 定义
docs/                           FEATURES / PROTOCOL / OTA / REVERSE
sim/p4can-sim.html              本地模拟页（可直接打开）
```

---

### 详细文档

| 文档 | 内容 |
|---|---|
| [docs/FEATURES.md](docs/FEATURES.md) | 141 项功能全表，逐项标注证据等级、帧/位域、落地方式 |
| [docs/PROTOCOL.md](docs/PROTOCOL.md) | 帧格式、命令字、44 个位域、`0xBB` 快捷键值、前端契约 |
| [docs/OTA.md](docs/OTA.md) | 分区/回滚机制、打包 7 步、验收清单、离线校验 |
| [docs/REVERSE.md](docs/REVERSE.md) | 三路来源怎么拆的、纠错记录、去重决策、还没搞清的 |

---

## 硬件与接线

板子：Waveshare ESP32-P4-WIFI6，rev3.2，32 MB flash，`app5M_fat24M_32MB` 分区。
`ota_0` / `ota_1` 各 `0x480000`（4.5 MB），单包上限 4,718,592 B。

| 总线 | TWAI | TX | RX |
|---|---|---|---|
| CAN 1 BODY | 0 | GPIO20 | GPIO21 |
| CAN 2 CHASSIS | 1 | GPIO22 | GPIO23 |
| CAN 3 PARTY | 2 | GPIO26 | GPIO27 |

---

## 已知限制

- `web_api.h` 里 `/api/feifan/{status,config,action,gauge,blob}` 五个端点未实现，
  页面写入不落 CAN。这是本版最大的缺口。
- 设计图上的 `0x249 / 0x10C / 0x3E2 / 0x3E3` 在 Albert 固件与 P4 源码里命中 0 次，
  这几个功能已按真实位域重写，帧号只作脚注保留，别照着发帧。
- 分区表、bootloader、flash 参数只能线刷，OTA 无法更改。
- 没有在实车上验证过任何一项写入行为。

---

## 安全与合规

这是给**封闭场地调试**用的工具。改动车身行为（灯光爆闪、脉冲喇叭、
免打扰抑制、驾驶员监控抑制）在公共道路上可能违法，也可能让车辆进入
不符合型式认证的状态。

- 一切后果自负，作者不承担任何责任
- 不要在公共道路使用影响灯光、喇叭、限速识别的功能
- 刷机前确认你有办法救砖（完整包 + USB 线）

与特斯拉公司无任何关联。特斯拉、Model 3/Y 等商标归其所有者。

---

## 致谢

- [P4can-universal-unlock](https://github.com/06066060606060/P4can-universal-unlock) —— 固件基线
- [204442021](https://github.com/204442021) —— 功能清单与逆向素材
- [P4can-universal-unlock 生态](https://github.com/06066060606060) 的其他贡献者

## ☕ 赞助

> 项目完全开源免费。如果它帮你省下了折腾的时间，欢迎请作者喝杯咖啡，助力后续更新~

<table>
  <tr>
    <td align="center"><img src="docs/sponsor/web_alipay.jpg" width="220" alt="支付宝收款码"><br><sub><b>支付宝</b></sub></td>
    <td align="center"><img src="docs/sponsor/web_wechatpay.jpg" width="220" alt="微信收款码"><br><sub><b>微信支付</b></sub></td>
  </tr>
</table>

## 📮 联系作者

> 装不上、刷完了没反应、想加功能，都可以来找我。

<table>
  <tr>
    <td align="center"><img src="docs/sponsor/web_douyin.jpg" width="220" alt="抖音二维码"><br><sub><b>抖音 · @耶基大学懂事长</b><br>抖音号 <code>yejiuni</code></sub></td>
    <td align="center"><img src="docs/sponsor/web_wechatauthor.jpg" width="220" alt="作者微信二维码"><br><sub><b>微信 · 扫码加好友</b></sub></td>
  </tr>
</table>

## License

新增部分 MIT，见 [LICENSE](LICENSE)；固件基线的版权与条款见 [NOTICE](NOTICE)。

---

[English](README.en.md)
