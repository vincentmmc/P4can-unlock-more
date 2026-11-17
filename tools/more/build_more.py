#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild feifan-menu-data.json into the 'More features' layout.

Sources merged
--------------
1. TSL mini-program reverse engineering  -> the 44 SETTINGS bit-fields plus the
   0xA7 / 0xBB command tables (evidence A: bit offsets read straight from the
   decompiled SETTINGS array, so they are exact).
2. Albert-P4-P1.6.4 firmware dashboard   -> element ids scraped out of the gzip
   page embedded in Albert-P4-P1.6.4-V3.2-c565dc82-OTA.bin (evidence A).
3. The two P4CAN FUSION design mock-ups  -> ids/claims marked evidence B. These
   are *not* free-standing frames: several turn out to be the same behaviour as
   an existing TSL bit-field and are folded into it.

Dedup rules applied
-------------------
* 滚轮挂挡 (design, "Albert 0x229") is one input mode of 自动换挡 -> folded into d2.
* 开启自动变道 (a2c) and 打灯变道 (design, "P4can 0x293") are one feature
  -> moved to d1b, removed from a2.
* 氛围灯 (design) == 常亮氛围灯 (ambientEnabled); 迎宾灯光 (design) == 迎宾灯效
  -> kept once each under l4.
* 脉冲远光 (design "0x249") / 脉冲喇叭 (design "0x10C") / 刹车灯爆闪 (design
  "0x3E2/0x3E3") are really the TSL bit-fields pluseHighBeam / pluseHorn /
  dynamicBrakeLight. Those frame ids exist in neither codebase, so the
  bit-field description wins; the frame id stays only as a footnote.
* 电池预热 already lives in the one-tap bar (h2b) -> not repeated in comf.
* 座椅/记忆 (b2*), 空调烘干 (b3a) moved into 舒适与座椅.
"""
import copy
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / 'data' / 'feifan-menu-data.json'
BAK = REPO / 'data' / 'feifan-menu-data.pre-more.bak.json'

data = json.loads(SRC.read_text(encoding='utf-8'))

# ---------------------------------------------------------------- index old
old_groups = {g['id']: g for g in data['groups']}
old_items = {}
for g in data['groups']:
    for s in g['sections']:
        for i in s['items']:
            old_items[i['id']] = i

total_old = len(old_items)
print('loaded %d groups / %d items' % (len(old_groups), total_old))


def it(**kw):
    base = dict(id='', n='', en='', d='', t='sw', lv='B', p4='需新增',
                im='', src='', api='POST /api/feifan/action')
    base.update(kw)
    return base


def opts(pairs):
    return [{'v': str(v), 'l': l} for v, l in pairs]


def take(item_id, **override):
    c = copy.deepcopy(old_items[item_id])
    c.update(override)
    return c


def fld(fid, n, en, d, pairs, field, bit, extra=''):
    """One of the 44 SETTINGS bit-fields: evidence A, written via CMD 0xA3."""
    item = it(id=fid, n=n, en=en, d=d, lv='A', p4='需新增',
              im=('配置位域 %s，byte%d >>> %d & %d。读：0xAB 整块回包后按位取；'
                  '写：先清位再或入，最后 CMD 0xA3 整块回写。%s'
                  % (field, bit[0], bit[1], bit[2], extra)),
              src='TSL SETTINGS 位域 %s' % field, api='POST /api/feifan/config')
    if pairs:
        item['t'] = 'seg'
        item['o'] = opts(pairs)
    return item


# =====================================================================  drv
drv_d1 = [
    it(id='d1a', n='Nag Killer 抑制', en='Nag Killer suppression',
       d='扭矩回显 0x370，Nag Burst 按需脉冲；纠正扭矩、帧数、暂停时长可调，今日已消次数回显',
       t='sw', lv='A', p4='已有',
       im='P4-CAN 已内置 Nag Killer（web_api.h 里 Nag 相关实现 122 处，状态页已有实时计数），'
          '本页只做开关与参数映射，不重复实现。设计图标的「Flipper 算法」在这里落到 P4 现有 nag 配置。',
       src='web_api.h:1461 / vehicle_logic.h', api='POST /api/feifan/config'),
    it(id='d1b', n='打灯变道', en='Turn-signal lane change',
       d='打灯触发变道；CHASSIS 读 0x399 DAS 状态作为 AP 激活门。须已有 EAP/FSD 订阅',
       t='sw', lv='A', p4='已有',
       im='P4 已有 0x293 注入（vehicle_logic.h LAB 段 7 处），设计图标注的「P4can 0x293 LAB」'
          '即此项。无订阅时不发帧，开关保持灰态。原 a2c「开启自动变道」与它是同一个功能，已合并到此处。',
       src='vehicle_logic.h:0x293', api='POST /api/feifan/config'),
    it(id='d1c', n='加速模式', en='Acceleration profile',
       d='舒适 / 标准 / 运动三挡，写 0x334 踏板映射',
       t='seg', o=opts([('comfort', '舒适'), ('standard', '标准'), ('sport', '运动')]),
       lv='A', p4='已有',
       im='P4 的 AP Drive Profile 已独占 0x334 出口（web_api.h:3239），与 LAB PedalMap 共用 '
          'UI_powertrainControl 覆盖层，本项做映射即可。注意 Party+Chassis 拓扑没有 0x334 通路。',
       src='vehicle_logic.h:1561', api='POST /api/feifan/config'),
    it(id='d1d', n='赛道模式', en='Track mode',
       d='操控平衡偏后驱、稳定性辅助强度、赛后冷却。非性能版可用，改帧重发会自动重算校验',
       t='seg', o=opts([('off', '关闭'), ('street', '街道'), ('track', '赛道')]),
       lv='B', p4='需新增',
       im='设计图标注「Flipper 0x313，操控平衡 100 / 稳定性辅助 30% / 赛后冷却关」。'
          '0x313 在 Albert 固件与 TSL 小程序里都搜不到，属未验证规格；落地前必须先在台架确认'
          '该帧在本车拓扑上真实存在。真正能落地的运动化入口是 d4 自动运动模式，那个是实锤位域。',
       src='设计图 P4CAN FUSION', api='POST /api/feifan/config'),
    it(id='d1e', n='TLSSC 限速跟随', en='TLSSC speed follow',
       d='0x331 恢复在 2026.14+ 车机固件下已失效，开关仅保留代码与状态显示',
       t='sw', lv='B', p4='需新增',
       im='设计图标注「已堵 · 2026.14+ 封」。TSL 侧 0x331 注入被车机加了校验，恢复后无效。'
          '本项如实标为不可用，不做「能开」的假承诺。',
       src='设计图 P4CAN FUSION', api='POST /api/feifan/config'),
    it(id='d1f', n='AP-First 注入顺序', en='AP-First injection order',
       d='任何注入之前先确认 AP 已接管，否则整包不发；Abort Guard 在 DAS 进入 ABORTING 时立即停发',
       t='sw', lv='B', p4='需新增',
       im='设计图底栏的三层安全：AP-First（AP 接管后才允许注入）、Abort Guard（DAS 进入 ABORTING '
          '立即停发）、OTA 检测（升级中全停）。任一层不过就不发帧并记入诊断日志。'
          'P4 侧可复用现有 AP gate 状态机。',
       src='设计图 P4CAN FUSION', api='POST /api/feifan/config'),
]

drv_d2 = [
    it(id='d2a', n='启用自动换挡', en='Auto shift',
       d='支持滚轮、刹车＋方向盘、障碍物三种换挡入口，默认关闭',
       t='sw', lv='A', p4='需新增',
       im='Albert 固件 gearAutomationEnabled，默认关闭。原文：「支持滚轮、刹车方向盘和障碍物换挡」。'
          '设计图里的「滚轮挂挡 Albert 0x229」是本功能的四方向输入之一，不是独立功能，已合并到此处。',
       src='Albert dashboard #gearAutomationEnabled', api='POST /api/feifan/config'),
    it(id='d2b', n='换挡前必须系安全带', en='Seatbelt gate',
       d='读原车 0x145 刹车与 PARTY 0x30A 主驾安全带，两者都要连续 2 帧确认；进 P 挡不受此门限制',
       t='sw', lv='A', p4='需新增',
       im='gearSeatbeltSafetyEnabled，出厂默认勾选。「驾驶位有人与安全带模拟」不会绕过本机读取的'
          '真实安全带状态，这是原版明确写的。',
       src='Albert dashboard #gearSeatbeltSafetyEnabled', api='POST /api/feifan/config'),
    it(id='d2c', n='换挡次数（单次刹车周期）', en='Shifts per brake cycle',
       d='0 表示不限；每次进入速度范围重新计数',
       t='seg', o=opts([('0', '不限'), ('3', '3 次'), ('6', '6 次'), ('10', '10 次')]),
       lv='A', p4='需新增',
       im='gearShiftLimit，原版范围 0-255，默认 0。开启「关闭刹车安全门」后本项一并失效。',
       src='Albert dashboard #gearShiftLimit', api='POST /api/feifan/config'),
    it(id='d2d', n='允许换挡速度上限', en='Shift speed gate',
       d='按真实速度整数部分判断，0 表示低于 1 km/h；连续 2 帧满足才开放',
       t='seg', o=opts([('0', '< 1 km/h'), ('1', '< 2 km/h'), ('2', '< 3 km/h'), ('3', '< 4 km/h')]),
       lv='A', p4='需新增',
       im='gearAutoShiftMaxSpeedKph，原版 0-8。连续两帧判定是为了避免边界抖动卡住体验。',
       src='Albert dashboard #gearAutoShiftMaxSpeedKph', api='POST /api/feifan/config'),
    it(id='d2e', n='动作冷却', en='Shift cooldown',
       d='两次换挡之间的最小间隔',
       t='seg', o=opts([('100', '100 ms'), ('300', '300 ms'), ('500', '500 ms'), ('1000', '1000 ms')]),
       lv='A', p4='需新增',
       im='gearCooldownMs，原版 100-5000，步进 50。',
       src='Albert dashboard #gearCooldownMs', api='POST /api/feifan/config'),
    it(id='d2f', n='刹车＋方向盘确认', en='Brake + steering confirm',
       d='P 挡左转进 D、右转进 R；D/R 挡向任意方向超过阈值即互换',
       t='sw', lv='A', p4='需新增',
       im='gearBrakeToggleEnabled。速度门满足且刹车按下时取当前方向盘角度为基线；掉出再进入会重新'
          '取基线，取基线时角度无效则继续等待。方向按相对基线的瞬时角度判断，不做左右累计。',
       src='Albert dashboard #gearBrakeToggleEnabled', api='POST /api/feifan/config'),
    it(id='d2g', n='D/R 挡转向阈值', en='Steering threshold',
       d='方向盘相对基线转动多少度触发互换',
       t='seg', o=opts([('60', '60°'), ('90', '90°'), ('120', '120°'), ('180', '180°')]),
       lv='A', p4='需新增',
       im='gearDriveReverseSteeringThresholdDeciDeg，原版 1-360，默认 120。',
       src='Albert dashboard #gearDriveReverseSteeringThresholdDeciDeg', api='POST /api/feifan/config'),
    it(id='d2h', n='障碍物换挡', en='Obstacle shift',
       d='读 PARTY 2/3 路 0x255 挡位建议与 0x12B 扭矩方向，只在 P 挡处理',
       t='sw', lv='A', p4='需新增',
       im='进 D/R 或挡位过期会清空数据；回到 P 后必须重新收到两帧新数据。方向盘角度确认开启时，'
          'D 建议要求左转、R 建议要求右转。',
       src='Albert dashboard #gearObstacleNested', api='POST /api/feifan/config'),
    it(id='d2i', n='滚轮换挡方向映射', en='Wheel shift mapping',
       d='原版四个方向默认均为无动作，需逐项指定',
       t='seg', o=opts([('none', '无动作'), ('ud', '上下'), ('lr', '左右'), ('all', '四向')]),
       lv='A', p4='需新增',
       im='设计图的「滚轮挂挡 Albert 0x229」即这里的输入源。P4 侧用 0xBB 模拟滚轮键值注入'
          '（左滚轮 140-144 / 右滚轮 146-149），与 TSL 侧键值表一致。',
       src='Albert dashboard + TSL 0xBB 键值表', api='POST /api/feifan/action'),
    it(id='d2j', n='智能流畅预设', en='Smooth preset',
       d='一键写入 1000 ms · P 30° · D/R 60° · 障碍物 30°',
       t='grid', o=opts([('smooth', '应用预设'), ('default', '恢复默认')]),
       lv='A', p4='需新增',
       im='gearSmoothPreset 一次性写完四项，省得逐个调。默认值是原版的保守组合。',
       src='Albert dashboard #gearSmoothPreset', api='POST /api/feifan/config'),
    it(id='d2k', n='换挡闭环反馈', en='Shift closed loop',
       d='复用原车真实帧发送路径，读 0x118 确认；失败不重发',
       t='info', lv='A', p4='需新增',
       im='原版明确「继续复用真实原帧发送路径和 0x118 反馈确认」。P4 侧 0x118 已有 6 处实现，可直接接。',
       src='Albert dashboard + vehicle_logic.h:0x118', api='GET /api/feifan/status'),
]

drv_d3 = [
    it(id='d3a', n='速度补偿模板', en='Speed offset template',
       d='舒适 / 标准 / 迅捷三套目标速度，另可开 V14 独立模板',
       t='seg', o=opts([('comfort', '舒适'), ('standard', '标准'), ('quick', '迅捷')]),
       lv='A', p4='需新增',
       im='Albert 有「舒适目标速度 / 标准目标速度 / 迅捷目标速度」三组数值，另加「V14 独立速度模板」'
          '与「日常预防扭矩（H0/H1、H2 等待期）」。本项只做模板选择，数值在固件侧落。',
       src='Albert dashboard 驾驶员设置 / FSD 速度补偿', api='POST /api/feifan/config'),
    it(id='d3b', n='V14 独立速度模板', en='V14 separate template',
       d='老版车机与 V14 用不同模板，避免互相覆盖',
       t='sw', lv='A', p4='需新增',
       im='原版按车机版本分流：V12 目标模板、V13 低速后台/高速车机、V14 独立模板。',
       src='Albert dashboard FSD 速度补偿', api='POST /api/feifan/config'),
    it(id='d3c', n='预防扭矩与纠正', en='Preventive torque',
       d='日常预防扭矩 H0/H1、H2 等待期；升级纠正 H2 超时与 H3-H5 帧数',
       t='seg', o=opts([('gentle', '温和'), ('normal', '标准'), ('strong', '加强')]),
       lv='A', p4='需新增',
       im='对应 Nag Killer 的扭矩模型。P4 侧 nag 参数已存在，这里给三档预设，避免用户直接填 Nm。',
       src='Albert dashboard Nag Killer 段', api='POST /api/feifan/config'),
]

drv_d4 = [
    fld('d4a', '自动运动模式', 'Auto sport mode',
        '按驾驶风格自动切运动化响应，三比特共 8 档',
        [('0', '关闭'), ('1', '运动'), ('2', '赛道'), ('3', '自定义')],
        'autoSportMode', (24, 0, 7),
        '这是设计图「赛道模式」真正能落地的那一层：TSL 原生就有这个位域，不用去猜 0x313。'),
    fld('d4b', '能量回收制动', 'Regen braking',
        '回收强度，与原车停止模式配合决定松电门后的减速感',
        [('0', '标准'), ('1', '低'), ('2', '高')],
        'KERS', (24, 5, 7),
        '三比特可取值 0-7，原版 UI 只暴露常用三档。'),
    fld('d4c', '停止模式', 'Stopping mode',
        '缓行 / 保持 / 转动，决定刹停后车辆行为',
        [('0', '缓行'), ('1', '保持'), ('2', '转动')],
        'stoppingMode', (25, 5, 3), ''),
    fld('d4d', '自动强驻车', 'Auto park brake',
        '离车自动上电子手刹',
        None, 'autoParkBrake', (24, 4, 1), ''),
]

# ====================================================================  lamp
lamp_l1 = [
    fld('l1a', '远光爆闪', 'High beam strobe',
        '交替闪远光，档位决定脉冲速度',
        [('0', '关闭'), ('1', '慢'), ('2', '中'), ('3', '快')],
        'pluseHighBeam', (25, 0, 3),
        '设计图把它写成「P4can 0x249」，但 0x249 是 SCCM 拨杆状态帧、只能读不能写；'
        '真正让灯闪的是这个位域，原版就是写配置块，不是发 0x249。'),
    fld('l1b', '近光跟随远光爆闪', 'Low beam follows strobe',
        '爆闪时近光同步亮灭，避免只剩远光孤零零闪',
        None, 'pluseHighBeamAndLowBeam', (25, 2, 1), ''),
    fld('l1c', '远光闪 3 次', 'Triple flash',
        '拉杆触发固定三下远光，超车示意用',
        None, 'blinkHighBeam', (30, 6, 1),
        '与 l1a 的区别：这一项是固定三次、不需要持续按住。'),
    it(id='l1d', n='远近光交替爆闪', en='High/low alternating strobe',
       d='走 DAS_bodyControls 高低 beam 决策位，200 ms 交替。不是 0x249 拨杆帧，不会把灯管成近光',
       t='sw', lv='B', p4='需新增',
       im='设计图标注「0x3E9 DAS」。这点确实关键：拿 0x249 拨杆帧做爆闪，灯光模块会判定为持续拨杆'
          '进而切近光；走 DAS 决策位才能真的闪远光。但 0x3E9 在 Albert 固件里不存在，'
          'Albert 的远光走 0x3C2 Mux1（见下两项）。想要现成可用的，直接用 l1a 位域。',
       src='设计图 P4CAN FUSION', api='POST /api/feifan/action'),
    it(id='l1e', n='强制远光锁存', en='Forced high beam latch',
       d='单次长按 1.5 秒，松开后确认锁存；控制帧 VEH 0x3C2 Mux1',
       t='sw', lv='A', p4='需新增',
       im='Albert fsdForceHighPhysicalEnabled。P4 里 0x3C2 是 VCLEFT 开关帧（无杆转向灯也走它），'
          '做灯光控制必须先锁定 Mux 号，否则会和转向灯打架。',
       src='Albert dashboard #fsdForceHighPhysicalEnabled', api='POST /api/feifan/action'),
    it(id='l1f', n='第二次长按 0.5 秒爆闪', en='Second long-press strobe',
       d='短按一次，第二次长按 0.5 秒；按住持续爆闪，松开立即停止',
       t='sw', lv='A', p4='需新增',
       im='Albert longPressHighBeamStrobeEnabled。手势状态机分短按 / 长按 / 锁存三态，'
          '松开必须立即停，不能有尾帧残留。',
       src='Albert dashboard #longPressHighBeamStrobeEnabled', api='POST /api/feifan/action'),
    it(id='l1g', n='爆闪间隔', en='Strobe interval',
       d='两次远光切换之间的间隔，1-100 ms',
       t='seg', o=opts([('20', '20 ms'), ('50', '50 ms'), ('80', '80 ms'), ('100', '100 ms')]),
       lv='A', p4='需新增',
       im='highBeamStrobeIntervalMs。间隔太小会被前车当成挑衅，20 ms 已经很明显。',
       src='Albert dashboard #highBeamStrobeIntervalMs', api='POST /api/feifan/config'),
    it(id='l1h', n='双拉固定闪次数', en='Double-pull flash count',
       d='连续两次拉杆触发固定次数闪烁',
       t='seg', o=opts([('2', '闪 2 次'), ('3', '闪 3 次'), ('5', '闪 5 次'), ('7', '闪 7 次')]),
       lv='B', p4='需新增',
       im='设计图原文「双拉触发固定闪 2/3/5/7 次可选」。',
       src='设计图 P4CAN FUSION', api='POST /api/feifan/config'),
]

lamp_l2 = [
    fld('l2a', '脉冲喇叭', 'Pulse horn',
        '按固定节奏断鸣，档位决定脉冲速度',
        [('0', '关闭'), ('1', '慢'), ('2', '中'), ('3', '快')],
        'pluseHorn', (27, 6, 3),
        '设计图把它写成「0x10C」，但 0x10C 在 Albert 固件和 P4 源码里都不存在，'
        '写这个帧不会有任何东西响应。原版实际动作是写这个位域。'),
    fld('l2b', '长按喇叭开启脉冲', 'Long-press enables pulse',
        '长按喇叭时按 l2a 的节奏断鸣，松手恢复常鸣',
        None, 'longPluseHorn', (27, 5, 1), ''),
    fld('l2c', '低速轻鸣笛', 'Gentle horn at low speed',
        '低速时按一下只轻鸣，不吓人',
        [('0', '关闭'), ('1', '1 声'), ('2', '2 声'), ('3', '3 声')],
        'gentryHorn', (34, 4, 3), ''),
    fld('l2d', '轻鸣笛次数', 'Gentle horn count',
        '轻鸣笛响几下',
        [('1', '1 声'), ('2', '2 声'), ('3', '3 声')],
        'gentryHornCount', (34, 6, 3), ''),
    fld('l2e', '喇叭联动远光', 'Horn triggers high beam',
        '按喇叭时同步闪远光提醒前车',
        None, 'hornLinkedHighBeam', (32, 5, 1),
        '城市道路慎用：按喇叭已经够吵，再闪远光容易激化矛盾。'),
    fld('l2f', '远光联动喇叭', 'High beam triggers horn',
        '闪远光时同步短鸣',
        None, 'highBeamLinkedHorn', (32, 6, 1), ''),
    it(id='l2g', n='脉冲喇叭间隔', en='Horn pulse gap',
       d='两声之间的静音时长',
       t='seg', o=opts([('150', '150 ms'), ('200', '200 ms'), ('300', '300 ms')]),
       lv='B', p4='需新增',
       im='与 l2a 配合。城市禁鸣区域不要开脉冲喇叭，属于违法行为，仅台架验证用。',
       src='设计图 P4CAN FUSION', api='POST /api/feifan/config'),
]

lamp_l3 = [
    fld('l3a', '前雾灯爆闪', 'Front fog strobe',
        '前雾灯参与爆闪，雨雾天辨识度更高',
        None, 'pluseFrontFogLight', (30, 5, 1), ''),
    fld('l3b', '后雾灯爆闪', 'Rear fog strobe',
        '后雾灯按节奏闪，用来提醒后车',
        None, 'pluseRearFogLight', (31, 6, 1), ''),
    fld('l3c', '动态刹车灯', 'Dynamic brake light',
        '刹车灯按减速度分档闪烁。设计图叫「刹车灯爆闪」，实际就是这一项',
        [('0', '关闭'), ('1', '轻'), ('2', '中'), ('3', '重')],
        'dynamicBrakeLight', (33, 6, 3),
        '关键差别：设计图写「亮起超过 1000 ms 才开始爆闪」，原版是按减速度分档。'
        '按时间触发会在等红灯时乱闪，按减速度触发只在真急刹时闪，后者才合理。'),
    fld('l3d', '开门双闪', 'Hazard on door open',
        '开门时自动双闪，夜间路边下车更安全',
        None, 'openDoorHazardLight', (30, 4, 1), ''),
    fld('l3e', '倒车双闪', 'Hazard on reverse',
        '挂倒挡时双闪',
        None, 'backHazardLight', (30, 7, 1), ''),
    fld('l3f', '倒车后雾灯照明', 'Rear fog as reverse light',
        '倒车时点亮后雾灯补光',
        None, 'backHazardRearFogLight', (24, 3, 1), ''),
    fld('l3g', '转向辅助照明', 'Cornering light',
        '打方向时对应侧雾灯补光',
        None, 'steerAssistanceLighting', (31, 7, 1), ''),
    it(id='l3h', n='后雾灯领航模式', en='Rear fog pilot mode',
       d='实时控制 + 脉冲 + 安全锁存。四项权限默认关闭',
       t='sw', lv='A', p4='需新增',
       im='Albert 后雾灯段，帧 0x3E3。锁存意味着触发后必须显式解除，不会自己恢复，'
          '避免高速上突然熄灭。TSL 侧对应的就是 l3b 位域，两者选一实现。',
       src='Albert dashboard 后雾灯', api='POST /api/feifan/action'),
    it(id='l3i', n='后雾灯触发阈值', en='Rear fog threshold',
       d='减速度达到多少才算重度，100-500',
       t='seg', o=opts([('150', '150'), ('250', '250'), ('400', '400')]),
       lv='A', p4='需新增',
       im='rear-fog-hard-threshold，默认 250。',
       src='Albert dashboard #rear-fog-hard-threshold', api='POST /api/feifan/config'),
    it(id='l3j', n='自动减速后雾灯', en='Decel rear fog',
       d='轻度减速闪 3 次、重度减速闪 6 次',
       t='sw', lv='A', p4='需新增',
       im='rear-fog-strobe-tgl。档位按减速度分轻度/重度，次数写死，不可调。',
       src='Albert dashboard #rear-fog-strobe-tgl', api='POST /api/feifan/config'),
    it(id='l3k', n='倒车警示（双闪 + 8 次后雾灯）', en='Reverse warning',
       d='挂倒挡时联动双闪，并执行 8 次后雾灯脉冲',
       t='sw', lv='A', p4='需新增',
       im='与自动减速共用同一套脉冲引擎，只是固定 8 次。',
       src='Albert dashboard 后雾灯', api='POST /api/feifan/config'),
]

lamp_l4 = [
    it(id='l4a', n='常亮氛围灯', en='Always-on ambient',
       d='总开关；关闭后仍保留分区设置，迎宾、转向、安全提示各自独立',
       t='sw', lv='A', p4='需新增',
       im='Albert ambientEnabled。设计图里的「氛围灯 Albert 0x679」就是这一项；0x679 在固件页面里'
          '没出现（属通信层 ID），UI 上按分区配置走。',
       src='Albert dashboard #ambientEnabled', api='POST /api/feifan/config'),
    it(id='l4b', n='分区选择', en='Zone selection',
       d='六个独立分区，每区独立开关与亮度，默认 60%',
       t='grid', o=opts([('z4', '仪表台左'), ('z5', '仪表台右'), ('z0', '左前门'),
                         ('z1', '右前门'), ('z2', '左后门'), ('z3', '右后门')]),
       lv='A', p4='需新增',
       im='data-ambient-zone-select 0-5，仪表台左右为 4/5，四门为 0-3。点一次切换该区开关。',
       src='Albert dashboard 车厢氛围灯区域图', api='POST /api/feifan/config'),
    it(id='l4c', n='氛围灯亮度', en='Ambient brightness',
       d='分区默认亮度',
       t='seg', o=opts([('30', '30%'), ('60', '60%'), ('100', '100%')]),
       lv='A', p4='需新增',
       im='原版是 10-100 的滑块，这里取三档常用值。',
       src='Albert dashboard 常亮氛围灯', api='POST /api/feifan/config'),
    it(id='l4d', n='氛围灯跟随转向灯', en='Ambient follows indicator',
       d='左右独立跟随，设置按驾驶员保存',
       t='sw', lv='A', p4='需新增',
       im='turnFollowAmbient 独立区块，与常亮氛围灯互不覆盖。P4 侧可从 0x249/0x3C2 拿转向灯状态。',
       src='Albert dashboard #turnFollowAmbientControls', api='POST /api/feifan/config'),
    it(id='l4e', n='迎宾灯效', en='Welcome lighting',
       d='开门聚焦，最后一个合格门关闭后播放一次展开。与常亮氛围灯独立，默认关闭',
       t='sw', lv='A', p4='需新增',
       im='welcomeEnabled。设计图的「迎宾灯光 Albert」即此项，已合并，不再单列。',
       src='Albert dashboard #welcomeEnabled', api='POST /api/feifan/config'),
    it(id='l4f', n='灯效主题', en='Welcome theme',
       d='五种预设，按开门到关门的整段时序播放',
       t='seg', o=opts([('0', '柔光环抱'), ('1', '冰蓝流光'), ('2', '暖金礼序'),
                        ('3', '黑幕启幕'), ('4', '光迹回环')]),
       lv='A', p4='需新增',
       im='welcomeStyle 0-4，默认 3 黑幕启幕（先暗场再按路径渐亮）。',
       src='Albert dashboard welcome-theme-grid', api='POST /api/feifan/config'),
    it(id='l4g', n='开门触发方式', en='Welcome trigger',
       d='先过滤座椅有人/未知/过期，再决定主驾优先',
       t='seg', o=opts([('0', '确认无人后'), ('1', '任何开门')]),
       lv='A', p4='需新增',
       im='welcomeTriggerMode。通过开门筛选后资格会保持到关门，不是每次开门都重算。',
       src='Albert dashboard #welcomeTriggerMode0', api='POST /api/feifan/config'),
    it(id='l4h', n='迎宾亮度与节奏', en='Welcome brightness & tempo',
       d='亮度 10-100%，节奏舒缓 / 标准 / 利落',
       t='seg', o=opts([('slow', '舒缓'), ('normal', '标准'), ('fast', '利落')]),
       lv='A', p4='需新增',
       im='welcomeBrightness 默认 40%，welcomeTempo 默认 1 标准。两项合并成一组，避免面板过长。',
       src='Albert dashboard #welcomeBrightness / #welcomeTempo', api='POST /api/feifan/config'),
]

# ====================================================================  comf
comf_c1 = [
    it(id='c1a', n='座椅按摩（腰托气囊）', en='Seat massage',
       d='充气 / 放气位交替驱动腰托气囊，压力读数（hPa）实时回显，节奏三挡',
       t='sw', lv='B', p4='需新增',
       im='设计图标注「0x3C2」。这一条要特别小心：0x3C2 在 P4 里是 VCLEFT 开关帧，无杆转向灯和'
          '座椅记忆都走它，Albert 也用它做灯光 Mux1。同一 ID 多用途，实现前必须先确认 Mux 号，'
          '否则按错 Mux 会误触发转向灯。',
       src='设计图 P4CAN FUSION + vehicle_logic.h:VCLEFT_SWITCH_ID', api='POST /api/feifan/action'),
    it(id='c1b', n='按摩节奏', en='Massage tempo',
       d='充放气交替的速度',
       t='seg', o=opts([('slow', '舒缓'), ('normal', '标准'), ('strong', '强劲')]),
       lv='B', p4='需新增',
       im='设计图「节奏三挡」。气囊压力上限原版未给数值，需实测确定。',
       src='设计图 P4CAN FUSION', api='POST /api/feifan/config'),
    it(id='c1c', n='按摩压力回显', en='Massage pressure',
       d='腰托气囊压力 hPa 实时读数，用于判断充放气是否真的在动',
       t='info', lv='B', p4='需新增',
       im='设计图「压力读数（hPa）实时回显」。没有这一路回读就无法判断气囊是否卡住，'
          '所以它是按摩功能的前置条件，不是可选项。',
       src='设计图 P4CAN FUSION', api='GET /api/feifan/status'),
    it(id='c1d', n='座椅加热快捷', en='Seat heat shortcut',
       d='滚轮长按切主驾加热挡位，不用进菜单',
       t='sw', lv='B', p4='需新增',
       im='设计图「滚轮长按切主驾加热挡位」。滚轮长按与滚轮换挡共用输入，必须有优先级仲裁，'
          '否则换挡时会被加热抢走。',
       src='设计图 P4CAN FUSION', api='POST /api/feifan/action'),
    it(id='c1e', n='座椅加热挡位', en='Seat heat level',
       d='关 / 1 / 2 / 3 挡',
       t='seg', o=opts([('0', '关'), ('1', '1 挡'), ('2', '2 挡'), ('3', '3 挡')]),
       lv='B', p4='需新增',
       im='仅主驾。副驾加热仍是原车面板控制。',
       src='设计图 P4CAN FUSION', api='POST /api/feifan/action'),
    it(id='c1f', n='座椅占用伪装', en='Seat occupancy spoof',
       d='与安全带门冲突时，滚轮挂挡优先拦截。谨慎项',
       t='sw', lv='B', p4='需新增',
       im='设计图标注「Albert 0x30A，谨慎」。Albert 固件里 0x30A 出现过 2 次但与会话相关，'
          '未能确认就是座椅占用。风险点很实在：伪装「有人」会让 AEB 与安全气囊判定失真，'
          '所以默认关闭且不设快捷入口。',
       src='设计图 P4CAN FUSION', api='POST /api/feifan/config'),
]

comf_c2 = [take('b2a'), take('b2b'), take('b2c'), take('b2d'), take('b2e'),
           take('b2f'), take('b2g')]

comf_c3 = [
    it(id='c3a', n='空调快捷', en='HVAC shortcut',
       d='远程预冷 / 预热模板，上车前在首页一键触发',
       t='seg', o=opts([('cool', '远程预冷'), ('heat', '远程预热'), ('tmpl', '模板')]),
       lv='B', p4='需新增',
       im='设计图标注「TSL 0x2E5」。0x2E5 在 P4 源码里搜不到，属需新增帧；TSL 侧走 CMD 0xA7 '
          '动作码，不直接发 CAN。这两条路径得二选一，不能混。',
       src='设计图 P4CAN FUSION', api='POST /api/feifan/action'),
    take('b3a'),
]

# ====================================================================== ap
ap_a1 = [take('a1%c' % c) for c in 'abcdefghijk'] + [take('a1l')]
ap_a2 = [take(x) for x in ('a2a', 'a2b', 'a2d', 'a2e', 'a2f', 'a2g', 'a2h', 'a2i', 'a2j')]
ap_a3 = [take(x) for x in ('a3a', 'a3b', 'a3c', 'a3d', 'a3e')]
ap_a4 = [take(x) for x in ('a4a', 'a4b', 'a4c', 'a4d', 'a4e', 'a4f', 'a4g', 'a4h')]

# ==================================================================== body
body_b1 = [take('b1a'), take('b1b'), take('b1c'), take('b1d'),
           fld('b1e', '门把手开关前备箱', 'Handle opens frunk',
               '按住门把手多久触发前备箱，单位秒',
               [('0', '关闭'), ('1', '1 秒'), ('2', '2 秒'), ('3', '3 秒')],
               'TimeOpenFrontBox', (29, 2, 7), ''),
           fld('b1f', '门把手开关充电口', 'Handle opens charge port',
               '按住门把手多久触发充电口盖',
               [('0', '关闭'), ('1', '1 秒'), ('2', '2 秒'), ('3', '3 秒')],
               'TimeOpenChargeDoor', (29, 5, 7), '')]

body_b5 = [
    fld('b5a', '主驾安全带提醒', 'Driver belt reminder',
        '关闭后主驾不系安全带不再提示。台架必需，上路别关',
        None, 'frontLeftBuckle', (34, 1, 1),
        '注意：这条不影响 d2b 换挡安全门，那个读的是真实安全带状态。'),
    fld('b5b', '副驾安全带提醒', 'Passenger belt reminder',
        '副驾安全带提示开关',
        None, 'frontRightBuckle', (34, 2, 1), ''),
    fld('b5c', '后排安全带提醒', 'Rear belt reminder',
        '后排安全带提示开关',
        None, 'rearBuckle', (34, 3, 1), ''),
    fld('b5d', '提示音音量', 'Chime volume',
        '车辆提示音整体音量',
        [('0', '静音'), ('1', '低'), ('2', '中'), ('3', '高')],
        'beep', (26, 0, 255), '八比特，原版给的是 0-255 的直通值。'),
    fld('b5e', 'LED 灯开关', 'LED switch',
        '车内 LED 照明总开关',
        None, 'led', (27, 4, 1), ''),
]

body_b4 = [take('b4a'), take('b4b'), take('b4c')]

home_h1 = [take('h1a'), take('h1b'), take('h1c')]
home_h2 = [take('h2a'), take('h2b'), take('h2c')]
home_h3 = [take('h3a'), take('h3b'), take('h3c')]

set_s1 = [take('s1a'), take('s1b'), take('s1c'), take('s1d')]
set_s2 = [take('s2a'), take('s2b'), take('s2c'), take('s2d'), take('s2e')]
set_s3 = [take('s3a'), take('s3b')]


def sect(sid, name, en, items):
    return {'id': sid, 'name': name, 'en': en, 'items': items}


groups = [
    {'id': 'drv', 'name': '驾驶辅助', 'en': 'Drive assist',
     'note': 'Nag Killer、打灯变道、自动换挡、速度与传动',
     'sections': [
         sect('d1', '智驾核心', 'ADAS core', drv_d1),
         sect('d2', '自动换挡', 'Auto shift', drv_d2),
         sect('d3', '速度补偿', 'Speed offset', drv_d3),
         sect('d4', '传动与制动', 'Drivetrain', drv_d4),
     ]},
    {'id': 'lamp', 'name': '灯光与喇叭', 'en': 'Lights & horn',
     'note': '远光爆闪、脉冲喇叭、雾灯警示与氛围灯',
     'sections': [
         sect('l1', '大灯与爆闪', 'Headlight & strobe', lamp_l1),
         sect('l2', '喇叭', 'Horn', lamp_l2),
         sect('l3', '雾灯与警示', 'Fog & hazard', lamp_l3),
         sect('l4', '氛围灯与迎宾', 'Ambient & welcome', lamp_l4),
     ]},
    {'id': 'comf', 'name': '舒适与座椅', 'en': 'Comfort & seats',
     'note': '座椅按摩加热、记忆、空调与占用',
     'sections': [
         sect('c1', '按摩与加热', 'Massage & heat', comf_c1),
         sect('c2', '座椅与记忆', 'Seat & memory', comf_c2),
         sect('c3', '空调与便利', 'HVAC', comf_c3),
     ]},
    {'id': 'ap', 'name': '免打扰与 AP', 'en': 'Nag & AP',
     'note': '提醒抑制、AP/EAP/FSD 开关与轮询算法',
     'sections': [
         sect('a1', '免打扰设置', 'Nag suppression', ap_a1),
         sect('a2', 'AP 设置', 'AP settings', ap_a2),
         sect('a3', 'EAP 设置', 'EAP settings', ap_a3),
         sect('a4', 'FSD 设置', 'FSD settings', ap_a4),
     ]},
    {'id': 'body', 'name': '车身与开合', 'en': 'Body & latches',
     'note': '车门锁扣、开合状态、提醒与滚轮模拟',
     'sections': [
         sect('b1', '车身开合', 'Latches', body_b1),
         sect('b5', '提醒与显示', 'Alerts & display', body_b5),
         sect('b4', '模拟滚轮', 'Scroll wheel', body_b4),
     ]},
    {'id': 'home', 'name': '仪表与快捷', 'en': 'Gauges & shortcuts',
     'note': '实时数据、胎压与一键快捷',
     'sections': [
         sect('h1', '仪表盘', 'Gauges', home_h1),
         sect('h2', '快捷动作', 'Shortcuts', home_h2),
         sect('h3', '常用与配置块', 'Common & blobs', home_h3),
     ]},
    {'id': 'set', 'name': '模块设置', 'en': 'Module settings',
     'note': '外观、模块维护与参数备份',
     'sections': [
         sect('s1', '通用设置', 'General', set_s1),
         sect('s2', '功能模块', 'Modules', set_s2),
         sect('s3', '高级功能', 'Advanced', set_s3),
     ]},
    {'id': 'dev', 'name': '集成清单', 'en': 'Integration notes',
     'note': '命令表、位域、端点与刷写步骤',
     'sections': []},
]

data['meta']['name'] = '更多功能'
data['meta']['baseline'] = ('P4-CAN Universal v3.29.3 / Waveshare ESP32-P4 (rev3.2, 32MB, 3xTWAI) '
                            '+ Albert-P4-P1.6.4 固件内嵌页面')
data['meta']['source'] = ('TSL-Android.apk.1 -> assets/SaaA_embed (__APP__.wxapkg) -> app-service.main.js；'
                          'Albert-P4-P1.6.4-V3.2-c565dc82-OTA.bin -> 内嵌 dashboard (gzip)；'
                          'P4CAN FUSION 设计图（证据 B）')
data['groups'] = groups

# ------------------------------------------------------------ dedupe report
new_ids = [i['id'] for g in groups for s in g['sections'] for i in s['items']]
dupes = sorted({x for x in new_ids if new_ids.count(x) > 1})
dropped = sorted(set(old_items) - set(new_ids))
total_new = len(new_ids)
n_field = sum(1 for g in groups for s in g['sections'] for i in s['items']
              if (i.get('src') or '').startswith('TSL SETTINGS'))
print('items: %d -> %d   groups: %d -> %d   bit-field items: %d'
      % (total_old, total_new, len(old_groups), len(groups), n_field))
print('duplicate ids:', dupes or 'none')
print('dropped ids  :', ', '.join(dropped) or 'none')

if not BAK.exists():
    shutil.copy2(SRC, BAK)
    print('backup ->', BAK.name)
SRC.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
print('wrote', SRC.name, SRC.stat().st_size, 'bytes')
