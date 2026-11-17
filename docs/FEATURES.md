# 功能清单 / Feature index

> 本文件由 `tools/more/gen_docs.py` 从 `data/feifan-menu-data.json` 自动生成，请勿手改。

共 **141** 项，分为 **8** 组。证据等级：`A` 反编译实锤 · `B` 设计图推断 · `C` 本地 UI。

## 总览

| # | 分组 | 英文 | 项数 | 说明 |
|---|---|---|---:|---|
| 1 | 驾驶辅助 | Drive assist | 24 | Nag Killer、打灯变道、自动换挡、速度与传动 |
| 2 | 灯光与喇叭 | Lights & horn | 34 | 远光爆闪、脉冲喇叭、雾灯警示与氛围灯 |
| 3 | 舒适与座椅 | Comfort & seats | 15 | 座椅按摩加热、记忆、空调与占用 |
| 4 | 免打扰与 AP | Nag & AP | 34 | 提醒抑制、AP/EAP/FSD 开关与轮询算法 |
| 5 | 车身与开合 | Body & latches | 14 | 车门锁扣、开合状态、提醒与滚轮模拟 |
| 6 | 仪表与快捷 | Gauges & shortcuts | 9 | 实时数据、胎压与一键快捷 |
| 7 | 模块设置 | Module settings | 11 | 外观、模块维护与参数备份 |
| 8 | 集成清单 | Integration notes | 0 | 命令表、位域、端点与刷写步骤 |

## 1. 驾驶辅助 / Drive assist

> Nag Killer、打灯变道、自动换挡、速度与传动

### 1.1 智驾核心 / ADAS core

#### `d1a` Nag Killer 抑制 · Nag Killer suppression

- 类型：**开关** · 证据：**A** · 状态：已有
- 说明：扭矩回显 0x370，Nag Burst 按需脉冲；纠正扭矩、帧数、暂停时长可调，今日已消次数回显
- 实现：P4-CAN 已内置 Nag Killer（web_api.h 里 Nag 相关实现 122 处，状态页已有实时计数），本页只做开关与参数映射，不重复实现。设计图标的「Flipper 算法」在这里落到 P4 现有 nag 配置。
- 来源：web_api.h:1461 / vehicle_logic.h
- 接口：`POST /api/feifan/config`

#### `d1b` 打灯变道 · Turn-signal lane change

- 类型：**开关** · 证据：**A** · 状态：已有
- 说明：打灯触发变道；CHASSIS 读 0x399 DAS 状态作为 AP 激活门。须已有 EAP/FSD 订阅
- 实现：P4 已有 0x293 注入（vehicle_logic.h LAB 段 7 处），设计图标注的「P4can 0x293 LAB」即此项。无订阅时不发帧，开关保持灰态。原 a2c「开启自动变道」与它是同一个功能，已合并到此处。
- 来源：vehicle_logic.h:0x293
- 接口：`POST /api/feifan/config`

#### `d1c` 加速模式 · Acceleration profile

- 类型：**分段选择** · 证据：**A** · 状态：已有
- 说明：舒适 / 标准 / 运动三挡，写 0x334 踏板映射
- 实现：P4 的 AP Drive Profile 已独占 0x334 出口（web_api.h:3239），与 LAB PedalMap 共用 UI_powertrainControl 覆盖层，本项做映射即可。注意 Party+Chassis 拓扑没有 0x334 通路。
- 来源：vehicle_logic.h:1561
- 接口：`POST /api/feifan/config`
- 取值：`comfort` 舒适 / `standard` 标准 / `sport` 运动

#### `d1d` 赛道模式 · Track mode

- 类型：**分段选择** · 证据：**B** · 状态：需新增
- 说明：操控平衡偏后驱、稳定性辅助强度、赛后冷却。非性能版可用，改帧重发会自动重算校验
- 实现：设计图标注「Flipper 0x313，操控平衡 100 / 稳定性辅助 30% / 赛后冷却关」。0x313 在 Albert 固件与 TSL 小程序里都搜不到，属未验证规格；落地前必须先在台架确认该帧在本车拓扑上真实存在。真正能落地的运动化入口是 d4 自动运动模式，那个是实锤位域。
- 来源：设计图 P4CAN FUSION
- 接口：`POST /api/feifan/config`
- 取值：`off` 关闭 / `street` 街道 / `track` 赛道

#### `d1e` TLSSC 限速跟随 · TLSSC speed follow

- 类型：**开关** · 证据：**B** · 状态：需新增
- 说明：0x331 恢复在 2026.14+ 车机固件下已失效，开关仅保留代码与状态显示
- 实现：设计图标注「已堵 · 2026.14+ 封」。TSL 侧 0x331 注入被车机加了校验，恢复后无效。本项如实标为不可用，不做「能开」的假承诺。
- 来源：设计图 P4CAN FUSION
- 接口：`POST /api/feifan/config`

#### `d1f` AP-First 注入顺序 · AP-First injection order

- 类型：**开关** · 证据：**B** · 状态：需新增
- 说明：任何注入之前先确认 AP 已接管，否则整包不发；Abort Guard 在 DAS 进入 ABORTING 时立即停发
- 实现：设计图底栏的三层安全：AP-First（AP 接管后才允许注入）、Abort Guard（DAS 进入 ABORTING 立即停发）、OTA 检测（升级中全停）。任一层不过就不发帧并记入诊断日志。P4 侧可复用现有 AP gate 状态机。
- 来源：设计图 P4CAN FUSION
- 接口：`POST /api/feifan/config`

### 1.2 自动换挡 / Auto shift

#### `d2a` 启用自动换挡 · Auto shift

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：支持滚轮、刹车＋方向盘、障碍物三种换挡入口，默认关闭
- 实现：Albert 固件 gearAutomationEnabled，默认关闭。原文：「支持滚轮、刹车方向盘和障碍物换挡」。设计图里的「滚轮挂挡 Albert 0x229」是本功能的四方向输入之一，不是独立功能，已合并到此处。
- 来源：Albert dashboard #gearAutomationEnabled
- 接口：`POST /api/feifan/config`

#### `d2b` 换挡前必须系安全带 · Seatbelt gate

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：读原车 0x145 刹车与 PARTY 0x30A 主驾安全带，两者都要连续 2 帧确认；进 P 挡不受此门限制
- 实现：gearSeatbeltSafetyEnabled，出厂默认勾选。「驾驶位有人与安全带模拟」不会绕过本机读取的真实安全带状态，这是原版明确写的。
- 来源：Albert dashboard #gearSeatbeltSafetyEnabled
- 接口：`POST /api/feifan/config`

#### `d2c` 换挡次数（单次刹车周期） · Shifts per brake cycle

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：0 表示不限；每次进入速度范围重新计数
- 实现：gearShiftLimit，原版范围 0-255，默认 0。开启「关闭刹车安全门」后本项一并失效。
- 来源：Albert dashboard #gearShiftLimit
- 接口：`POST /api/feifan/config`
- 取值：`0` 不限 / `3` 3 次 / `6` 6 次 / `10` 10 次

#### `d2d` 允许换挡速度上限 · Shift speed gate

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：按真实速度整数部分判断，0 表示低于 1 km/h；连续 2 帧满足才开放
- 实现：gearAutoShiftMaxSpeedKph，原版 0-8。连续两帧判定是为了避免边界抖动卡住体验。
- 来源：Albert dashboard #gearAutoShiftMaxSpeedKph
- 接口：`POST /api/feifan/config`
- 取值：`0` < 1 km/h / `1` < 2 km/h / `2` < 3 km/h / `3` < 4 km/h

#### `d2e` 动作冷却 · Shift cooldown

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：两次换挡之间的最小间隔
- 实现：gearCooldownMs，原版 100-5000，步进 50。
- 来源：Albert dashboard #gearCooldownMs
- 接口：`POST /api/feifan/config`
- 取值：`100` 100 ms / `300` 300 ms / `500` 500 ms / `1000` 1000 ms

#### `d2f` 刹车＋方向盘确认 · Brake + steering confirm

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：P 挡左转进 D、右转进 R；D/R 挡向任意方向超过阈值即互换
- 实现：gearBrakeToggleEnabled。速度门满足且刹车按下时取当前方向盘角度为基线；掉出再进入会重新取基线，取基线时角度无效则继续等待。方向按相对基线的瞬时角度判断，不做左右累计。
- 来源：Albert dashboard #gearBrakeToggleEnabled
- 接口：`POST /api/feifan/config`

#### `d2g` D/R 挡转向阈值 · Steering threshold

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：方向盘相对基线转动多少度触发互换
- 实现：gearDriveReverseSteeringThresholdDeciDeg，原版 1-360，默认 120。
- 来源：Albert dashboard #gearDriveReverseSteeringThresholdDeciDeg
- 接口：`POST /api/feifan/config`
- 取值：`60` 60° / `90` 90° / `120` 120° / `180` 180°

#### `d2h` 障碍物换挡 · Obstacle shift

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：读 PARTY 2/3 路 0x255 挡位建议与 0x12B 扭矩方向，只在 P 挡处理
- 实现：进 D/R 或挡位过期会清空数据；回到 P 后必须重新收到两帧新数据。方向盘角度确认开启时，D 建议要求左转、R 建议要求右转。
- 来源：Albert dashboard #gearObstacleNested
- 接口：`POST /api/feifan/config`

#### `d2i` 滚轮换挡方向映射 · Wheel shift mapping

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：原版四个方向默认均为无动作，需逐项指定
- 实现：设计图的「滚轮挂挡 Albert 0x229」即这里的输入源。P4 侧用 0xBB 模拟滚轮键值注入（左滚轮 140-144 / 右滚轮 146-149），与 TSL 侧键值表一致。
- 来源：Albert dashboard + TSL 0xBB 键值表
- 接口：`POST /api/feifan/action`
- 取值：`none` 无动作 / `ud` 上下 / `lr` 左右 / `all` 四向

#### `d2j` 智能流畅预设 · Smooth preset

- 类型：**网格按钮** · 证据：**A** · 状态：需新增
- 说明：一键写入 1000 ms · P 30° · D/R 60° · 障碍物 30°
- 实现：gearSmoothPreset 一次性写完四项，省得逐个调。默认值是原版的保守组合。
- 来源：Albert dashboard #gearSmoothPreset
- 接口：`POST /api/feifan/config`
- 取值：`smooth` 应用预设 / `default` 恢复默认

#### `d2k` 换挡闭环反馈 · Shift closed loop

- 类型：**只读信息** · 证据：**A** · 状态：需新增
- 说明：复用原车真实帧发送路径，读 0x118 确认；失败不重发
- 实现：原版明确「继续复用真实原帧发送路径和 0x118 反馈确认」。P4 侧 0x118 已有 6 处实现，可直接接。
- 来源：Albert dashboard + vehicle_logic.h:0x118
- 接口：`GET /api/feifan/status`

### 1.3 速度补偿 / Speed offset

#### `d3a` 速度补偿模板 · Speed offset template

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：舒适 / 标准 / 迅捷三套目标速度，另可开 V14 独立模板
- 实现：Albert 有「舒适目标速度 / 标准目标速度 / 迅捷目标速度」三组数值，另加「V14 独立速度模板」与「日常预防扭矩（H0/H1、H2 等待期）」。本项只做模板选择，数值在固件侧落。
- 来源：Albert dashboard 驾驶员设置 / FSD 速度补偿
- 接口：`POST /api/feifan/config`
- 取值：`comfort` 舒适 / `standard` 标准 / `quick` 迅捷

#### `d3b` V14 独立速度模板 · V14 separate template

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：老版车机与 V14 用不同模板，避免互相覆盖
- 实现：原版按车机版本分流：V12 目标模板、V13 低速后台/高速车机、V14 独立模板。
- 来源：Albert dashboard FSD 速度补偿
- 接口：`POST /api/feifan/config`

#### `d3c` 预防扭矩与纠正 · Preventive torque

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：日常预防扭矩 H0/H1、H2 等待期；升级纠正 H2 超时与 H3-H5 帧数
- 实现：对应 Nag Killer 的扭矩模型。P4 侧 nag 参数已存在，这里给三档预设，避免用户直接填 Nm。
- 来源：Albert dashboard Nag Killer 段
- 接口：`POST /api/feifan/config`
- 取值：`gentle` 温和 / `normal` 标准 / `strong` 加强

### 1.4 传动与制动 / Drivetrain

#### `d4a` 自动运动模式 · Auto sport mode

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：按驾驶风格自动切运动化响应，三比特共 8 档
- 实现：配置位域 autoSportMode，byte24 >>> 0 & 7。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。这是设计图「赛道模式」真正能落地的那一层：TSL 原生就有这个位域，不用去猜 0x313。
- 来源：TSL SETTINGS 位域 autoSportMode
- 接口：`POST /api/feifan/config`
- 取值：`0` 关闭 / `1` 运动 / `2` 赛道 / `3` 自定义

#### `d4b` 能量回收制动 · Regen braking

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：回收强度，与原车停止模式配合决定松电门后的减速感
- 实现：配置位域 KERS，byte24 >>> 5 & 7。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。三比特可取值 0-7，原版 UI 只暴露常用三档。
- 来源：TSL SETTINGS 位域 KERS
- 接口：`POST /api/feifan/config`
- 取值：`0` 标准 / `1` 低 / `2` 高

#### `d4c` 停止模式 · Stopping mode

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：缓行 / 保持 / 转动，决定刹停后车辆行为
- 实现：配置位域 stoppingMode，byte25 >>> 5 & 3。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 stoppingMode
- 接口：`POST /api/feifan/config`
- 取值：`0` 缓行 / `1` 保持 / `2` 转动

#### `d4d` 自动强驻车 · Auto park brake

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：离车自动上电子手刹
- 实现：配置位域 autoParkBrake，byte24 >>> 4 & 1。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 autoParkBrake
- 接口：`POST /api/feifan/config`

## 2. 灯光与喇叭 / Lights & horn

> 远光爆闪、脉冲喇叭、雾灯警示与氛围灯

### 2.1 大灯与爆闪 / Headlight & strobe

#### `l1a` 远光爆闪 · High beam strobe

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：交替闪远光，档位决定脉冲速度
- 实现：配置位域 pluseHighBeam，byte25 >>> 0 & 3。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。设计图把它写成「P4can 0x249」，但 0x249 是 SCCM 拨杆状态帧、只能读不能写；真正让灯闪的是这个位域，原版就是写配置块，不是发 0x249。
- 来源：TSL SETTINGS 位域 pluseHighBeam
- 接口：`POST /api/feifan/config`
- 取值：`0` 关闭 / `1` 慢 / `2` 中 / `3` 快

#### `l1b` 近光跟随远光爆闪 · Low beam follows strobe

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：爆闪时近光同步亮灭，避免只剩远光孤零零闪
- 实现：配置位域 pluseHighBeamAndLowBeam，byte25 >>> 2 & 1。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 pluseHighBeamAndLowBeam
- 接口：`POST /api/feifan/config`

#### `l1c` 远光闪 3 次 · Triple flash

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：拉杆触发固定三下远光，超车示意用
- 实现：配置位域 blinkHighBeam，byte30 >>> 6 & 1。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。与 l1a 的区别：这一项是固定三次、不需要持续按住。
- 来源：TSL SETTINGS 位域 blinkHighBeam
- 接口：`POST /api/feifan/config`

#### `l1d` 远近光交替爆闪 · High/low alternating strobe

- 类型：**开关** · 证据：**B** · 状态：需新增
- 说明：走 DAS_bodyControls 高低 beam 决策位，200 ms 交替。不是 0x249 拨杆帧，不会把灯管成近光
- 实现：设计图标注「0x3E9 DAS」。这点确实关键：拿 0x249 拨杆帧做爆闪，灯光模块会判定为持续拨杆进而切近光；走 DAS 决策位才能真的闪远光。但 0x3E9 在 Albert 固件里不存在，Albert 的远光走 0x3C2 Mux1（见下两项）。想要现成可用的，直接用 l1a 位域。
- 来源：设计图 P4CAN FUSION
- 接口：`POST /api/feifan/action`

#### `l1e` 强制远光锁存 · Forced high beam latch

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：单次长按 1.5 秒，松开后确认锁存；控制帧 VEH 0x3C2 Mux1
- 实现：Albert fsdForceHighPhysicalEnabled。P4 里 0x3C2 是 VCLEFT 开关帧（无杆转向灯也走它），做灯光控制必须先锁定 Mux 号，否则会和转向灯打架。
- 来源：Albert dashboard #fsdForceHighPhysicalEnabled
- 接口：`POST /api/feifan/action`

#### `l1f` 第二次长按 0.5 秒爆闪 · Second long-press strobe

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：短按一次，第二次长按 0.5 秒；按住持续爆闪，松开立即停止
- 实现：Albert longPressHighBeamStrobeEnabled。手势状态机分短按 / 长按 / 锁存三态，松开必须立即停，不能有尾帧残留。
- 来源：Albert dashboard #longPressHighBeamStrobeEnabled
- 接口：`POST /api/feifan/action`

#### `l1g` 爆闪间隔 · Strobe interval

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：两次远光切换之间的间隔，1-100 ms
- 实现：highBeamStrobeIntervalMs。间隔太小会被前车当成挑衅，20 ms 已经很明显。
- 来源：Albert dashboard #highBeamStrobeIntervalMs
- 接口：`POST /api/feifan/config`
- 取值：`20` 20 ms / `50` 50 ms / `80` 80 ms / `100` 100 ms

#### `l1h` 双拉固定闪次数 · Double-pull flash count

- 类型：**分段选择** · 证据：**B** · 状态：需新增
- 说明：连续两次拉杆触发固定次数闪烁
- 实现：设计图原文「双拉触发固定闪 2/3/5/7 次可选」。
- 来源：设计图 P4CAN FUSION
- 接口：`POST /api/feifan/config`
- 取值：`2` 闪 2 次 / `3` 闪 3 次 / `5` 闪 5 次 / `7` 闪 7 次

### 2.2 喇叭 / Horn

#### `l2a` 脉冲喇叭 · Pulse horn

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：按固定节奏断鸣，档位决定脉冲速度
- 实现：配置位域 pluseHorn，byte27 >>> 6 & 3。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。设计图把它写成「0x10C」，但 0x10C 在 Albert 固件和 P4 源码里都不存在，写这个帧不会有任何东西响应。原版实际动作是写这个位域。
- 来源：TSL SETTINGS 位域 pluseHorn
- 接口：`POST /api/feifan/config`
- 取值：`0` 关闭 / `1` 慢 / `2` 中 / `3` 快

#### `l2b` 长按喇叭开启脉冲 · Long-press enables pulse

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：长按喇叭时按 l2a 的节奏断鸣，松手恢复常鸣
- 实现：配置位域 longPluseHorn，byte27 >>> 5 & 1。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 longPluseHorn
- 接口：`POST /api/feifan/config`

#### `l2c` 低速轻鸣笛 · Gentle horn at low speed

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：低速时按一下只轻鸣，不吓人
- 实现：配置位域 gentryHorn，byte34 >>> 4 & 3。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 gentryHorn
- 接口：`POST /api/feifan/config`
- 取值：`0` 关闭 / `1` 1 声 / `2` 2 声 / `3` 3 声

#### `l2d` 轻鸣笛次数 · Gentle horn count

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：轻鸣笛响几下
- 实现：配置位域 gentryHornCount，byte34 >>> 6 & 3。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 gentryHornCount
- 接口：`POST /api/feifan/config`
- 取值：`1` 1 声 / `2` 2 声 / `3` 3 声

#### `l2e` 喇叭联动远光 · Horn triggers high beam

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：按喇叭时同步闪远光提醒前车
- 实现：配置位域 hornLinkedHighBeam，byte32 >>> 5 & 1。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。城市道路慎用：按喇叭已经够吵，再闪远光容易激化矛盾。
- 来源：TSL SETTINGS 位域 hornLinkedHighBeam
- 接口：`POST /api/feifan/config`

#### `l2f` 远光联动喇叭 · High beam triggers horn

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：闪远光时同步短鸣
- 实现：配置位域 highBeamLinkedHorn，byte32 >>> 6 & 1。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 highBeamLinkedHorn
- 接口：`POST /api/feifan/config`

#### `l2g` 脉冲喇叭间隔 · Horn pulse gap

- 类型：**分段选择** · 证据：**B** · 状态：需新增
- 说明：两声之间的静音时长
- 实现：与 l2a 配合。城市禁鸣区域不要开脉冲喇叭，属于违法行为，仅台架验证用。
- 来源：设计图 P4CAN FUSION
- 接口：`POST /api/feifan/config`
- 取值：`150` 150 ms / `200` 200 ms / `300` 300 ms

### 2.3 雾灯与警示 / Fog & hazard

#### `l3a` 前雾灯爆闪 · Front fog strobe

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：前雾灯参与爆闪，雨雾天辨识度更高
- 实现：配置位域 pluseFrontFogLight，byte30 >>> 5 & 1。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 pluseFrontFogLight
- 接口：`POST /api/feifan/config`

#### `l3b` 后雾灯爆闪 · Rear fog strobe

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：后雾灯按节奏闪，用来提醒后车
- 实现：配置位域 pluseRearFogLight，byte31 >>> 6 & 1。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 pluseRearFogLight
- 接口：`POST /api/feifan/config`

#### `l3c` 动态刹车灯 · Dynamic brake light

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：刹车灯按减速度分档闪烁。设计图叫「刹车灯爆闪」，实际就是这一项
- 实现：配置位域 dynamicBrakeLight，byte33 >>> 6 & 3。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。关键差别：设计图写「亮起超过 1000 ms 才开始爆闪」，原版是按减速度分档。按时间触发会在等红灯时乱闪，按减速度触发只在真急刹时闪，后者才合理。
- 来源：TSL SETTINGS 位域 dynamicBrakeLight
- 接口：`POST /api/feifan/config`
- 取值：`0` 关闭 / `1` 轻 / `2` 中 / `3` 重

#### `l3d` 开门双闪 · Hazard on door open

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：开门时自动双闪，夜间路边下车更安全
- 实现：配置位域 openDoorHazardLight，byte30 >>> 4 & 1。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 openDoorHazardLight
- 接口：`POST /api/feifan/config`

#### `l3e` 倒车双闪 · Hazard on reverse

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：挂倒挡时双闪
- 实现：配置位域 backHazardLight，byte30 >>> 7 & 1。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 backHazardLight
- 接口：`POST /api/feifan/config`

#### `l3f` 倒车后雾灯照明 · Rear fog as reverse light

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：倒车时点亮后雾灯补光
- 实现：配置位域 backHazardRearFogLight，byte24 >>> 3 & 1。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 backHazardRearFogLight
- 接口：`POST /api/feifan/config`

#### `l3g` 转向辅助照明 · Cornering light

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：打方向时对应侧雾灯补光
- 实现：配置位域 steerAssistanceLighting，byte31 >>> 7 & 1。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 steerAssistanceLighting
- 接口：`POST /api/feifan/config`

#### `l3h` 后雾灯领航模式 · Rear fog pilot mode

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：实时控制 + 脉冲 + 安全锁存。四项权限默认关闭
- 实现：Albert 后雾灯段，帧 0x3E3。锁存意味着触发后必须显式解除，不会自己恢复，避免高速上突然熄灭。TSL 侧对应的就是 l3b 位域，两者选一实现。
- 来源：Albert dashboard 后雾灯
- 接口：`POST /api/feifan/action`

#### `l3i` 后雾灯触发阈值 · Rear fog threshold

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：减速度达到多少才算重度，100-500
- 实现：rear-fog-hard-threshold，默认 250。
- 来源：Albert dashboard #rear-fog-hard-threshold
- 接口：`POST /api/feifan/config`
- 取值：`150` 150 / `250` 250 / `400` 400

#### `l3j` 自动减速后雾灯 · Decel rear fog

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：轻度减速闪 3 次、重度减速闪 6 次
- 实现：rear-fog-strobe-tgl。档位按减速度分轻度/重度，次数写死，不可调。
- 来源：Albert dashboard #rear-fog-strobe-tgl
- 接口：`POST /api/feifan/config`

#### `l3k` 倒车警示（双闪 + 8 次后雾灯） · Reverse warning

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：挂倒挡时联动双闪，并执行 8 次后雾灯脉冲
- 实现：与自动减速共用同一套脉冲引擎，只是固定 8 次。
- 来源：Albert dashboard 后雾灯
- 接口：`POST /api/feifan/config`

### 2.4 氛围灯与迎宾 / Ambient & welcome

#### `l4a` 常亮氛围灯 · Always-on ambient

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：总开关；关闭后仍保留分区设置，迎宾、转向、安全提示各自独立
- 实现：Albert ambientEnabled。设计图里的「氛围灯 Albert 0x679」就是这一项；0x679 在固件页面里没出现（属通信层 ID），UI 上按分区配置走。
- 来源：Albert dashboard #ambientEnabled
- 接口：`POST /api/feifan/config`

#### `l4b` 分区选择 · Zone selection

- 类型：**网格按钮** · 证据：**A** · 状态：需新增
- 说明：六个独立分区，每区独立开关与亮度，默认 60%
- 实现：data-ambient-zone-select 0-5，仪表台左右为 4/5，四门为 0-3。点一次切换该区开关。
- 来源：Albert dashboard 车厢氛围灯区域图
- 接口：`POST /api/feifan/config`
- 取值：`z4` 仪表台左 / `z5` 仪表台右 / `z0` 左前门 / `z1` 右前门 / `z2` 左后门 / `z3` 右后门

#### `l4c` 氛围灯亮度 · Ambient brightness

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：分区默认亮度
- 实现：原版是 10-100 的滑块，这里取三档常用值。
- 来源：Albert dashboard 常亮氛围灯
- 接口：`POST /api/feifan/config`
- 取值：`30` 30% / `60` 60% / `100` 100%

#### `l4d` 氛围灯跟随转向灯 · Ambient follows indicator

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：左右独立跟随，设置按驾驶员保存
- 实现：turnFollowAmbient 独立区块，与常亮氛围灯互不覆盖。P4 侧可从 0x249/0x3C2 拿转向灯状态。
- 来源：Albert dashboard #turnFollowAmbientControls
- 接口：`POST /api/feifan/config`

#### `l4e` 迎宾灯效 · Welcome lighting

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：开门聚焦，最后一个合格门关闭后播放一次展开。与常亮氛围灯独立，默认关闭
- 实现：welcomeEnabled。设计图的「迎宾灯光 Albert」即此项，已合并，不再单列。
- 来源：Albert dashboard #welcomeEnabled
- 接口：`POST /api/feifan/config`

#### `l4f` 灯效主题 · Welcome theme

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：五种预设，按开门到关门的整段时序播放
- 实现：welcomeStyle 0-4，默认 3 黑幕启幕（先暗场再按路径渐亮）。
- 来源：Albert dashboard welcome-theme-grid
- 接口：`POST /api/feifan/config`
- 取值：`0` 柔光环抱 / `1` 冰蓝流光 / `2` 暖金礼序 / `3` 黑幕启幕 / `4` 光迹回环

#### `l4g` 开门触发方式 · Welcome trigger

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：先过滤座椅有人/未知/过期，再决定主驾优先
- 实现：welcomeTriggerMode。通过开门筛选后资格会保持到关门，不是每次开门都重算。
- 来源：Albert dashboard #welcomeTriggerMode0
- 接口：`POST /api/feifan/config`
- 取值：`0` 确认无人后 / `1` 任何开门

#### `l4h` 迎宾亮度与节奏 · Welcome brightness & tempo

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：亮度 10-100%，节奏舒缓 / 标准 / 利落
- 实现：welcomeBrightness 默认 40%，welcomeTempo 默认 1 标准。两项合并成一组，避免面板过长。
- 来源：Albert dashboard #welcomeBrightness / #welcomeTempo
- 接口：`POST /api/feifan/config`
- 取值：`slow` 舒缓 / `normal` 标准 / `fast` 利落

## 3. 舒适与座椅 / Comfort & seats

> 座椅按摩加热、记忆、空调与占用

### 3.1 按摩与加热 / Massage & heat

#### `c1a` 座椅按摩（腰托气囊） · Seat massage

- 类型：**开关** · 证据：**B** · 状态：需新增
- 说明：充气 / 放气位交替驱动腰托气囊，压力读数（hPa）实时回显，节奏三挡
- 实现：设计图标注「0x3C2」。这一条要特别小心：0x3C2 在 P4 里是 VCLEFT 开关帧，无杆转向灯和座椅记忆都走它，Albert 也用它做灯光 Mux1。同一 ID 多用途，实现前必须先确认 Mux 号，否则按错 Mux 会误触发转向灯。
- 来源：设计图 P4CAN FUSION + vehicle_logic.h:VCLEFT_SWITCH_ID
- 接口：`POST /api/feifan/action`

#### `c1b` 按摩节奏 · Massage tempo

- 类型：**分段选择** · 证据：**B** · 状态：需新增
- 说明：充放气交替的速度
- 实现：设计图「节奏三挡」。气囊压力上限原版未给数值，需实测确定。
- 来源：设计图 P4CAN FUSION
- 接口：`POST /api/feifan/config`
- 取值：`slow` 舒缓 / `normal` 标准 / `strong` 强劲

#### `c1c` 按摩压力回显 · Massage pressure

- 类型：**只读信息** · 证据：**B** · 状态：需新增
- 说明：腰托气囊压力 hPa 实时读数，用于判断充放气是否真的在动
- 实现：设计图「压力读数（hPa）实时回显」。没有这一路回读就无法判断气囊是否卡住，所以它是按摩功能的前置条件，不是可选项。
- 来源：设计图 P4CAN FUSION
- 接口：`GET /api/feifan/status`

#### `c1d` 座椅加热快捷 · Seat heat shortcut

- 类型：**开关** · 证据：**B** · 状态：需新增
- 说明：滚轮长按切主驾加热挡位，不用进菜单
- 实现：设计图「滚轮长按切主驾加热挡位」。滚轮长按与滚轮换挡共用输入，必须有优先级仲裁，否则换挡时会被加热抢走。
- 来源：设计图 P4CAN FUSION
- 接口：`POST /api/feifan/action`

#### `c1e` 座椅加热挡位 · Seat heat level

- 类型：**分段选择** · 证据：**B** · 状态：需新增
- 说明：关 / 1 / 2 / 3 挡
- 实现：仅主驾。副驾加热仍是原车面板控制。
- 来源：设计图 P4CAN FUSION
- 接口：`POST /api/feifan/action`
- 取值：`0` 关 / `1` 1 挡 / `2` 2 挡 / `3` 3 挡

#### `c1f` 座椅占用伪装 · Seat occupancy spoof

- 类型：**开关** · 证据：**B** · 状态：需新增
- 说明：与安全带门冲突时，滚轮挂挡优先拦截。谨慎项
- 实现：设计图标注「Albert 0x30A，谨慎」。Albert 固件里 0x30A 出现过 2 次但与会话相关，未能确认就是座椅占用。风险点很实在：伪装「有人」会让 AEB 与安全气囊判定失真，所以默认关闭且不设快捷入口。
- 来源：设计图 P4CAN FUSION
- 接口：`POST /api/feifan/config`

### 3.2 座椅与记忆 / Seat & memory

#### `b2a` 主驾座椅 · Driver seat

- 类型：**开关** · 证据：**B** · 状态：不可达
- 说明：含记忆与按摩控制；点按记忆恢复，长按保存
- 实现：开关位在 JS 里对应 seatState.driverMassage，读自设备信息包 byte18>>>3&1；写入走 CMD 0xA7 的 base+(on?1:0)。座椅执行器不在 P4 三路 CAN 可达范围。
- 来源：vehicleControl.js:144 handleDeviceInfo / :224 toggleSeatMassage
- 接口：`POST /api/feifan/config`

#### `b2b` 主驾座椅调节 · Driver seat adjust

- 类型：**网格按钮** · 证据：**A** · 状态：不可达
- 说明：按住持续调节，8 秒自动发停止码，松手即停
- 实现：CMD 0xA7 + [26/27/28/29]；sendSeatHoldStart 触发后启 8000ms 定时器，sendSeatHoldEnd / onHide / onUnload 都会补发 CMD 0xA7 + [16]（座椅停止）。这是防止一直顶住电机的安全设计，净室重写时必须保留。
- 来源：vehicleControl.js:279-302
- 接口：`POST /api/feifan/action`
- 取值：`26` 前移 / `27` 后移 / `28` 靠背前 / `29` 靠背后

#### `b2c` 主驾记忆 · Driver memory

- 类型：**网格按钮** · 证据：**A** · 状态：不可达
- 说明：记忆1 / 2 / 3 / 女王 / 露营；短按恢复、长按保存
- 实现：短按发 CMD 0xA7 + [code]（恢复），长按发 [code+1]（保存），长按前有确认弹窗；650ms 内重复触发会被节流。名称「女王/露营」只是 UI 标签。
- 来源：vehicleControl.js:7-16 / :303 sendSeatMemory
- 接口：`POST /api/feifan/action`
- 取值：`52` 记忆1 / `54` 记忆2 / `56` 记忆3 / `60` 女王 / `58` 露营

#### `b2d` 副驾座椅调节 · Passenger seat adjust

- 类型：**网格按钮** · 证据：**A** · 状态：不可达
- 说明：含副驾按摩与记忆控制
- 实现：CMD 0xA7 + [12..15]，机制与主驾一致；主驾 26..29、副驾 12..15，两组码段不重叠，说明固件用单字节动作码查表分派。
- 来源：vehicleControl.js:42-49
- 接口：`POST /api/feifan/action`
- 取值：`12` 前移 / `13` 后移 / `14` 靠背前 / `15` 靠背后

#### `b2e` 副驾记忆 · Passenger memory

- 类型：**网格按钮** · 证据：**A** · 状态：不可达
- 说明：记忆1 / 2 / 3 / 女王 / 露营
- 实现：CMD 0xA7 + [62..70]，长按 code+1 保存。
- 来源：vehicleControl.js:17-27
- 接口：`POST /api/feifan/action`
- 取值：`62` 记忆1 / `64` 记忆2 / `66` 记忆3 / `70` 女王 / `68` 露营

#### `b2f` 编辑记忆名称 · Edit memory names

- 类型：**只读信息** · 证据：**C** · 状态：本地 UI
- 说明：主驾 / 副驾各自 5 个名称可自定义
- 实现：纯小程序本地 storage（readAll / saveGroup），只改显示文案，不下发模块。P4 若做可直接放浏览器 localStorage 或 NVS 的 UI 配置。
- 来源：vehicleControl.js:342 refreshSeatMemoryLabels
- 接口：`（前端本地）`

#### `b2g` 副驾便利进出 · Passenger easy access

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：副驾座椅便利进出触发条件
- 实现：不是动作码，而是配置块字段 frontRightEasyAccess：byte25 >>> 3 & 3。修改时 buildState -> updateState -> writeBytes 生成整块，再 CMD 0xA3 (163) 写回；回显读 e[25]>>>3&3。
- 来源：SETTINGS 表 / vehicleControl.js:235 pickEasyAccess
- 接口：`POST /api/feifan/config`
- 取值：`0` 关闭 / `1` 副驾安全带解系时 / `2` 副驾车门开关时

### 3.3 空调与便利 / HVAC

#### `c3a` 空调快捷 · HVAC shortcut

- 类型：**分段选择** · 证据：**B** · 状态：需新增
- 说明：远程预冷 / 预热模板，上车前在首页一键触发
- 实现：设计图标注「TSL 0x2E5」。0x2E5 在 P4 源码里搜不到，属需新增帧；TSL 侧走 CMD 0xA7 动作码，不直接发 CAN。这两条路径得二选一，不能混。
- 来源：设计图 P4CAN FUSION
- 接口：`POST /api/feifan/action`
- 取值：`cool` 远程预冷 / `heat` 远程预热 / `tmpl` 模板

#### `b3a` 空调烘干 · HVAC dry after parking

- 类型：**分段选择** · 证据：**A** · 状态：不可达
- 说明：停车后自动干燥空调风道
- 实现：配置块字段 airAutoArid：byte33 >>> 4 & 3（0/1/2/3 对应四档），写入走 CMD 0xA3 整块回写，回显读 e[33]>>>4&3。属于座舱 HVAC 执行器，P4 三路 CAN 不可达。
- 来源：SETTINGS 表 / vehicleControl.js:256 pickAirDry
- 接口：`POST /api/feifan/config`
- 取值：`0` 关闭 / `1` 烘干1分钟 / `2` 烘干5分钟 / `3` 烘干10分钟

## 4. 免打扰与 AP / Nag & AP

> 提醒抑制、AP/EAP/FSD 开关与轮询算法

### 4.1 免打扰设置 / Nag suppression

#### `a1a` 注视提醒抑制 · Gaze reminder suppression

- 类型：**开关** · 证据：**B** · 状态：已有
- 说明：辅助驾驶时自动抑制注意力提醒
- 实现：截图中新增项，本 APK 小程序版本里没有对应字段。按同构推断为配置块某个 bit 或 0x3FD 驾驶员监控位。P4 开源侧已有 Disable Driver Monitoring / driver_monitor_capture.h 与 LAB 门控，属于「已有等价」而非新增。
- 来源：截图 3；本包 SETTINGS 无此项
- 接口：`POST /api/feifan/config（待核对位）`

#### `a1b` 限速提示抑制 · ISA chime suppression

- 类型：**开关** · 证据：**B** · 状态：已有
- 说明：抑制 ISA 限速提示音
- 实现：同上，截图新增项。P4 v3.29.3 已含 isa_suppression_pure.h / ISA chime Suppression，直接复用即可。
- 来源：截图 3 / P4can isa_suppression_pure.h
- 接口：`POST /api/feifan/config（映射现有 ISA 设置）`

#### `a1c` 禁用视觉限速 · Disable visual speed limit

- 类型：**开关** · 证据：**B** · 状态：已有
- 说明：关闭视觉限速提醒
- 实现：截图新增项；P4 侧对应 Visual Speed Control Settings / Country-Map 相关设置， behaviour 需实车确认。
- 来源：截图 3
- 接口：`POST /api/feifan/config`

#### `a1d` 方向盘提醒抑制 · Hands-on-wheel suppression

- 类型：**开关** · 证据：**B** · 状态：已有
- 说明：辅助驾驶时自动抑制方向盘提醒
- 实现：截图新增项。P4 已有 Nag Killer（Mode H / TSL9 方式）与完整的力矩参数、 refractory、visual warning rescue 状态机，无需重写。
- 来源：截图 3 / P4can mode_h_pure.h / r79_dms_composition_pure.h
- 接口：`POST /api/feifan/config（映射现有 NAG 设置）`

#### `a1e` 方向盘抑制方式 · Suppression method

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：滚轮 / 无感 / 滚轮+无感
- 实现：配置块字段 ModeMDR：byte29 >>> 0 & 3，取值 0/1/2；apHelper 里还用该值控制 mdrWheelOn（1 !== value），即选「无感」时隐藏滚轮策略相关项。
- 来源：apHelper.js:94 / SETTINGS 表
- 接口：`POST /api/feifan/config {id:'ModeMDR'}`
- 取值：`0` 滚轮 / `1` 无感 / `2` 滚轮+无感

#### `a1f` 时间随机 · Randomised timing

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：滚轮操作间隔随机化
- 实现：字段 rand：byte28 >>> 0 & 1。resolveDelayMs 里 rand=1 时用 a+(b-a)*random() 在区间内取随机秒数，否则取区间中点。
- 来源：SETTINGS 表 / WHEEL_ACTIONS 模块 resolveDelayMs
- 接口：`POST /api/feifan/config {id:'rand'}`

#### `a1g` 滚轮操作时间 · Wheel action interval

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：模块模拟滚轮动作间隔
- 实现：字段 time：byte27 >>> 0 & 15。区间表 {1:[2,3],2:[3,5],3:[5,10],4:[10,15],5:[15,20],6:[20,25],7:[25,30],8:[30,35],15:[30,30]} 秒；15 为定点（固定 30 秒）。
- 来源：SETTINGS 表 / WHEEL_ACTIONS 模块 r 表
- 接口：`POST /api/feifan/config {id:'time'}`
- 取值：`1` 2-3秒 / `2` 3-5秒 / `3` 5-10秒 / `4` 10-15秒 / `5` 15-20秒 / `6` 20-25秒 / `7` 25-30秒 / `8` 30-35秒 / `15` 定点免打扰

#### `a1h` 加减时间间隔 · Up/down action gap

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：自动加减动作之间的间隔
- 实现：字段 jg：byte32 >>> 0 & 15。buildCycle 里 actionGapMs = jg * 100（1..10 -> 100..1000ms），越界或非整数默认 1000ms。
- 来源：SETTINGS 表 / WHEEL_ACTIONS 模块 buildCycle
- 接口：`POST /api/feifan/config {id:'jg'}`
- 取值：`1` 0.1s / `2` 0.2s / `3` 0.3s / `4` 0.4s / `5` 0.5s / `6` 0.6s / `7` 0.7s / `8` 0.8s / `9` 0.9s / `10` 1.0s

#### `a1i` 加减类型 · Up/down order

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：加减的执行顺序
- 实现：字段 jj：byte33 >>> 0 & 3。buildCycle 生成 [up,down] 或 [down,up] 两动作序列；2 按序号交替，3 用 Math.random() 决定。
- 来源：SETTINGS 表 / WHEEL_ACTIONS 模块 buildCycle
- 接口：`POST /api/feifan/config {id:'jj'}`
- 取值：`0` 先加后减 / `1` 先减后加 / `2` 加减交替 / `3` 加减随机

#### `a1j` 滚轮选择 · Wheel selection

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：操作滚轮选择
- 实现：字段 lr：byte28 >>> 6 & 3。buildCycle 里 0=left、1=right、2=按周期序号奇偶交替、3=随机；选中后再查 WHEEL_ACTIONS[left|right] 取键值。
- 来源：SETTINGS 表 / WHEEL_ACTIONS 模块 buildCycle
- 接口：`POST /api/feifan/config {id:'lr'}`
- 取值：`0` 左滚轮 / `1` 右滚轮 / `2` 左右交替 / `3` 左右随机

#### `a1k` 自动免打扰 · Auto nag suppression

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：跟随车机自动进入免打扰
- 实现：字段 automdr：byte28 >>> 4 & 1（0 关闭 / 1 跟随 AP）。与截图里的「注视/限速/视觉/方向盘」四项不同，这是本包确实存在的一项。
- 来源：SETTINGS 表 / apHelper.js:89
- 接口：`POST /api/feifan/config {id:'automdr'}`

#### `a1l` 免打扰周期算法 · Nag cycle algorithm

- 类型：**只读信息** · 证据：**A** · 状态：需新增
- 说明：随机延迟 + 滚轮选择 + 动作顺序 + 动作间隔
- 实现：完整链路已还原：resolveDelayMs(time,rand) 决定下一轮等待秒数 -> buildCycle(lr,jj,jg) 决定这一轮用哪只滚轮、先发 up 还是 down、两动作间隔多少毫秒 -> 每个动作最终转成 CMD 0xBB + WHEEL_ACTIONS 键值。P4 侧可用一个 FreeRTOS 任务 + runtime_gate 门控复刻，务必保留「停车硬暂停 / 视觉告警救援 / 物理滚轮输入优先」。
- 来源：WHEEL_ACTIONS (A1604D07) buildCycle / resolveDelayMs
- 接口：`（固件侧调度，无需单独 API）`

### 4.2 AP 设置 / AP settings

#### `a2a` 启用红绿灯识别 · Traffic-light recognition

- 类型：**开关** · 证据：**B** · 状态：需新增
- 说明：开启 AP 模式下红绿灯识别功能（需固件版本 4.3.0 以上）
- 实现：截图新增项，本包 SETTINGS 无对应字段，且带固件版本门槛。推断为新配置块 bit + 车机侧能力位，需抓新版小程序或实车抓包确认。
- 来源：截图 4
- 接口：`POST /api/feifan/config（待核对）`

#### `a2b` 绿灯自动起步 · Auto start on green

- 类型：**开关** · 证据：**C** · 状态：本地 UI
- 说明：绿灯亮起时自动起步（暂不开放）
- 实现：截图明确标注「暂不开放」，属于 UI 占位。P4 页面保留禁用态即可，不接后端。
- 来源：截图 4
- 接口：`（禁用占位）`

#### `a2d` 青春版 EAP · EAP lite

- 类型：**开关** · 证据：**B** · 状态：需新增
- 说明：启用青春版 EAP，需要车机设置下拉两次开启 AP
- 实现：截图新增项，本包无字段。行为描述与「自动补一次下拉操作」相似，可能与 oneClickOpenAP 共用拨杆帧路径。
- 来源：截图 4
- 接口：`POST /api/feifan/config（待核对）`

#### `a2e` 一键 AP · One-tap AP

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：自动补一次下拉操作，实现变道时不降速
- 实现：字段 oneClickOpenAP：byte31 >>> 3 & 1。写入走 CMD 0xA3 整块回写。
- 来源：SETTINGS 表 / apHelper.js:73
- 接口：`POST /api/feifan/config {id:'oneClickOpenAP'}`

#### `a2f` AP 自动恢复 · AP auto resume

- 类型：**分段选择** · 证据：**A** · 状态：已有
- 说明：退出 AP 后自动恢复
- 实现：字段 apAutoOpenType：byte28 >>> 1 & 3。P4 已有 continuous_ap_fsm_pure.h / continuous_ap_runtime.h（Continuous AP）等价状态机，可做映射而非重写。
- 来源：SETTINGS 表 / apHelper.js:41
- 接口：`映射现有 Continuous AP 设置`
- 取值：`0` 关闭 / `1` 双击右滚轮 / `2` 下拉档杆 / `3` 跟随AP

#### `a2g` AP 恢复延时 · AP resume delay

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：AP 恢复触发后的等待时间（0–7 秒）
- 实现：字段 apAutoOpenTime：byte30 >>> 1 & 7。这个字段只在「参数配置」页出现，截图里没画出来，属于逆向额外挖到的隐藏项。
- 来源：SETTINGS 表 / apHelper.js:53
- 接口：`POST /api/feifan/config {id:'apAutoOpenTime'}`
- 取值：`0` 立即 / `1` 1秒 / `2` 2秒 / `3` 3秒 / `4` 4秒 / `5` 5秒 / `6` 6秒 / `7` 7秒

#### `a2h` 开启手动远光 · Manual high beam

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：AP 模式下开启手动远光灯
- 实现：字段 apHighBeam：byte31 >>> 4 & 3（0 关闭 / 1 老-AP手动远光 / 2 新-随心远光）。
- 来源：SETTINGS 表 / apHelper.js:107
- 接口：`POST /api/feifan/config {id:'apHighBeam'}`
- 取值：`0` 关闭 / `1` 老款 / `2` 焕新版

#### `a2i` AP 超速退出 · AP overspeed exit

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：超速时退出 AP 辅助功能
- 实现：字段 apOverspeedExit：byte34 >>> 0 & 1。
- 来源：SETTINGS 表 / apHelper.js:77
- 接口：`POST /api/feifan/config {id:'apOverspeedExit'}`

#### `a2j` 关闭自动雨刮 · Disable auto wiper in AP

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：AP 模式下关闭自动雨刮
- 实现：字段 OffAPAutoWiper：byte25 >>> 7 & 1。
- 来源：SETTINGS 表 / apHelper.js:103
- 接口：`POST /api/feifan/config {id:'OffAPAutoWiper'}`

### 4.3 EAP 设置 / EAP settings

#### `a3a` EAP 增强 · EAP enhanced

- 类型：**开关** · 证据：**A** · 状态：已有
- 说明：开启自动打转向灯，打转向灯自动变道
- 实现：字段 id 就叫 fsd：byte28 >>> 5 & 1（SETTINGS 里名字是「EAP辅助」，apHelper 里叫「EAP增强」）。P4 的 Advanced EAP / auto_blinker_pure.h 是等价实现。
- 来源：SETTINGS 表 / apHelper.js:83
- 接口：`映射现有 Advanced EAP 端点`

#### `a3b` EU 召唤解锁 · EU summon unlock

- 类型：**分段选择** · 证据：**B** · 状态：已有
- 说明：关闭 / 模式二(保留 bit18) / 模式一(清 bit18)
- 实现：截图新增项，本包无字段。P4 侧已有 R79 固定策略：UI_applyEceR79 bit19 强制 0、UI_hardCoreSummon bit47 强制 1、SmartSummonOnly bit18 可选 FORCE 0 / STOCK（r79_fixed_policy_pure.h），与截图描述完全对应，直接映射即可。
- 来源：截图 4 / P4can r79_fixed_policy_pure.h
- 接口：`映射现有 /api/r79 设置`
- 取值：`0` 关闭 / `1` 模式二 / `2` 模式一

#### `a3c` 变道激进度 · Lane-change aggressiveness

- 类型：**分段选择** · 证据：**B** · 状态：需新增
- 说明：温和(默认) / 适中 / 激进 / 保持原厂
- 实现：截图新增项，本包无字段。推断为 0x3F8 / 0x293 相关参数或配置块 2bit 枚举；需新版小程序或实车抓包。
- 来源：截图 4
- 接口：`POST /api/feifan/config（待核对）`
- 取值：`0` 温和 / `1` 适中 / `2` 激进 / `3` 保持原厂

#### `a3d` 召唤心跳 (LAB) · Summon heartbeat (LAB)

- 类型：**开关** · 证据：**B** · 状态：已有
- 说明：实验功能，手动覆盖召唤心跳值
- 实现：截图新增 LAB 项。P4 已有 panelLabSummonHeartbeat（0x3F8 UI_driverAssistControl / UI_summonHeartbeat bits 2-3，raw 0-3），可直接映射。
- 来源：截图 5 / P4can dashboard_source.html panelLabSummonHeartbeat
- 接口：`映射现有 LAB endpoint`

#### `a3e` 召唤心跳值 (LAB) · Summon heartbeat value

- 类型：**分段选择** · 证据：**B** · 状态：已有
- 说明：0 / 1 / 2(默认) / 3
- 实现：同上，2bit 值直接对应 0x3F8 的 UI_summonHeartbeat。
- 来源：截图 5 / P4can panelLabSummonHeartbeat
- 接口：`映射现有 LAB endpoint`
- 取值：`0` 0 / `1` 1 / `2` 2 默认 / `3` 3

### 4.4 FSD 设置 / FSD settings

#### `a4a` FSD 激活 · FSD activation

- 类型：**开关** · 证据：**B** · 状态：不可达
- 说明：激活已购买的 FSD 功能
- 实现：截图项。本包 apHelper 的 FSD 分组里所有条目都标了 uiOnly:true，点击只弹「固件不支持」，既没有 bit 也没有 CMD。注意： entitlement / 订阅校验不在模块能力范围，开源三仓库都明写需要有效 EAP/FSD 订阅，P4 侧也不做授权破解。
- 来源：截图 5 / apHelper.js:196-233 / 三个开源仓库 README
- 接口：`（不接入）`

#### `a4b` 硬件模式 · Hardware mode

- 类型：**分段选择** · 证据：**C** · 状态：本地 UI
- 说明：车辆类型切换 HW3 / HW4
- 实现：本包对应项 fsdHwMode 是 uiOnly（自动检测 / HW3 / HW4 / 旧版），纯 UI 占位。P4 有 vehicle profile，但那是车型拓扑，不是 FSD 硬件授权模式，不要混为一谈。
- 来源：截图 5 / apHelper.js:202
- 接口：`（不接入）`
- 取值：`1` HW3 / `2` HW4

#### `a4c` 紧急车辆避让 · Emergency vehicle avoidance

- 类型：**开关** · 证据：**B** · 状态：需新增
- 说明：HW4 专属，需车型 HW4 且 AP 激活
- 实现：截图新增项；ev-open-can-tools-plugins 里有 emergency-vehicle-detection-hw4.json 示例规则可作参考，但它属于插件规则层，不保证与 TSL 行为一致。
- 来源：截图 5 / evoct-plugins HW4
- 接口：`POST /api/feifan/config（待核对）`

#### `a4d` 车道线可视化 · Lane line visualisation

- 类型：**开关** · 证据：**B** · 状态：需新增
- 说明：AP 激活时显示车道线
- 实现：截图新增项，推断为车机显示相关的配置位，需抓包。
- 来源：截图 5
- 接口：`POST /api/feifan/config（待核对）`

#### `a4e` 导航 FSD 线路 · Navigation FSD route

- 类型：**开关** · 证据：**B** · 状态：需新增
- 说明：导航时显示 FSD 线路
- 实现：截图新增项，推断为车机显示相关的配置位，需抓包。
- 来源：截图 5
- 接口：`POST /api/feifan/config（待核对）`

#### `a4f` AP-First 模式 · AP-First mode

- 类型：**开关** · 证据：**B** · 状态：已有
- 说明：优先维持 AP
- 实现：截图新增项；P4 有 continuous_ap_runtime.h / AP-First 相关门控与 Pause TLSSC During NOA，语义接近，需实车核对后再映射。
- 来源：截图 5 / P4can 源码
- 接口：`映射现有 Continuous AP 设置`

#### `a4g` Autopark 拦截 · Autopark interception

- 类型：**开关** · 证据：**B** · 状态：需新增
- 说明：泊车时暂停模块注入
- 实现：截图新增项。属于注入总闸的联动条件：检测到泊车状态时应暂停所有周期性注入。P4 已有 runtime_gate_pure.h 与 park-state 监控（summon_state_pure.h），加一个 gate 条件即可。
- 来源：截图 5 / P4can runtime_gate_pure.h
- 接口：`POST /api/feifan/config（gate 条件）`

#### `a4h` 本包 FSD 分组占位说明 · Placeholder note

- 类型：**只读信息** · 证据：**C** · 状态：本地 UI
- 说明：FSD 改装 / 中国模式 / 抑制 ISA / 抑制转向提醒 / 速度偏移 / 速度来源 / 速度档位
- 实现：这 8 项在 app-service.main.js 的 apHelper 页里全部带 uiOnly:true，toggleConfig/selectOption/inputConfig 都会走 lockFsdToast() 弹「固件不支持」或「需要连接模块」，不产生任何 BLE 写入。截图里能操作说明用户看到的是更新版小程序/固件。做 P4 页面时建议保留这一组但默认禁用并明确标注，避免误以为已实现。
- 来源：apHelper.js:196-233, :429 lockFsdToast
- 接口：`（不接入）`

## 5. 车身与开合 / Body & latches

> 车门锁扣、开合状态、提醒与滚轮模拟

### 5.1 车身开合 / Latches

#### `b1a` 车身示意图 · Body diagram

- 类型：**只读信息** · 证据：**B** · 状态：需新增
- 说明：点击车身部位切换开合；中控锁支持解锁 / 锁定
- 实现：截图里的车形热区是 WXML 的 dataset.key / dataset.code。点击后先本地反转 bodyState[key]，再发 CMD 0xA7 + 1 字节动作码；失败时回滚本地状态。本 APK 只解出 app-service.js，未含 WXML，故各部位具体 code 未逐项确认。
- 来源：vehicleControl.js:178 sendBodyPart
- 接口：`POST /api/feifan/action`

#### `b1b` 车门 / 前后备箱 / 后视镜 · Doors, frunk, trunk, mirrors

- 类型：**网格按钮** · 证据：**B** · 状态：不可达
- 说明：前备箱、后备箱、左前门、右前门、左后门、右后门、后视镜折叠
- 实现：同样是 CMD 0xA7 单字节动作码。状态回显不靠这些按钮，而是 CMD 0xB0 (176) 仪表帧解析出 doorList[0..3] / frunkIsOpen / trunkIsOpen 后重建 bodyState。注意：这类车身/座舱执行器在 TSL 上多走车身以太网或专用总线，P4 三路 CAN 收发器物理够不到，换固件也解决不了。
- 来源：vehicleControl.js:116 buildBodyStateFromGauge / :133 handleGaugePacket
- 接口：`GET /api/feifan/gauge`
- 取值：`frunk` 前备箱 / `trunk` 后备箱 / `lf` 左前门 / `rf` 右前门 / `lr` 左后门 / `rr` 右后门 / `mirror` 后视镜折叠

#### `b1c` 中控锁 · Central lock

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：解锁 / 锁定，发送后本地立刻更新 locked 状态
- 实现：CMD 0xA7 (167)，payload = [动作码]；code 23 解锁、22 锁定，成功 Toast 分别为「解锁成功 / 锁定成功」。这是全部车控里唯一在 JS 里写死、可确证的 code 对。
- 来源：vehicleControl.js:208 sendCarLock
- 接口：`POST /api/feifan/action {code:22|23}`
- 取值：`23` 解锁 / `22` 锁定

#### `b1d` 车身状态回显 · Body state feedback

- 类型：**只读信息** · 证据：**A** · 状态：已有
- 说明：门 / 盖开合由周期性仪表帧驱动，不是按钮回包
- 实现：onLoad 注册 app.onPacket(176, handleGaugePacket)，用 parseGaugeFrame 解析出 doorList / frunk / trunk；页面 onShow 还会 acquire 一次仪表快照。P4 侧已有三路 CAN RX 分发与状态缓存，接一个解析函数即可。
- 来源：vehicleControl.js:93 / :116 / :129
- 接口：`GET /api/feifan/gauge`

#### `b1e` 门把手开关前备箱 · Handle opens frunk

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：按住门把手多久触发前备箱，单位秒
- 实现：配置位域 TimeOpenFrontBox，byte29 >>> 2 & 7。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 TimeOpenFrontBox
- 接口：`POST /api/feifan/config`
- 取值：`0` 关闭 / `1` 1 秒 / `2` 2 秒 / `3` 3 秒

#### `b1f` 门把手开关充电口 · Handle opens charge port

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：按住门把手多久触发充电口盖
- 实现：配置位域 TimeOpenChargeDoor，byte29 >>> 5 & 7。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 TimeOpenChargeDoor
- 接口：`POST /api/feifan/config`
- 取值：`0` 关闭 / `1` 1 秒 / `2` 2 秒 / `3` 3 秒

### 5.2 提醒与显示 / Alerts & display

#### `b5a` 主驾安全带提醒 · Driver belt reminder

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：关闭后主驾不系安全带不再提示。台架必需，上路别关
- 实现：配置位域 frontLeftBuckle，byte34 >>> 1 & 1。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。注意：这条不影响 d2b 换挡安全门，那个读的是真实安全带状态。
- 来源：TSL SETTINGS 位域 frontLeftBuckle
- 接口：`POST /api/feifan/config`

#### `b5b` 副驾安全带提醒 · Passenger belt reminder

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：副驾安全带提示开关
- 实现：配置位域 frontRightBuckle，byte34 >>> 2 & 1。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 frontRightBuckle
- 接口：`POST /api/feifan/config`

#### `b5c` 后排安全带提醒 · Rear belt reminder

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：后排安全带提示开关
- 实现：配置位域 rearBuckle，byte34 >>> 3 & 1。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 rearBuckle
- 接口：`POST /api/feifan/config`

#### `b5d` 提示音音量 · Chime volume

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：车辆提示音整体音量
- 实现：配置位域 beep，byte26 >>> 0 & 255。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。八比特，原版给的是 0-255 的直通值。
- 来源：TSL SETTINGS 位域 beep
- 接口：`POST /api/feifan/config`
- 取值：`0` 静音 / `1` 低 / `2` 中 / `3` 高

#### `b5e` LED 灯开关 · LED switch

- 类型：**开关** · 证据：**A** · 状态：需新增
- 说明：车内 LED 照明总开关
- 实现：配置位域 led，byte27 >>> 4 & 1。读：0xAB 整块回包后按位取；写：先清位再或入，最后 CMD 0xA3 整块回写。
- 来源：TSL SETTINGS 位域 led
- 接口：`POST /api/feifan/config`

### 5.3 模拟滚轮 / Scroll wheel

#### `b4a` 当前操作滚轮 · Active wheel

- 类型：**分段选择** · 证据：**C** · 状态：本地 UI
- 说明：左滚轮 / 右滚轮切换（纯前端选中态）
- 实现：仅 changeWheelSide 改 wheelSide / wheelSideLabel，用来选择查哪张键值表，不发给模块。
- 来源：vehicleControl.js:315
- 接口：`（前端本地）`
- 取值：`left` 左滚轮 / `right` 右滚轮

#### `b4b` 五向按键（左滚轮） · Left wheel keys

- 类型：**网格按钮** · 证据：**A** · 状态：需新增
- 说明：上 / 下 / 左 / 右 / 确认
- 实现：CMD 0xBB (187) + [value]，value 来自 WHEEL_ACTIONS.left。180ms 按键高亮，150ms 内重复触发节流（连续 3 次提示「操作过快」）。P4 已有 0x249 拨杆帧合成与 TX 仲裁设施，滚轮按键帧需另按目标车型实车抓包确认。
- 来源：WHEEL_ACTIONS (A1604D07) / vehicleControl.js:320
- 接口：`POST /api/feifan/action {wheel:'left',direction}`
- 取值：`141` 上 / `142` 下 / `143` 左 / `144` 右 / `140` 确认

#### `b4c` 五向按键（右滚轮） · Right wheel keys

- 类型：**网格按钮** · 证据：**A** · 状态：需新增
- 说明：车速 / 车距 / 一键最高限速
- 实现：CMD 0xBB + WHEEL_ACTIONS.right 的 value。免打扰策略的「加减」其实就是反复发 up/down 这两个值，靠定时与随机化模拟人手拨轮。
- 来源：WHEEL_ACTIONS (A1604D07)
- 接口：`POST /api/feifan/action {wheel:'right',direction}`
- 取值：`146` 上 / `147` 下 / `148` 左 / `149` 右 / `24` 确认

## 6. 仪表与快捷 / Gauges & shortcuts

> 实时数据、胎压与一键快捷

### 6.1 仪表盘 / Gauges

#### `h1a` 实时数据 · Live telemetry

- 类型：**只读信息** · 证据：**A** · 状态：已有
- 说明：总压 / 电流 / 温度 / SOC / 剩余里程 / 总里程
- 实现：CMD 0xB0 (176) 周期仪表帧，parseGaugeFrame 解析后写入 status / health；首页还有 homeHealthSnapshot 本地缓存与「线束未插好」告警位。P4 已有三路 CAN RX 与仪表风格的 HOME 页，接字段映射即可。
- 来源：pages/index/index.js / F8FB8B01 gauge 解析模块
- 接口：`GET /api/feifan/gauge`

#### `h1b` 仪表盘自动启动 · Auto-start gauge

- 类型：**开关** · 证据：**C** · 状态：本地 UI
- 说明：进入 App 自动打开仪表盘
- 实现：本地 storage key isAutoGauge，只控制前端跳转，不下发模块。
- 来源：pages/index/index.js o="isAutoGauge"
- 接口：`（前端本地）`

#### `h1c` TPMS 信息 · TPMS

- 类型：**只读信息** · 证据：**B** · 状态：需新增
- 说明：直读蓝牙胎压传感器，四轮胎压 / 温度
- 实现：pages/tpms/tpms.js 有独立页面与四轮数据模型；现代特斯拉用 BLE 胎压传感器，需要 P4 的 BLE 主机扫描与解析，属于新增能力，不是 CAN 帧。
- 来源：pages/tpms/tpms.js / pages/set/set.js
- 接口：`GET /api/feifan/tpms（建议新增）`

### 6.2 快捷动作 / Shortcuts

#### `h2a` 灯光 / 喇叭快捷 · Light & horn quick actions

- 类型：**网格按钮** · 证据：**A** · 状态：需新增
- 说明：前爆闪 / 后爆闪 / 脉冲喇叭 / 领航模式
- 实现：首页 quickActions 映射表 {frontStrobe:91, rearStrobe:94, pulseHorn:90, rearFog:95}，点击 runQuickCommand 发 CMD 0xBB (187) + [value] 并切换 active 态。配置块里还有对应的速度档：pluseHighBeam byte25>>0&3、pluseHorn byte27>>6&3 等。注意灯光爆闪在公共道路属于滥用灯光与非法改装，仅封闭场地。
- 来源：pages/index/index.js:660 / SETTINGS 表
- 接口：`POST /api/feifan/action {quick}`
- 取值：`91` 前爆闪 / `94` 后爆闪 / `90` 脉冲喇叭 / `95` 领航模式

#### `h2b` 电池预热 · Battery preheat

- 类型：**分段选择** · 证据：**A** · 状态：需新增
- 说明：开启 / 关闭（带确认弹窗）
- 实现：CMD 0xBB + [29] 开启 / [28] 关闭；开启前 wx.showModal 二次确认。
- 来源：pages/index/index.js:11941 toggleBatteryHeat
- 接口：`POST /api/feifan/action`
- 取值：`29` 开启 / `28` 关闭

#### `h2c` 模块开关 · Module switch

- 类型：**分段选择** · 证据：**A** · 状态：已有
- 说明：一键启停模块全部注入
- 实现：CMD 0xBB + [251 | 252]；配置块里还有模块总开关 mianSwitch byte28>>3&1。P4 已有 LAB 总闸 / runtime gate，建议把它做成页面顶部的「总闸」而不是普通开关。
- 来源：pages/index/index.js runModuleSwitch / SETTINGS 表
- 接口：`映射到现有总闸端点`
- 取值：`251` 停用 / `252` 启用

### 6.3 常用与配置块 / Common & blobs

#### `h3a` 功能入口 · Feature entries

- 类型：**只读信息** · 证据：**C** · 状态：本地 UI
- 说明：车辆控制 / 辅助驾驶 / 模块设置 / 快捷指令 / 高级功能
- 实现：首页 features3 / features2 只是小程序路由表，对应本页的四个分组。P4 侧用底部导航或页面内锚点即可。
- 来源：pages/index/index.js
- 接口：`（前端路由）`

#### `h3b` 快捷指令 · Shortcut commands

- 类型：**只读信息** · 证据：**A** · 状态：需新增
- 说明：绑定按键和功能；256 字节配置块同步
- 实现：CMD 0xAB (171) 读写快捷指令配置块，页面提示「未收到 256 字节配置回包」；scene / gaugeMenu 页也走 171。蓝牙按钮配置是 CMD 0xBA (186) 回包。P4 要做可复用一个通用的 256B blob 存取端点。
- 来源：pages/shortcut/shortcut.js / pages/scene/scene.js / pages/bleBtn/bleBtn.js
- 接口：`GET/POST /api/feifan/blob?name=shortcut`

#### `h3c` 蓝牙按钮 · BLE buttons

- 类型：**只读信息** · 证据：**A** · 状态：已有
- 说明：外部蓝牙按键搜索、配对、绑定动作
- 实现：CMD 0xF0 (240) 主机配对 / 0xBA (186) 配置同步。P4 已内置 s3xy_ble.h（最多 3 个 S3XY 按钮、绑定与动作映射），可直接映射。
- 来源：pages/bleHost/bleHost.js / P4can s3xy_ble.h
- 接口：`映射现有 S3XY 端点`

## 7. 模块设置 / Module settings

> 外观、模块维护与参数备份

### 7.1 通用设置 / General

#### `s1a` 深色模式 · Dark mode

- 类型：**开关** · 证据：**C** · 状态：本地 UI
- 说明：全局霓虹深色主题
- 实现：小程序本地 settings + resolveThemeClass，只改 CSS class。P4 的 dashboard 已有 p4canDashboardTheme（system/light/dark），直接复用现有主题开关，不要重复做。
- 来源：pages/set/set.js / dashboard_source.html:12-27
- 接口：`（复用现有主题设置）`

#### `s1b` 跟随系统 · Follow system

- 类型：**开关** · 证据：**C** · 状态：本地 UI
- 说明：随手机深色 / 浅色自动切换
- 实现：同上，matchMedia('(prefers-color-scheme: dark)')。
- 来源：dashboard_source.html:13
- 接口：`（复用现有主题设置）`

#### `s1c` 自动深色 · Scheduled dark

- 类型：**开关** · 证据：**C** · 状态：本地 UI
- 说明：18:00 - 06:00 自动切换
- 实现：截图新增项，本包只有跟随系统；按时间段切换属前端定时器，P4 若做需本地时钟（NTP/浏览器时间）。
- 来源：截图 7
- 接口：`（前端本地）`

#### `s1d` 字体大小 · Font size

- 类型：**数值** · 证据：**C** · 状态：本地 UI
- 说明：全局界面缩放（截图值 20）
- 实现：本地 settings.fontSize，各页 syncFontSize 读取后改根节点字号。P4 中文语言版可把「语言选择 + 字号」放在同一张外观卡里。
- 来源：pages/set/set.js / apHelper.js syncFontSize
- 接口：`（前端本地）`

### 7.2 功能模块 / Modules

#### `s2a` 显示与仪表 · Display & gauge

- 类型：**只读信息** · 证据：**C** · 状态：本地 UI
- 说明：显示与仪表盘的设置
- 实现：路由到 gaugeMenu 页；该页大量设置走 CMD 0xAB 171 配置块（仪表外观、布局、背景、自定义文案）。
- 来源：pages/set/set.js / pages/gaugeMenu/gaugeMenu.js
- 接口：`GET/POST /api/feifan/blob?name=gauge`

#### `s2b` 备份恢复 · Backup & restore

- 类型：**只读信息** · 证据：**B** · 状态：需新增
- 说明：数据备份与恢复
- 实现：pages/backup/backup.js 有「上次操作已中断 / 未备份 / 已备份」状态，导出导入的是配置块与本地设置的打包。P4 可做成 /api/feifan/backup 的 JSON 导出导入。
- 来源：pages/backup/backup.js / pages/my/my.js
- 接口：`GET/POST /api/feifan/backup（建议新增）`

#### `s2c` 维护模式 · Service mode

- 类型：**只读信息** · 证据：**A** · 状态：需新增
- 说明：车辆进入维护模式（需安全静止）
- 实现：CMD 0xA7 (167) + [255]，发送前 wx.showModal 警告「车辆必须处于安全静止状态」。高级功能页也用同一个 255。
- 来源：pages/set/set.js:3356 / pages/advanced/advanced.js:7121
- 接口：`POST /api/feifan/action {code:255}`

#### `s2d` 参数配置 · Parameter config

- 类型：**只读信息** · 证据：**A** · 状态：需新增
- 说明：模块后台操作（完整位域表）
- 实现：所有位域设置最终都走 writeConfigBytes -> CMD 0xA3 (163) 整块回写；读由 CMD 0xA0/0xA1/0xA3 回包同步到 globalData.configBytes（≥35 字节）。下方「集成清单」有 32 个已确证字段。
- 来源：app-service.main.js:239841 / SETTINGS 表
- 接口：`GET/POST /api/feifan/config`

#### `s2e` 恢复默认 · Factory reset

- 类型：**只读信息** · 证据：**A** · 状态：已有
- 说明：模块恢复出厂设置
- 实现：CMD 0xA4 (164)，payload = getUid(deviceInfo)（UID 字节）。P4 已有多级重置（Firmware Settings / Bluetooth Data / Factory Reset），注意对齐语义。
- 来源：pages/set/set.js:3881 / P4can 现有 reset 端点
- 接口：`映射现有 reset 端点`

### 7.3 高级功能 / Advanced

#### `s3a` 实验动作 · Lab actions

- 类型：**网格按钮** · 证据：**B** · 状态：不可达
- 说明：漂移模式 / 关闭前电机 / 关闭后电机 / 重启模块
- 实现：pages/advanced/advanced.js 的实验动作走 CMD 0xA5 (165) 自定义 payload 与 CMD 0xA7 (167)；涉及动力/驱动单元，风险最高，本页只保留菜单不接后端。
- 来源：pages/advanced/advanced.js:4651 / :5200 / :6660
- 接口：`（不接入）`
- 取值：`drift` 漂移模式 / `frontOff` 关闭前电机 / `rearOff` 关闭后电机 / `reboot` 重启模块

#### `s3b` 模块总开关 · Master switch

- 类型：**开关** · 证据：**A** · 状态：已有
- 说明：一键启停模块全部功能
- 实现：配置块 mianSwitch：byte28 >>> 3 & 1；与首页 CMD 0xBB 251/252 是两条路径。P4 建议统一到一个总闸，避免两套状态打架。
- 来源：SETTINGS 表 / pages/index/index.js
- 接口：`映射到现有总闸端点`

## 8. 集成清单 / Integration notes

> 命令表、位域、端点与刷写步骤

本组为追溯清单，内容见 `docs/REVERSE.md`。

