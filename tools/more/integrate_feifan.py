#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integrate the generated 'Beta features' fragments into dashboard_source.html.

Idempotent: every injected region is fenced by a /*P4CAN-FEIFAN-*-START*/ marker,
so re-running this script replaces the previous injection instead of duplicating.
"""
import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / 'firmware' / 'P4can-unlock-more'
DASH = SRC / 'dashboard_source.html'
OUT = REPO / 'build' / 'out'

page = (OUT / 'feifan_page.html').read_text(encoding='utf-8').strip()
panels = (OUT / 'feifan_panels.html').read_text(encoding='utf-8').strip()
css = (OUT / 'feifan.css').read_text(encoding='utf-8').strip()
js = (OUT / 'feifan.js').read_text(encoding='utf-8').strip()
dict_new = json.loads((OUT / 'feifan_dict.json').read_text(encoding='utf-8'))
menu = json.loads((REPO / 'data' / 'feifan-menu-data.json').read_text(encoding='utf-8'))

html = DASH.read_text(encoding='utf-8')
orig_len = len(html)


def strip_marked(text, start, end):
    pat = re.compile(re.escape(start) + r'.*?' + re.escape(end) + r'\n?', re.S)
    return pat.sub('', text)


# ---------------------------------------------------------------- clean slate
for s, e in (('<!--P4CAN-FEIFAN-PAGE-START-->', '<!--P4CAN-FEIFAN-PAGE-END-->'),
             ('<!--P4CAN-FEIFAN-PANELS-START-->', '<!--P4CAN-FEIFAN-PANELS-END-->'),
             ('<!--P4CAN-FEIFAN-JS-START-->', '<!--P4CAN-FEIFAN-JS-END-->'),
             ('/*P4CAN-FEIFAN-CSS-START*/', '/*P4CAN-FEIFAN-CSS-END*/'),
             ('/*P4CAN-FEIFAN-DICT-START*/', '/*P4CAN-FEIFAN-DICT-END*/')):
    html = strip_marked(html, s, e)
html = re.sub(r'<button class="navbtn[^"]*" data-page="feifan" id="feifanNavBtn">[^<]*</button>', '', html)
html = re.sub(r'\n?<div class="listrow clickable" id="feifanSettingsRow">.*?</div>\n', '\n', html, flags=re.S)

# --------------------------------------------------------------- 1. CSS block
last_style = html.rfind('</style>')
assert last_style > 0, 'no </style> found'
html = html[:last_style] + css + '\n' + html[last_style:]

# --------------------------------------------------------- 2. page + panels
anchor_page = '</main>\n</div>\n<section class="panel" id="panelVisionControl">'
assert html.count(anchor_page) == 1, 'page anchor not unique: %d' % html.count(anchor_page)
html = html.replace(anchor_page, '</main>\n' + page + '\n</div>\n<section class="panel" id="panelVisionControl">')

anchor_panels = '<nav aria-label="Dashboard" class="bottomnav'
assert html.count(anchor_panels) == 1, 'panels anchor not unique'
html = html.replace(anchor_panels, panels + '\n' + anchor_panels)

# ------------------------------------------------------------ 3. nav button
nav_lab = '<button class="navbtn hiddenByProfile" data-page="lab" id="labNavBtn">LAB</button>'
assert html.count(nav_lab) == 1, 'nav anchor not unique'
html = html.replace(nav_lab, nav_lab + '<button class="navbtn" data-page="feifan" id="feifanNavBtn">More</button>')

# ------------------------------------------------- 4. settings entry (row)
_n = sum(len(s['items']) for g in menu['groups'] for s in g['sections'])
_g = len(menu['groups'])
settings_row = ('\n<div class="listrow clickable" id="feifanSettingsRow"><div>'
                '<div class="listkey">More features</div>'
                '<div class="listdesc">TSL + Albert controls · %d entries in %d groups</div></div>'
                '<span class="chev">›</span></div>' % (_n, _g))
summon_row = ('<div class="listrow clickable" data-panel="panelSummon"><div><div class="listkey">Summon Status</div>'
              '<div class="listdesc" id="setSumDesc">View the current Summon session and status.</div></div>'
              '<span class="chev">›</span></div>')
assert html.count(summon_row) == 1, 'settings anchor not unique'
html = html.replace(summon_row, summon_row + settings_row)

# ----------------------------------------------------------------- 5. script
anchor_zh = '<!--P4CAN-ZH-START-->'
assert html.count(anchor_zh) == 1, 'zh anchor not unique'
html = html.replace(anchor_zh, js + '\n' + anchor_zh)

# --------------------------------------------------------- 6. merge the DICT
m = re.search(r'var DICT=\{', html)
assert m, 'DICT literal not found'
i = m.end() - 1
depth = 0
j = i
while j < len(html):
    c = html[j]
    if c == '{':
        depth += 1
    elif c == '}':
        depth -= 1
        if depth == 0:
            break
    j += 1
literal = html[i:j + 1]
try:
    existing = json.loads(literal)
except Exception as exc:  # noqa: BLE001
    print('DICT literal is not plain JSON:', exc)
    sys.exit(1)

added, conflicts = {}, {}
for k, v in dict_new.items():
    if k in existing:
        if existing[k] != v:
            conflicts[k] = (existing[k], v)
        continue
    added[k] = v

if added:
    payload = json.dumps(added, ensure_ascii=False, separators=(',', ':'))
    inject = ('\n  /*P4CAN-FEIFAN-DICT-START*/\n'
              '  Object.assign(DICT,' + payload + ');\n'
              '  /*P4CAN-FEIFAN-DICT-END*/\n')
    anchor = "  var cur='zh';"
    assert html.count(anchor) == 1, 'cur anchor not unique'
    html = html.replace(anchor, inject + anchor)

print('DICT: existing %d, added %d, conflicts %d' % (len(existing), len(added), len(conflicts)))
for k, (old, new) in list(conflicts.items())[:20]:
    print('   conflict %-40r existing=%r wanted=%r' % (k, old, new))

# ------------------------------------------------------------------- commit
backup = DASH.with_suffix('.html.pre-feifan.bak')
if not backup.exists():
    shutil.copy2(DASH, backup)
    print('backup ->', backup.name)
DASH.write_text(html, encoding='utf-8')
print('dashboard_source.html: %d -> %d chars (+%d)' % (orig_len, len(html), len(html) - orig_len))
