#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate docs/FEATURES.md and docs/PROTOCOL.md from data/feifan-menu-data.json.

Keeping the docs machine-generated means the feature table can never drift away
from what the page actually renders -- if an entry is renamed in the JSON, rerun
this script and the docs follow.

    python tools/more/gen_docs.py
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = json.loads((REPO / 'data' / 'feifan-menu-data.json').read_text(encoding='utf-8'))
DOCS = REPO / 'docs'
DOCS.mkdir(exist_ok=True)

KIND = {'sw': '开关', 'seg': '分段选择', 'grid': '网格按钮', 'num': '数值', 'info': '只读信息'}
P4 = {'需新增': '需新增', '已有': '已有', '本地UI': '本地 UI', '不可达': '不可达'}

# 0xBB 快捷键单字节值：从 187 帧的实际发送日志确认（证据 A）
BB_VALUES = [
    ('0x5B / 91', '前爆闪', 'frontStrobe'),
    ('0x5E / 94', '后爆闪', 'rearStrobe'),
    ('0x5A / 90', '脉冲喇叭', 'pulseHorn'),
    ('0x5F / 95', '领航喇叭', 'gentryHorn'),
    ('0x1D / 29', '电池预热 开', 'batteryPreheatOn'),
    ('0x1C / 28', '电池预热 关', 'batteryPreheatOff'),
]


def total_items():
    return sum(len(s['items']) for g in DATA['groups'] for s in g['sections'])


def gen_features():
    out = []
    w = out.append
    w('# 功能清单 / Feature index')
    w('')
    w('> 本文件由 `tools/more/gen_docs.py` 从 `data/feifan-menu-data.json` 自动生成，请勿手改。')
    w('')
    w('共 **%d** 项，分为 **%d** 组。证据等级：`A` 反编译实锤 · `B` 设计图推断 · `C` 本地 UI。'
      % (total_items(), len(DATA['groups'])))
    w('')
    w('## 总览')
    w('')
    w('| # | 分组 | 英文 | 项数 | 说明 |')
    w('|---|---|---|---:|---|')
    for n, g in enumerate(DATA['groups'], 1):
        cnt = sum(len(s['items']) for s in g['sections'])
        w('| %d | %s | %s | %d | %s |' % (n, g['name'], g.get('en', ''), cnt, g.get('note', '')))
    w('')
    for n, g in enumerate(DATA['groups'], 1):
        w('## %d. %s / %s' % (n, g['name'], g.get('en', '')))
        w('')
        if g.get('note'):
            w('> %s' % g['note'])
            w('')
        if not g['sections']:
            w('本组为追溯清单，内容见 `docs/REVERSE.md`。')
            w('')
            continue
        for m, sec in enumerate(g['sections'], 1):
            w('### %d.%d %s / %s' % (n, m, sec['name'], sec.get('en', '')))
            w('')
            for it in sec['items']:
                w('#### `%s` %s · %s' % (it['id'], it.get('n', ''), it.get('en', '')))
                w('')
                meta = ['类型：**%s**' % KIND.get(it.get('t'), it.get('t', '—')),
                        '证据：**%s**' % it.get('lv', '—'),
                        '状态：%s' % P4.get(it.get('p4'), it.get('p4', '—'))]
                w('- ' + ' · '.join(meta))
                if it.get('d'):
                    w('- 说明：%s' % it['d'])
                if it.get('im'):
                    w('- 实现：%s' % it['im'])
                if it.get('src'):
                    w('- 来源：%s' % it['src'])
                if it.get('api'):
                    w('- 接口：`%s`' % it['api'])
                if it.get('o'):
                    opts = ' / '.join('`%s` %s' % (o['v'], o['l']) for o in it['o'])
                    w('- 取值：%s' % opts)
                w('')
    (DOCS / 'FEATURES.md').write_text('\n'.join(out) + '\n', encoding='utf-8')
    return total_items()


def gen_protocol():
    fr = DATA['frame']
    out = []
    w = out.append
    w('# TSL BLE / 配置块协议')
    w('')
    w('> 本文件由 `tools/more/gen_docs.py` 从 `data/feifan-menu-data.json` 自动生成，请勿手改。')
    w('')
    w('本文只涵盖实现 `更多功能` 页所需的帧与位域，不涉及鉴权细节以外的流程。')
    w('')
    w('## 1. 帧格式')
    w('')
    w('```text')
    w(fr['format'])
    w('```')
    w('')
    w('- 校验：`%s`' % fr['sum'])
    w('- 传输：%s' % fr['transport'])
    w('- 配置块：%s' % fr['config'])
    w('')
    w('## 2. 命令字')
    w('')
    w('| 命令 | 十进制 | 用途 | 证据 |')
    w('|---|---:|---|---|')
    for row in DATA['commands']:
        w('| `%s` | %s | %s | %s |' % (row[0], row[1], row[2], row[3]))
    w('')
    w('实现本页只需要其中四条：')
    w('')
    w('- `0xA3 / 163` —— **写**：按位域清位、置值，整块回写')
    w('- `0xAB / 171` —— **读**：256 字节配置块，按位域取值')
    w('- `0xA7 / 167` —— 车身动作，payload 为 1 字节动作码')
    w('- `0xBB / 187` —— 滚轮/快捷键，payload 为 1 字节值')
    w('')
    w('## 3. 快捷键单字节值（0xBB）')
    w('')
    w('| 值 | 动作 | 内部名 |')
    w('|---|---|---|')
    for v, label, key in BB_VALUES:
        w('| `%s` | %s | `%s` |' % (v, label, key))
    w('')
    w('## 4. 位域表')
    w('')
    w('读：`value = (byte[offset] >>> shift) & mask`')
    w('')
    w('写：')
    w('')
    w('```c')
    w('cfg[offset] = (cfg[offset] & ~(mask << shift)) | ((value & mask) << shift);')
    w('// 改完全部字段后，用 CMD 0xA3 一次性整块回写')
    w('```')
    w('')
    w('共 **%d** 个字段，取自反编译的 `SETTINGS` 数组，偏移与掩码为原值。' % len(DATA['fields_full']))
    w('')
    w('| 字段 | 名称 | 分组 | byte | shift | mask | 取值 |')
    w('|---|---|---|---:|---:|---:|---|')
    for f in DATA['fields_full']:
        off, shift, mask = f['bit']
        opts = ' / '.join('%s=%s' % (o[0], o[1]) for o in f.get('options', [])) or '0/1'
        if len(opts) > 90:
            opts = opts[:87] + '…'
        w('| `%s` | %s | %s | %d | %d | %d | %s |'
          % (f['id'], f['name'], f.get('section', ''), off, shift, mask, opts))
    w('')
    w('## 5. 前端契约（待实现）')
    w('')
    w('页面已经按下列契约发请求，`web_api.h` 补上即可：')
    w('')
    w('| 方法 | 路径 | 请求体 | 说明 |')
    w('|---|---|---|---|')
    for row in DATA['apis']:
        path = row[1]
        body = '`{id, value}`' if 'config' in path else ('`{code}` / `{wheel,direction}` / `{quick}`'
                                                       if 'action' in path else '—')
        w('| `%s` | `%s` | %s | %s |' % (row[0], path, body, row[2]))
    w('')
    w('补充两个页面已用到、上表未列的端点：')
    w('')
    w('| 方法 | 路径 | 说明 |')
    w('|---|---|---|')
    w('| `GET` | `/api/feifan/blob` | 导出/导入整块配置（备份用） |')
    w('| `GET` | `/api/ota/status` | 固件更新进度（上游已实现） |')
    w('')
    (DOCS / 'PROTOCOL.md').write_text('\n'.join(out) + '\n', encoding='utf-8')


if __name__ == '__main__':
    n = gen_features()
    gen_protocol()
    print('FEATURES.md  %d 项' % n)
    print('PROTOCOL.md  %d 个位域' % len(DATA['fields_full']))
