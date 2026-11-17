#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the integrated 'More features' page for the P4-CAN dashboard.

Reads feifan-menu-data.json (reverse-engineering result) and emits HTML/CSS/JS
fragments that follow the dashboard's existing component vocabulary
(.page/.card/.listrow/.toggle/.settingChoiceButtons/.panel).
"""
import json
import re
import html
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = json.loads((REPO / 'data' / 'feifan-menu-data.json').read_text(encoding='utf-8'))
OUT = REPO / 'build' / 'out'
OUT.mkdir(parents=True, exist_ok=True)

E = lambda s: html.escape(str(s), quote=True)

groups = DATA['groups']
total = sum(len(s['items']) for g in groups for s in g['sections'])
n_groups = len(groups)

# ---------------------------------------------------------------- translations
OPT_EN = {
    '前备箱': 'Frunk', '后备箱': 'Trunk',
    '左前门': 'Front left door', '右前门': 'Front right door',
    '左后门': 'Rear left door', '右后门': 'Rear right door',
    '后视镜折叠': 'Fold mirrors', '解锁': 'Unlock', '锁定': 'Lock',
    '前移': 'Forward', '后移': 'Backward',
    '靠背前': 'Backrest fwd', '靠背后': 'Backrest back',
    '记忆1': 'Memory 1', '记忆2': 'Memory 2', '记忆3': 'Memory 3',
    '女王': 'Queen', '露营': 'Camp', '关闭': 'Off',
    '副驾安全带解系时': 'On belt released', '副驾车门开关时': 'On door open',
    '烘干1分钟': 'Dry 1 min', '烘干5分钟': 'Dry 5 min', '烘干10分钟': 'Dry 10 min',
    '左滚轮': 'Left wheel', '右滚轮': 'Right wheel',
    '上': 'Up', '下': 'Down', '左': 'Left', '右': 'Right', '确认': 'Confirm',
    '滚轮': 'Wheel', '无感': 'Silent', '滚轮+无感': 'Wheel + silent',
    '2-3秒': '2-3 s', '3-5秒': '3-5 s', '5-10秒': '5-10 s', '10-15秒': '10-15 s',
    '15-20秒': '15-20 s', '20-25秒': '20-25 s', '25-30秒': '25-30 s', '30-35秒': '30-35 s',
    '定点免打扰': 'Fixed cycle',
    '先加后减': 'Add then sub', '先减后加': 'Sub then add',
    '加减交替': 'Alternate', '加减随机': 'Random', '左右交替': 'Alternate L/R',
    '左右随机': 'Random L/R', '双击右滚轮': 'Double right wheel',
    '下拉档杆': 'Pull stalk', '跟随AP': 'Follow AP', '立即': 'Instant',
    '老款': 'Legacy', '焕新版': 'Refresh', '模式一': 'Mode 1', '模式二': 'Mode 2',
    '温和': 'Gentle', '适中': 'Balanced', '激进': 'Aggressive',
    '保持原厂': 'Keep factory', '2 默认': '2 default',
    '前爆闪': 'Front strobe', '后爆闪': 'Rear strobe',
    '脉冲喇叭': 'Pulse horn', '领航模式': 'Navigate on AP',
    '开启': 'On', '停用': 'Disabled', '启用': 'Enabled',
    '漂移模式': 'Drift mode', '关闭前电机': 'Front motor off',
    '关闭后电机': 'Rear motor off', '重启模块': 'Reboot module',
    # ---- 驾驶辅助 / 自动换挡
    '舒适': 'Comfort', '标准': 'Standard', '运动': 'Sport',
    '街道': 'Street', '赛道': 'Track', '加强': 'Strong',
    '不限': 'Unlimited', '3 次': '3 shifts', '6 次': '6 shifts', '10 次': '10 shifts',
    '无动作': 'No action', '上下': 'Up/Down', '左右': 'Left/Right', '四向': 'All four',
    '应用预设': 'Apply preset', '恢复默认': 'Restore default',
    # ---- 灯光
    # 注意：不要在这里放裸「2 次 / 5 次 / 7 次」。它们和「闪 N 次」映射到同一英文串，
    # DICT 反向回译时先插入者胜，会让「闪 2 次」显示成「2 次」。
    '仪表台左': 'Dash left', '仪表台右': 'Dash right',
    '柔光环抱': 'Soft embrace', '冰蓝流光': 'Ice blue flow', '暖金礼序': 'Warm gold',
    '黑幕启幕': 'Black curtain', '光迹回环': 'Light trail loop',
    '确认无人后': 'After seats empty', '任何开门': 'Any door opens',
    '舒缓': 'Gentle', '利落': 'Crisp', '强劲': 'Strong',
    # ---- 舒适
    '关': 'Off', '1 挡': 'Level 1', '2 挡': 'Level 2', '3 挡': 'Level 3',
    '远程预冷': 'Remote cool', '远程预热': 'Remote heat', '模板': 'Template',
    # ---- 位域档位
    '慢': 'Slow', '中': 'Medium', '快': 'Fast', '自定义': 'Custom',
    '1 声': '1 beep', '2 声': '2 beeps', '3 声': '3 beeps',
    '闪 2 次': '2 flashes', '闪 3 次': '3 flashes', '闪 5 次': '5 flashes', '闪 7 次': '7 flashes',
    '缓行': 'Creep', '保持': 'Hold', '转动': 'Roll',
    '静音': 'Mute', '低': 'Low', '高': 'High',
    '1 秒': '1 s', '2 秒': '2 s', '3 秒': '3 s',
}
P4_EN = {'需新增': ('New', 'p4new'), '已有': ('Existing', 'p4have'),
         '不可达': ('Unreachable', 'p4no'), '本地UI': ('Local UI', 'p4ui')}

# ------------------------------------------------------- one-tap action bar
# CMD 0xBB (187) single-byte key codes, lifted from pages/index/index.js
# quickActions map. Battery preheat is a pair: 29 = on, 28 = off.
QICON = {
    'bolt': '<path d="M13.4 2.2 4.9 13.6h4.7l-.9 8.2 8.5-11.6h-4.8l1-8Z"/>',
    'horn': '<path d="M4.2 9.3h3.2L11.7 5.9v12.2L7.4 14.7H4.2a1.4 1.4 0 0 1-1.4-1.4v-2.6a1.4 1.4 0 0 1 1.4-1.4Z"/>'
            '<circle cx="16.4" cy="12" r="3.5" fill="none" stroke="currentColor" stroke-width="1.7"/>',
    'pilot': '<rect x="2.2" y="9.6" width="19.6" height="4.8" rx="2.4" transform="rotate(-12 12 12)"/>',
    'heat': '<ellipse cx="12" cy="12" rx="5.7" ry="8.3"/>',
}
QUICK = [
    ('frontStrobe', '前爆闪', 'Front strobe', '91', 'qPurple', 'bolt', None),
    ('rearStrobe', '后爆闪', 'Rear strobe', '94', 'qPink', 'bolt', None),
    ('pulseHorn', '脉冲喇叭', 'Pulse horn', '90', 'qAmber', 'horn', None),
    ('pilotMode', '领航模式', 'Navigate on AP', '95', 'qViolet', 'pilot', None),
    ('preheat', '电池预热', 'Battery preheat', '29', 'qOrange', 'heat', '28'),
]
QUICK_TEXT = [('One-tap actions', '一键快捷'), ('5 shortcuts', '5 个快捷动作'),
              ('Tap to send · firmware endpoint required', '点一下即发送 · 需要固件端点在线'),
              ('Sent · {a}', '已发送 · {a}'),
              ('Recorded only · firmware endpoint not wired yet', '仅记录在本机 · 固件端点尚未接入'),
              ('Tap again to confirm', '再点一次确认')]
QUICK_ROW_IDS = {'h2a', 'h2b'}   # detail rows superseded by the shortcut bar
QUICK_HINT = 'Moved to the one-tap bar at the top of this page.'
SAFE_HINT = 'Vehicle must be stationary and safe. Sends CMD 0xA7 with byte 255.'
HINT_MAP = {'h2a': QUICK_HINT, 'h2b': QUICK_HINT, 's2c': SAFE_HINT}
TECH_SKIP = {'s2c'}   # hint already names the command byte
# rows whose prose mentions several IDs; show the operative one only
TECH_OVERRIDE = {
    'd2a': '0x229 · in',
    'c1a': '0x3C2 · Mux',
}

# Rows that were pure prose ("info") get a live widget instead of an empty
# description: id -> (container id, action key, panel group)
DATA_ROWS = {
    'b1a': ('ffBodyState', 'body'),
    'a1l': ('ffCycle', 'cycle'),
    'h1c': ('ffTpms', 'tpms'),
    'h3b': ('ffQuickBlob', 'quick'),
    's2b': ('ffBackup', 'backup'),
    's2d': ('ffCfgBytes', 'config'),
}
DATA_EMPTY = {'s2b': 'No backup yet'}
# avoid collisions with existing dashboard DICT keys that mean something else
SECTION_EN = {'通用设置': 'General settings'}
GROUP_DESC = {
    'drv': ('Nag Killer, turn-signal lane change, auto shift and speed offset.',
            '昵称抑制、打灯变道、自动换挡与速度补偿。'),
    'lamp': ('High-beam strobe, pulse horn, rear fog and ambient lighting.',
             '远光爆闪、脉冲喇叭、后雾灯与氛围灯。'),
    'comf': ('Seat massage and heat, position memory, HVAC and occupancy.',
             '座椅按摩加热、位置记忆、空调与占用判定。'),
    'body': ('Doors, latches and scroll-wheel key emulation.',
             '车门锁扣与滚轮按键模拟。'),
    'ap': ('Reminder suppression, AP/EAP/FSD flags and the wheel-cycle algorithm.',
           '提醒抑制、AP/EAP/FSD 开关与滚轮周期算法。'),
    'home': ('Live pack telemetry, TPMS and the one-tap shortcuts.',
             '实时电池数据、胎压与一键快捷动作。'),
    'set': ('Appearance, module maintenance and parameter backup.',
            '外观、模块维护与参数备份。'),
    'dev': ('Command table, config bit-fields, planned endpoints and flash steps.',
            '命令表、配置位域、待实现端点与刷写步骤。'),
}
SETTINGS_DESC = ('TSL + Albert controls · %d entries in %d groups' % (total, n_groups),
                 '逆向自 TSL 与 Albert · %d 组 %d 项' % (n_groups, total))
SUBTITLE = ('Merged from the TSL mini-program and the Albert firmware: %d control points in %d groups, '
            'plus a 5-button shortcut bar. Widgets work now; the firmware endpoints are not wired yet, '
            'so switches stay on this phone.' % (total, n_groups))
SUBTITLE_ZH = ('合并自 TSL 小程序与 Albert 固件：%d 组共 %d 个功能点，另加 5 键快捷条。'
               '控件已可用；固件端点尚未接入，开关暂存在本机。' % (n_groups, total))
PAGE_TEXT = [
    ('More features', '更多功能'),
    (SUBTITLE, SUBTITLE_ZH),
    ('Firmware link', '固件连接'),
    ('Checking…', '检测中…'),
    ('Stored on this phone, firmware endpoint absent', '仅存本机，固件端点未接入'),
    ('Synced with firmware', '已与固件同步'),
    ('Reset local state', '清空本地状态'),
    ('Clear every switch stored on this phone', '清除本机保存的所有开关'),
    ('Reset', '重置'),
    ('Groups', '功能分组'),
    ('entries', '项'),
    ('Legend', '标记说明'),
    ('Evidence A', '证据 A'),
    ('Evidence B', '证据 B'),
    ('Evidence C', '证据 C'),
    ('Evidence level: read from the decompiled JS and tables', '证据等级：来自反编译 JS 与配置表'),
    ('Evidence level: inferred from screenshots, same structure', '证据等级：截图推断，结构同构'),
    ('Evidence level: UI placeholder only', '证据等级：仅 UI 占位'),
    ('P4 status', 'P4 状态'),
    ('Already implemented in P4-CAN, map instead of rebuild', 'P4-CAN 已有实现，做映射即可'),
    ('Needs new code in the firmware', '需在固件新增'),
    ('Not reachable over the three CAN buses', '三路 CAN 无法触达'),
    ('Local UI state only, nothing is transmitted', '仅本地 UI 状态，不发帧'),
    ('Commands', '命令表'),
    ('Config bit-fields', '配置位域'),
    ('Planned endpoints', '待实现端点'),
    ('Firmware steps', '固件改造步骤'),
    ('Build', '编译参数'),
    ('Flash', '刷写'),
    ('More', '更多'),
]

def sec_en(sec):
    return SECTION_EN.get(sec['name']) or sec.get('en') or sec['name']


DICT = {}
for en, zh in PAGE_TEXT:
    DICT[en] = zh
for g in DATA['groups']:
    DICT.setdefault(g['en'], g['name'])
    for s in g['sections']:
        DICT.setdefault(sec_en(s), s['name'])
        for it in s['items']:
            if it.get('en'):
                DICT.setdefault(it['en'], it['n'])
for zh, en in OPT_EN.items():
    DICT.setdefault(en, zh)
for en, zh in QUICK_TEXT:
    DICT.setdefault(en, zh)
DICT.setdefault(QUICK_HINT, '已移至本页顶部的一键快捷条。')
DICT.setdefault(SAFE_HINT, '车辆必须处于安全静止状态。发送 CMD 0xA7 + 0xFF。')
DICT.setdefault('Enter', '进入')
for en, zh in [('Device', '设备'),
               ('Firmware update', '固件更新'),
               ('Flash a local .bin over Wi-Fi · no USB cable', '通过 Wi-Fi 刷入本地 .bin · 无需插线')]:
    DICT.setdefault(en, zh)

LIVE_TEXT = [
    ('Not read yet', '尚未读取'), ('No backup yet', '尚无备份'), ('Reading…', '读取中…'),
    ('Central lock', '中控锁'), ('Locked', '已锁定'), ('Unlocked', '已解锁'),
    ('Front trunk', '前备箱'), ('Open', '开启'), ('Closed', '关闭'),
    ('Front left', '左前'), ('Front right', '右前'),
    ('Rear left', '左后'), ('Rear right', '右后'),
    ('Body status unavailable.', '读不到车身状态。'),
    ('TPMS unavailable.', '读不到胎压。'),
    ('Next delay', '下次等待'), ('Wheel', '滚轮'), ('Order', '顺序'),
    ('Gap', '间隔'), ('Keys', '键值'),
    ('Preview cycle', '生成周期预览'), ('Reload', '重新读取'),
    ('Blob size', '配置块大小'),
    ('No 256 B reply yet. The module answers CMD 0xAB only after a full block arrives.',
     '尚未收到 256B 回包。模块要等整块到齐才会应答 CMD 0xAB。'),
    ('Size', '大小'), ('Read 256 B blob', '读取 256B 配置块'),
    ('Read config block', '读取配置块'),
    ('Export', '导出'), ('Import', '导入'),
    ('Exported', '已导出'), ('Imported', '已导入'),
    ('Export failed.', '导出失败。'), ('Not a valid backup file.', '不是有效的备份文件。'),
    ('Blob endpoint unavailable.', '配置块端点不可用。'),
    ('Config read failed.', '配置读取失败。'),
]
for en, zh in LIVE_TEXT:
    DICT.setdefault(en, zh)
for zh, (en, _) in P4_EN.items():
    DICT.setdefault(en, zh)
for zh, en in (('A', 'A'), ('B', 'B'), ('C', 'C')):
    DICT.pop(en, None)


def opt_en(label):
    if label in OPT_EN:
        return OPT_EN[label]
    return label


def tech_of(it):
    im = it.get('im') or ''
    m = re.search(r'byte\s*(\d+)\s*>>>\s*(\d+)\s*&\s*(\d+)', im)
    if m:
        return 'byte%s >>> %s & %s' % (m.group(1), m.group(2), m.group(3))
    m = re.search(r'(\d+)\s*>>>\s*(\d+)\s*&\s*(\d+)', im)
    if m:
        return 'byte%s >>> %s & %s' % (m.group(1), m.group(2), m.group(3))
    codes = list(dict.fromkeys(re.findall(r'0x[0-9A-Fa-f]{2,3}', im)))
    if codes:
        return ' · '.join(codes[:3])
    return ''


def chips(it, closing=True):
    """Return the right-hand chip cluster. Opening <div class=rowRight> is
    closed here so every caller gets balanced markup."""
    lv = it.get('lv') or ''
    p4 = it.get('p4') or ''
    out = ['<div class="rowRight">']
    if lv:
        out.append('<span class="ffTag lv%s">%s</span>' % (lv, lv))
    if p4 in P4_EN:
        en, cls = P4_EN[p4]
        out.append('<span class="ffTag %s">%s</span>' % (cls, E(en)))
    out.append('</div>')
    return out


def _head(it):
    tech = TECH_OVERRIDE.get(it['id']) or tech_of(it)
    h = ['<div class="listkey">%s</div>' % E(it['en'])]
    if it['id'] in HINT_MAP:
        h.append('<div class="listdesc">%s</div>' % E(HINT_MAP[it['id']]))
    if tech and it['id'] not in TECH_SKIP:
        h.append('<div class="listdesc">%s</div>' % E(tech))
    return h


def row_sw(it):
    tid = 'ff_' + it['id']
    h = ['<div class="listrow"><div>'] + _head(it) + ['</div>']
    h.extend(chips(it))
    h.append('<label class="toggle"><input id="%s" data-ff="%s" type="checkbox"/>'
             '<span class="track"></span></label>' % (tid, it['id']))
    h.append('</div>')
    return ''.join(h)


def row_seg(it):
    opts = it.get('o') or []
    if not opts:
        opts = [{'v': 'small', 'l': '小'}, {'v': 'standard', 'l': '中'}, {'v': 'large', 'l': '大'}]
    n = 2 if len(opts) <= 2 else (4 if len(opts) > 3 else 3)
    cols = ' style="grid-template-columns:repeat(%d,minmax(0,1fr))"' % n
    h = ['<div class="listrow settingChoiceRow"><div>'] + _head(it) + ['</div>',
         '<div class="settingChoiceButtons" role="group" aria-label="%s"%s>' % (E(it['en']), cols)]
    for o in opts:
        h.append('<button type="button" data-ff-seg="%s" data-v="%s" aria-pressed="false">%s</button>'
                 % (it['id'], E(o['v']), E(opt_en(o['l']))))
    h.append('</div></div>')
    return ''.join(h)


def row_grid(it):
    h = ['<div class="listrow ffBlock"><div class="ffRowTop"><div>'] + _head(it) + ['</div>']
    h.extend(chips(it))
    h.append('</div><div class="ffGrid">')
    for o in it.get('o') or []:
        title = (' title="%s"' % E(o['s'])) if o.get('s') else ''
        h.append('<button type="button" class="ffBtn" data-ff-act="%s" data-v="%s"%s>%s</button>'
                 % (it['id'], E(o['v']), title, E(opt_en(o['l']))))
    h.append('</div></div>')
    return ''.join(h)


def row_info(it):
    h = ['<div class="listrow"><div>'] + _head(it) + ['</div>']
    h.extend(chips(it))
    h.append('</div>')
    return ''.join(h)


ARM_ID = {'s2c'}          # destructive 0xA7 actions need a second tap


def row_act(it):
    """Info row with a red two-tap action button (service mode, 0xA7 255)."""
    opts = it.get('o') or [{'v': '255', 'l': '进入'}]
    h = ['<div class="listrow"><div>'] + _head(it) + ['</div>']
    h.extend(chips(it))
    h.append('<button type="button" class="ffDanger" data-ff-act="%s" data-v="%s" data-arm="1">Enter</button>'
             % (it['id'], E(opts[0]['v'])))
    h.append('</div>')
    return ''.join(h)


ROW = {'sw': row_sw, 'seg': row_seg, 'grid': row_grid, 'info': row_info,
       'num': row_seg, 'act': row_act}


def row_data(it):
    """Info row promoted to a live panel: data dump + one or two buttons."""
    cid, key = DATA_ROWS[it['id']]
    h = ['<div class="listrow ffBlock"><div class="ffRowTop"><div>'] + _head(it) + ['</div>']
    h.extend(chips(it))
    h.append('</div><div class="ffData" id="%s"><span class="ffDim">%s</span></div>'
             % (cid, DATA_EMPTY.get(it['id'], 'Not read yet')))
    h.append('<div class="ffActions">')
    if key == 'backup':
        h.append('<button type="button" class="ffMini" data-ff-load="export">Export</button>'
                 '<label class="ffMini ffFile">Import<input type="file" id="ffImport" accept=".json"></label>')
    elif key == 'cycle':
        h.append('<button type="button" class="ffMini" data-ff-load="cycle">Preview cycle</button>')
    elif key == 'quick':
        h.append('<button type="button" class="ffMini" data-ff-load="quick">Read 256 B blob</button>')
    elif key == 'config':
        h.append('<button type="button" class="ffMini" data-ff-load="config">Read config block</button>')
    else:
        h.append('<button type="button" class="ffMini" data-ff-load="%s">Reload</button>' % key)
    h.append('</div></div>')
    return ''.join(h)


ROW['data'] = row_data


def kv_card(title_zh, title_en, rows):
    h = ['<div class="sectionhead tight"><div class="sectiontitle">%s</div></div><section class="card"><div class="body">'
         % E(title_en)]
    for k, v in rows:
        h.append('<div class="r"><span class="rk2">%s</span><span>%s</span></div>' % (E(k), E(v)))
    h.append('</div></section>')
    return ''.join(h)


# --------------------------------------------------------------------- page
T = dict(PAGE_TEXT)
counts = sorted({len(s['items']) for g in groups for s in g['sections']} | {total})
for n in counts:
    DICT.setdefault('%d entries' % n, '%d 项' % n)
DICT.setdefault('Commands · bit-fields · endpoints', '命令表 · 配置位域 · 待实现端点')
DICT.setdefault('LOCAL', '本机')
DICT.setdefault(*SETTINGS_DESC)
DICT.setdefault('SYNC', '已同步')
DICT.setdefault('Build / Flash', '编译 / 刷写')
for _i in range(len(DATA['steps'])):
    DICT.setdefault('Step %d' % (_i + 1), '步骤 %d' % (_i + 1))

page = ['<!--P4CAN-FEIFAN-PAGE-START-->',
        '<main class="page ffScope" data-page="feifan">',
        '<div class="pageTitle">More features</div>',
        '<div class="pageSub">%s</div>' % E(SUBTITLE),
        '<div class="sectionhead tight"><div class="sectiontitle">One-tap actions</div>'
        '<div class="sectionnote">5 shortcuts</div></div>',
        '<section class="card"><div class="ffQuick">']
for key, zh, en, code, cls, icon, off in QUICK:
    page.append('<button type="button" class="ffQ" data-ff-q="%s" data-v="%s"%s>'
                '<span class="ffQIco %s"><svg viewbox="0 0 24 24" aria-hidden="true" '
                'fill="currentColor">%s</svg></span>'
                '<span class="ffQlbl">%s</span></button>'
                % (key, code, (' data-off="%s"' % off) if off else '', cls, QICON[icon], E(en)))
page.append('</div>'
            '<div class="ffQStatus" id="ffQStatus" data-kind="idle"'
            ' data-t-idle-en="Tap to send · firmware endpoint required"'
            ' data-t-idle-zh="点一下即发送 · 需要固件端点在线"'
            ' data-t-sent-en="Sent · {a}" data-t-sent-zh="已发送 · {a}"'
            ' data-t-local-en="Recorded only · firmware endpoint not wired yet"'
            ' data-t-local-zh="仅记录在本机 · 固件端点尚未接入"'
            ' data-t-arm-en="Tap again to confirm" data-t-arm-zh="再点一次确认">'
            '<span class="ffQSDot"></span>'
            '<span class="ffQSText">Tap to send · firmware endpoint required</span>'
            '</div></section>')
page += [
        '<section class="card">',
        '<div class="listrow"><div><div class="listkey">Firmware link</div>'
        '<div class="listdesc" id="ffLinkState">Checking…</div></div>'
        '<div class="rowRight"><span class="ffTag" id="ffLinkTag">LOCAL</span></div></div>',
        '<div class="listrow"><div><div class="listkey">Reset local state</div>'
        '<div class="listdesc">Clear every switch stored on this phone</div></div>'
        '<div class="rowRight"><button type="button" class="ffMini" id="ffResetBtn">Reset</button></div></div>',
        '</section>',
        '<div class="sectionhead"><div class="sectiontitle">Groups</div>'
        '<div class="sectionnote">%d entries</div></div>' % total,
        '<section class="card">']

for g in groups:
    n = sum(len(s['items']) for s in g['sections'])
    secs = ' · '.join(sec_en(s) for s in g['sections']) or 'Commands · bit-fields · endpoints'
    DICT.setdefault(secs, ' · '.join(s['name'] for s in g['sections']) or '命令表 · 配置位域 · 待实现端点')
    right = ('<span class="value" data-ff-count="%s" data-ff-total="%d">0/%d</span>' % (g['id'], n, n)) if n else ''
    page.append('<div class="listrow clickable" data-panel="panelFeifan%s">'
                '<div><div class="listkey">%s</div><div class="listdesc">%s</div></div>'
                '<div class="rowRight">%s<span class="chev">›</span></div></div>'
                % (g['id'].capitalize(), E(g['en']), E(secs), right))

page.append('</section>')

page.append('<div class="sectionhead"><div class="sectiontitle">Legend</div></div><section class="card">')
for lv, key in (('A', 'Evidence level: read from the decompiled JS and tables'),
                ('B', 'Evidence level: inferred from screenshots, same structure'),
                ('C', 'Evidence level: UI placeholder only')):
    page.append('<div class="listrow"><div><div class="listkey">Evidence %s</div>'
                '<div class="listdesc">%s</div></div><span class="ffTag lv%s">%s</span></div>'
                % (lv, E(key), lv, lv))

LEGEND = [('需新增', 'Needs new code in the firmware'),
          ('已有', 'Already implemented in P4-CAN, map instead of rebuild'),
          ('不可达', 'Not reachable over the three CAN buses'),
          ('本地UI', 'Local UI state only, nothing is transmitted')]
for zh, desc_en in LEGEND:
    en, cls = P4_EN[zh]
    page.append('<div class="listrow"><div><div class="listkey">%s</div>'
                '<div class="listdesc">%s</div></div><span class="ffTag %s">%s</span></div>'
                % (E(en), E(desc_en), cls, E(en)))
page.append('</section>')
page.append('</main>')
page.append('<!--P4CAN-FEIFAN-PAGE-END-->')
page_html = '\n'.join(page)

# ------------------------------------------------------------------- panels
panels = ['<!--P4CAN-FEIFAN-PANELS-START-->']
back = ('<button aria-label="Back" class="backbtn"><svg aria-hidden="true" class="backIcon" '
        'viewbox="0 0 24 24"><path d="M15 18l-6-6 6-6" fill="none" stroke="currentColor" '
        'stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></button>')

for g in groups:
    desc_en, desc_zh = GROUP_DESC[g['id']]
    DICT.setdefault(desc_en, desc_zh)
    pid = 'panelFeifan' + g['id'].capitalize()
    panels.append('<section class="panel ffScope" id="%s"><div class="panelin">' % pid)
    panels.append('<div class="paneltop">%s<div class="paneltitle">More features</div></div>' % back)
    panels.append('<div class="panelHero">%s</div>' % E(g['en']))
    panels.append('<div class="panelSub">%s</div>' % E(desc_en))
    if g['id'] == 'dev':
        panels.append(kv_card('命令表', 'Commands',
                              [(c[0] + ' / ' + c[1], c[2]) for c in DATA['commands']]))
        panels.append(kv_card('配置位域', 'Config bit-fields',
                              [('%s = %s' % (f['id'], '%d>>%d&%d' % tuple(f['bit'])), f['name'])
                               for f in DATA['fields_full']]))
        panels.append(kv_card('待实现端点', 'Planned endpoints',
                              [('%s %s' % (a[0], a[1]), a[2]) for a in DATA['apis']]))
        panels.append(kv_card('固件改造步骤', 'Firmware steps',
                              [('Step %d' % (i + 1), s) for i, s in enumerate(DATA['steps'])]))
        panels.append(kv_card('编译/刷写', 'Build / Flash',
                              [('arduino-cli', DATA['build']), ('esptool', DATA['flash'])]))
        panels.append('<div class="card"><div class="ffNote">%s</div></div>'
                      % E('Static reverse engineering, behaviour spec only. '
                          'Bench-test CAN TX on an isolated bus before any road use.'))
        DICT.setdefault('Static reverse engineering, behaviour spec only. '
                        'Bench-test CAN TX on an isolated bus before any road use.',
                        '静态逆向，仅行为规格。上路前先在隔离总线上做台架验证。')
    else:
        for s in g['sections']:
            panels.append('<div class="sectionhead tight"><div class="sectiontitle">%s</div>'
                          '<div class="sectionnote">%d %s</div></div><section class="card">'
                          % (E(sec_en(s)), len(s['items']), 'entries'))
            for it in s['items']:
                t = it.get('t', 'info')
                if it['id'] in QUICK_ROW_IDS:   # rendered as the top shortcut bar
                    t = 'info'
                if it['id'] in ARM_ID:          # two-tap destructive action
                    t = 'act'
                if it['id'] in DATA_ROWS:       # live data widget
                    t = 'data'
                panels.append(ROW[t](it))
            panels.append('</section>')
    panels.append('</div></section>')
panels.append('<!--P4CAN-FEIFAN-PANELS-END-->')
panels_html = '\n'.join(panels)

# ---------------------------------------------------------------------- css
CSS = """/*P4CAN-FEIFAN-CSS-START*/
body .ffScope .ffTag{display:inline-flex;align-items:center;height:19px;padding:0 7px;border-radius:999px;border:1px solid var(--line);font-size:8px;font-weight:700;letter-spacing:.04em;color:var(--muted);white-space:nowrap}
body .ffScope .ffTag.lvA{color:var(--green);border-color:rgba(39,131,83,.35)}
body .ffScope .ffTag.lvB{color:var(--amber);border-color:rgba(173,119,25,.35)}
body .ffScope .ffTag.lvC{color:var(--muted2)}
body .ffScope .ffTag.p4new{color:var(--blue)}
body .ffScope .ffTag.p4have{color:var(--green)}
body .ffScope .ffTag.p4no{color:var(--red)}
body .ffScope .ffTag.p4ui{color:var(--muted)}
body .ffScope .listrow .rowRight{gap:7px}
body .ffScope .listrow.ffBlock{display:block;padding:13px 15px;min-height:0}
body .ffScope .ffRowTop{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
body .ffScope .ffRowTop>div:first-child{min-width:0;flex:1}
body .ffScope .ffGrid{display:flex;flex-wrap:wrap;gap:7px;margin-top:11px}
body .ffScope .ffBtn{border:1px solid var(--line);border-radius:999px;background:transparent;color:var(--ink);font-size:11px;font-weight:600;line-height:1.1;padding:9px 13px;font-family:inherit}
body .ffScope .ffBtn:active{transform:scale(.97)}
body .ffScope .ffBtn.on{background:var(--ink);color:var(--bg);border-color:transparent}
body .ffScope .ffBtn:disabled{opacity:.4}
body .ffScope .ffQuick{display:grid;grid-template-columns:repeat(auto-fit,minmax(56px,1fr));gap:5px;padding:13px 10px 8px;justify-items:center}
body .ffScope .ffQStatus{display:flex;align-items:center;gap:6px;padding:0 14px 13px;font-size:11px;font-weight:500;line-height:1.35;color:var(--muted);transition:color .18s ease}
body .ffScope .ffQSDot{width:5px;height:5px;border-radius:50%;background:var(--muted2);flex:0 0 auto;transition:background .18s ease}
body .ffScope .ffQStatus[data-kind="sent"]{color:var(--green)}
body .ffScope .ffQStatus[data-kind="sent"] .ffQSDot{background:var(--green)}
body .ffScope .ffQStatus[data-kind="local"]{color:var(--amber)}
body .ffScope .ffQStatus[data-kind="local"] .ffQSDot{background:var(--amber)}
body .ffScope .ffQStatus[data-kind="arm"]{color:var(--amber)}
body .ffScope .ffQStatus[data-kind="arm"] .ffQSDot{background:var(--amber);animation:ffQpulse 1s ease-in-out infinite}
@keyframes ffQpulse{0%,100%{opacity:1}50%{opacity:.2}}
/* 深色主题没覆盖 --green/--amber，直接用亮一档的值，否则在 #151515 上发闷 */
[data-theme="dark"] body .ffScope .ffQStatus[data-kind="sent"]{color:#4ec98a}
[data-theme="dark"] body .ffScope .ffQStatus[data-kind="sent"] .ffQSDot{background:#4ec98a}
[data-theme="dark"] body .ffScope .ffQStatus[data-kind="local"]{color:#e0a94a}
[data-theme="dark"] body .ffScope .ffQStatus[data-kind="local"] .ffQSDot{background:#e0a94a}
[data-theme="dark"] body .ffScope .ffQStatus[data-kind="arm"]{color:#e0a94a}
[data-theme="dark"] body .ffScope .ffQStatus[data-kind="arm"] .ffQSDot{background:#e0a94a}
body .ffScope .ffQ{display:flex;flex-direction:column;align-items:center;gap:9px;border:0;background:transparent;padding:0;font-family:inherit;color:var(--ink);-webkit-tap-highlight-color:transparent;cursor:pointer}
body .ffScope .ffQIco{width:45px;height:45px;border-radius:50%;display:flex;align-items:center;justify-content:center;transition:transform .16s ease,box-shadow .16s ease}
body .ffScope .ffQIco svg{width:21px;height:21px;display:block}
body .ffScope .ffQlbl{font-size:10px;font-weight:600;line-height:1.2;text-align:center;letter-spacing:-.01em}
body .ffScope .qPurple{background:rgba(132,116,255,.14);color:#8474ff}
body .ffScope .qPink{background:rgba(236,106,153,.14);color:#ec6a99}
body .ffScope .qAmber{background:rgba(216,165,58,.16);color:#d8a53a}
body .ffScope .qViolet{background:rgba(200,105,221,.14);color:#c869dd}
body .ffScope .qOrange{background:rgba(240,128,64,.15);color:#f08040}
body .ffScope .ffQ:active .ffQIco{transform:scale(.9)}
body .ffScope .ffQ.on .ffQIco{transform:scale(.86);box-shadow:0 0 0 3px currentColor}
body .ffScope .ffQ.on .ffQlbl{font-weight:750}
body .ffScope .ffQ.active .ffQIco{box-shadow:inset 0 0 0 2px currentColor}
body .ffScope .ffQ.active .ffQlbl{font-weight:750}
body .ffScope .ffQ.armed .ffQIco{box-shadow:0 0 0 3px rgba(240,128,64,.32);transform:scale(.92)}
body .ffScope .ffDanger{border:1px solid rgba(200,66,58,.45);background:transparent;color:var(--red);border-radius:999px;font-size:10px;font-weight:700;letter-spacing:.02em;padding:8px 13px;font-family:inherit;white-space:nowrap;transition:background .15s ease,color .15s ease}
body .ffScope .ffDanger.armed{background:var(--red);border-color:transparent;color:#fff}
body .ffScope .ffDanger.on{opacity:.45}
body .ffScope .ffData{margin-top:11px;border:1px solid var(--line);border-radius:11px;padding:9px 11px;font-size:10.5px;line-height:1.65;color:var(--ink);background:rgba(128,128,128,.09);word-break:break-all}
body .ffScope .ffData .ffMono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:-.01em}
body .ffScope .ffData .ffDim{color:var(--muted2)}
body .ffScope .ffCells{display:grid;grid-template-columns:repeat(auto-fit,minmax(62px,1fr));gap:8px 6px}
body .ffScope .ffCell{display:flex;flex-direction:column;gap:1px;font-size:10px}
body .ffScope .ffCell b{font-weight:700}
body .ffScope .ffCell i{font-style:normal;color:var(--muted);font-size:9.5px}
body .ffScope .ffKV{display:flex;justify-content:space-between;gap:12px}
body .ffScope .ffKV em{font-style:normal;color:var(--muted)}
body .ffScope .ffDot{display:inline-block;width:5px;height:5px;border-radius:50%;background:var(--green);margin-right:5px;vertical-align:1px}
body .ffScope .ffDot.warn{background:var(--amber)}
body .ffScope .ffActions{display:flex;gap:7px;margin-top:10px;flex-wrap:wrap}
body .ffScope .ffFile{position:relative;overflow:hidden}
body .ffScope .ffFile input{position:absolute;inset:0;opacity:0;cursor:pointer}
[data-theme="dark"] body .ffScope .qPurple{background:rgba(150,136,255,.22);color:#b9adff}
[data-theme="dark"] body .ffScope .qPink{background:rgba(245,130,170,.22);color:#fca5c0}
[data-theme="dark"] body .ffScope .qAmber{background:rgba(230,185,90,.22);color:#eec36a}
[data-theme="dark"] body .ffScope .qViolet{background:rgba(214,130,232,.22);color:#e9a3f2}
[data-theme="dark"] body .ffScope .qOrange{background:rgba(250,150,95,.22);color:#fba86f}
[data-theme="dark"] body .ffScope .ffQ.active .ffQIco{box-shadow:inset 0 0 0 2px currentColor}
body .ffScope .ffMini{border:0;border-radius:999px;background:var(--bg);color:var(--ink);font-size:10px;font-weight:650;padding:9px 14px;font-family:inherit}
body .ffScope .ffNote{font-size:9.5px;color:var(--muted);line-height:1.55;padding:13px 15px}
body .ffScope .listrow.settingChoiceRow{display:block;padding:15px;min-height:0}
body .ffScope .settingChoiceButtons{grid-template-columns:repeat(auto-fit,minmax(78px,1fr));margin-top:11px}
body .ffScope .settingChoiceButtons button{font-size:11px;min-height:38px;border:1px solid var(--line);border-radius:999px}
body .ffScope .pageTitle{margin-bottom:2px}
body .ffScope .pageSub{max-width:44ch}
@media(max-width:430px){body.p4-2027 .bottomnav .navbtn{min-width:0;padding:0 9px;font-size:11.5px}}
/*P4CAN-FEIFAN-CSS-END*/
"""

# ----------------------------------------------------------------------- js
JS = r"""<!--P4CAN-FEIFAN-JS-START-->
<script>
(function(){
  var KEY='p4canFeifan', state={}, link='local', probing=false;
  try{state=JSON.parse(localStorage.getItem(KEY)||'{}')||{};}catch(e){state={};}
  function q(id){return document.getElementById(id);}
  function save(){try{localStorage.setItem(KEY,JSON.stringify(state));}catch(e){}}
  function val(id){return Object.prototype.hasOwnProperty.call(state,id)?String(state[id]):null;}

  function render(){
    /* 这两处是 JS 动态写 textContent，全局词表只处理静态/新增节点，跟进不到，
       所以直接按语言出串，别指望 DICT。 */
    var tag=q('ffLinkTag'), st=q('ffLinkState'), zh=isZh();
    if(tag)tag.textContent=link==='online'?(zh?'已同步':'SYNC'):(zh?'本机':'LOCAL');
    if(st)st.textContent=link==='online'
      ?(zh?'已与固件同步':'Synced with firmware')
      :(zh?'仅存本机，固件端点未接入':'Stored on this phone, firmware endpoint absent');
    document.querySelectorAll('input[data-ff]').forEach(function(el){
      var v=val(el.dataset.ff);
      el.checked=v==='1'||v==='true';
    });
    document.querySelectorAll('[data-ff-seg]').forEach(function(b){
      b.setAttribute('aria-pressed',val(b.dataset.ffSeg)===b.dataset.v?'true':'false');
    });
    document.querySelectorAll('[data-ff-count]').forEach(function(el){
      var g=el.dataset.ffCount;
      var pid='panelFeifan'+g.charAt(0).toUpperCase()+g.slice(1);
      var panel=q(pid),seen={},n=0;
      if(panel)panel.querySelectorAll('[data-ff],[data-ff-seg]').forEach(function(x){
        var id=x.dataset.ff||x.dataset.ffSeg;
        if(id&&!seen[id]&&val(id)!=null){seen[id]=1;n++;}
      });
      el.textContent=n+'/'+el.dataset.ffTotal;
    });
    renderQuick();
  }

  function on_(id){return val('q.'+id)==='1';}
  function renderQuick(){
    /* 标签不再被 JS 改写：原来切到「Preheat on」会绕开词表变成英文。
       开/关状态改用 active 外环 + 状态行表达。 */
    document.querySelectorAll('[data-ff-q]').forEach(function(b){
      if(!b.dataset.off){b.classList.remove('active');return;}
      b.classList.toggle('active',on_(b.dataset.ffQ));
    });
  }

  function isZh(){try{return localStorage.getItem('p4canLang')!=='en';}catch(e){return true;}}

  var qsTimer=null;
  /* 动作型按钮原来只闪 420ms，手机上等于没反应。这里统一在快捷条下方
     给一行可见的确认：发出去 / 只记录在本机 / 再点一次确认。 */
  function qs(kind,act){
    var e=q('ffQStatus');if(!e)return;
    var key='t'+kind.charAt(0).toUpperCase()+kind.slice(1)+(isZh()?'Zh':'En');
    var t=e.dataset[key]||'';
    if(act)t=t.replace('{a}',act);
    var tx=e.querySelector('.ffQSText');
    if(tx)tx.textContent=t;
    e.dataset.kind=kind;
    clearTimeout(qsTimer);
    if(kind!=='idle')qsTimer=setTimeout(function(){qs('idle');},4200);
  }
  function hex2(code){
    var n=Number(code);
    if(isNaN(n))return String(code);
    var s=(n&0xFF).toString(16).toUpperCase();
    return '0x'+(s.length<2?'0'+s:s);
  }
  function lblOf(b){var l=b.querySelector('.ffQlbl');return l?l.textContent:'';}

  function sendAction(id,code){
    if(link!=='online')return false;
    var n=Number(code),payload={id:id};
    if(!isNaN(n))payload.code=n; else payload.label=String(code);
    try{fetch('/api/feifan/action',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload)});}catch(e){return false;}
    return true;
  }

  /* ------------------------------------------------ live data widgets */
  function setData(id,html){var e=q(id);if(e)e.innerHTML=html;}
  function getJSON(url){
    return fetch(url,{cache:'no-store'}).then(function(r){
      if(!r.ok)throw 0;return r.json();
    });
  }
  var TYRE=['Front left','Front right','Rear left','Rear right'];

  function loadBody(){
    setData('ffBodyState','<span class="ffDim">Reading…</span>');
    getJSON('/api/feifan/gauge').then(function(d){
      var c='<div class="ffKV"><em>Central lock</em><span>'+
        (d.locked?'<span class="ffDot"></span>Locked':'<span class="ffDot warn"></span>Unlocked')+'</span></div>';
      c+='<div class="ffKV"><em>Front trunk</em><span>'+(d.frunk?'Open':'Closed')+'</span></div>';
      c+='<div class="ffKV"><em>Trunk</em><span>'+(d.trunk?'Open':'Closed')+'</span></div>';
      c+='<div class="ffCells" style="margin-top:9px">';
      for(var i=0;i<4;i++){
        c+='<div class="ffCell"><b>'+TYRE[i]+'</b><i>'+(d.doors&&d.doors[i]?'Open':'Closed')+'</i></div>';
      }
      setData('ffBodyState',c+'</div>');
    }).catch(function(){setData('ffBodyState','<span class="ffDim">Body status unavailable.</span>');});
  }

  function loadTpms(){
    setData('ffTpms','<span class="ffDim">Reading…</span>');
    getJSON('/api/feifan/gauge').then(function(d){
      var t=d.tpms||[],c='<div class="ffCells">';
      for(var i=0;i<4;i++){
        var w=t[i]||{};
        c+='<div class="ffCell"><b>'+TYRE[i]+'</b><i>'+
          (w.bar!=null?Number(w.bar).toFixed(1)+' bar':'—')+'</i><i>'+
          (w.temp!=null?w.temp+' ℃':'—')+'</i></div>';
      }
      setData('ffTpms',c+'</div>');
    }).catch(function(){setData('ffTpms','<span class="ffDim">TPMS unavailable.</span>');});
  }

  var RANGE={1:[2,3],2:[3,5],3:[5,10],4:[10,15],5:[15,20],6:[20,25],7:[25,30],8:[30,35],15:[30,30]};
  function loadCycle(){
    var time=parseInt(val('a1g'),10);if(!RANGE[time])time=3;
    var seg=RANGE[time],lo=seg[0],hi=seg[1];
    var rand=val('a1f')==='1';
    var delay=rand?lo+(hi-lo)*Math.random():(lo+hi)/2;
    var lr=val('a1j');lr=lr==null?'0':lr;
    var pick=lr;
    if(lr==='2')pick=(Date.now()%2)?'1':'0';
    if(lr==='3')pick=Math.random()<0.5?'0':'1';
    var jj=val('a1i');jj=jj==null?'0':jj;
    var swap=jj==='1'||(jj==='3'&&Math.random()<0.5);
    var jg=parseInt(val('a1h'),10);if(!(jg>=1&&jg<=10))jg=10;
    var c='<div class="ffKV"><em>Next delay</em><span>'+delay.toFixed(1)+' s</span></div>';
    c+='<div class="ffKV"><em>Wheel</em><span>'+(pick==='1'?'Right wheel':'Left wheel')+'</span></div>';
    c+='<div class="ffKV"><em>Order</em><span>'+(swap?'↓ ↑':'↑ ↓')+'</span></div>';
    c+='<div class="ffKV"><em>Gap</em><span>'+(jg*100)+' ms</span></div>';
    c+='<div class="ffKV"><em>Keys</em><span class="ffMono">'+(pick==='1'?'146 · 147':'141 · 142')+'</span></div>';
    setData('ffCycle',c);
  }

  function loadQuick(){
    setData('ffQuickBlob','<span class="ffDim">Reading…</span>');
    getJSON('/api/feifan/blob?name=quick').then(function(d){
      var len=d.len||0,hex=d.hex||'';
      var c='<div class="ffKV"><em>Blob size</em><span>'+len+' / 256 B</span></div>';
      if(len)c+='<div class="ffMono" style="margin-top:6px">'+hex.slice(0,48)+' …</div>';
      else c+='<span class="ffDim">No 256 B reply yet. The module answers CMD 0xAB only after a full block arrives.</span>';
      setData('ffQuickBlob',c);
    }).catch(function(){setData('ffQuickBlob','<span class="ffDim">Blob endpoint unavailable.</span>');});
  }

  function loadConfig(){
    setData('ffCfgBytes','<span class="ffDim">Reading…</span>');
    getJSON('/api/feifan/blob?name=config').then(function(d){
      var hex=d.hex||'',n=d.len||Math.round(hex.length/3);
      var c='<div class="ffKV"><em>Size</em><span>'+n+' B</span></div>';
      for(var i=0;i<hex.length;i+=36)c+='<div class="ffMono">'+hex.slice(i,i+36)+'</div>';
      setData('ffCfgBytes',c);
    }).catch(function(){setData('ffCfgBytes','<span class="ffDim">Config read failed.</span>');});
  }

  function exportState(){
    try{
      var body=JSON.stringify({v:1,at:new Date().toISOString(),state:state},null,1);
      var blob=new Blob([body],{type:'application/json'});
      var a=document.createElement('a');
      a.href=URL.createObjectURL(blob);
      a.download='p4can-feifan.json';
      document.body.appendChild(a);a.click();
      setTimeout(function(){URL.revokeObjectURL(a.href);if(a.parentNode)a.parentNode.removeChild(a);},900);
      setData('ffBackup','<span class="ffDim">Exported</span>');
    }catch(e){setData('ffBackup','<span class="ffDim">Export failed.</span>');}
  }

  function importState(file){
    var rd=new FileReader();
    rd.onload=function(){
      try{
        var j=JSON.parse(rd.result),s=j.state||j,n=0,k;
        for(k in s){if(Object.prototype.hasOwnProperty.call(s,k)){state[k]=s[k];n++;}}
        save();render();
        setData('ffBackup','<span class="ffDim">Imported</span>');
      }catch(e){setData('ffBackup','<span class="ffDim">Not a valid backup file.</span>');}
    };
    rd.readAsText(file);
  }

  function loadPanel(panelId){
    var p=q(panelId);if(!p)return;
    p.querySelectorAll('[data-ff-load]').forEach(function(b){
      if(b.dataset.done==='1')return;
      if(b.dataset.ffLoad==='export')return;
      b.dataset.done='1';b.click();
    });
  }

  function push(id,v){
    if(link!=='online')return;
    try{fetch('/api/feifan/config',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({id:id,value:v})});}catch(e){}
  }  function set(id,v){state[id]=v;save();render();push(id,v);}

  document.addEventListener('change',function(e){
    var el=e.target;
    if(el&&el.dataset&&el.dataset.ff)set(el.dataset.ff,el.checked?1:0);
  });
  document.addEventListener('click',function(e){
    var el=e.target;
    while(el&&el!==document.body){
      if(el.dataset&&el.dataset.ffSeg){set(el.dataset.ffSeg,el.dataset.v);return;}
      if(el.dataset&&el.dataset.ffAct){
        var code=el.dataset.v;
        if(el.dataset.arm==='1'){
          if(el.dataset.armed!=='1'){
            el.dataset.armed='1';el.classList.add('armed');el.textContent='Confirm';
            setTimeout(function(){
              if(el.dataset.armed==='1'){el.dataset.armed='0';el.classList.remove('armed');el.textContent='Enter';}
            },2800);
            return;
          }
          el.dataset.armed='0';el.classList.remove('armed');el.textContent='Enter';
        }
        sendAction(el.dataset.ffAct,code);
        el.classList.add('on');
        setTimeout(function(){el.classList.remove('on');},600);
        return;
      }
      el=el.parentNode;
    }
  },true);

  document.addEventListener('click',function(e){
    var b=e.target;
    while(b&&b!==document.body&&!(b.dataset&&b.dataset.ffQ))b=b.parentNode;
    if(!b||b===document.body)return;
    var id=b.dataset.ffQ,code=b.dataset.v,off=b.dataset.off;
    var name=lblOf(b);
    if(off){
      var on=!on_(id);
      if(on&&b.dataset.arm!=='1'){
        b.dataset.arm='1';b.classList.add('armed');
        qs('arm');
        setTimeout(function(){
          if(b.dataset.arm==='1'){b.dataset.arm='0';b.classList.remove('armed');qs('idle');}
        },2600);
        return;
      }
      b.dataset.arm='0';b.classList.remove('armed');
      set('q.'+id,on?1:0);
      var ok1=sendAction(id,on?code:off);
      qs(ok1?'sent':'local',
         name+' · '+hex2(on?code:off)+' · '+(on?(isZh()?'开':'ON'):(isZh()?'关':'OFF')));
      return;
    }
    var ok=sendAction(id,code);
    b.classList.add('on');
    setTimeout(function(){b.classList.remove('on');},520);
    qs(ok?'sent':'local',name+' · '+hex2(code));
  },false);

  document.addEventListener('click',function(e){
    var b=e.target;
    while(b&&b!==document.body&&!(b.dataset&&b.dataset.ffLoad))b=b.parentNode;
    if(!b||b===document.body)return;
    var k=b.dataset.ffLoad;
    if(k==='body')loadBody();
    else if(k==='tpms')loadTpms();
    else if(k==='cycle')loadCycle();
    else if(k==='quick')loadQuick();
    else if(k==='config')loadConfig();
    else if(k==='export')exportState();
  },false);

  /* first visit to a panel auto-runs its readers once */
  document.addEventListener('click',function(e){
    var el=e.target;
    while(el&&el!==document.body&&!(el.dataset&&el.dataset.panel))el=el.parentNode;
    if(!el||el===document.body)return;
    var pid=el.dataset.panel;
    setTimeout(function(){loadPanel(pid);},280);
  },false);

  var fi=q('ffImport');
  if(fi)fi.addEventListener('change',function(){
    if(fi.files&&fi.files[0])importState(fi.files[0]);
  });

  var rb=q('ffResetBtn');
  if(rb)rb.onclick=function(){state={};save();render();};

  function probe(){
    if(probing||link==='online')return;probing=true;
    var ctl=typeof AbortController!=='undefined'?new AbortController():null;
    var tm=setTimeout(function(){if(ctl)ctl.abort();},1500);
    fetch('/api/feifan/status',{cache:'no-store',signal:ctl?ctl.signal:undefined})
      .then(function(r){clearTimeout(tm);if(!r.ok)throw 0;return r.json();})
      .then(function(d){
        link='online';
        if(d&&d.config){for(var k in d.config){state[k]=d.config[k];}save();}
        render();
      })
      .catch(function(){clearTimeout(tm);link='local';render();})
      .then(function(){probing=false;});
  }
  window.ffProbe=probe;
  var nav=q('feifanNavBtn');
  if(nav)nav.addEventListener('click',probe);
  var srow=q('feifanSettingsRow');
  if(srow)srow.addEventListener('click',function(){
    if(typeof showPage==='function'){showPage('feifan');probe();}
  });
  render();
})();
</script>
<!--P4CAN-FEIFAN-JS-END-->
"""

(OUT / 'feifan_page.html').write_text(page_html, encoding='utf-8')
(OUT / 'feifan_panels.html').write_text(panels_html, encoding='utf-8')
(OUT / 'feifan.css').write_text(CSS, encoding='utf-8')
(OUT / 'feifan.js').write_text(JS, encoding='utf-8')
(OUT / 'feifan_dict.json').write_text(json.dumps(DICT, ensure_ascii=False, indent=1), encoding='utf-8')

print('page chars', len(page_html), '| panels chars', len(panels_html),
      '| total items', total, '| dict', len(DICT))
