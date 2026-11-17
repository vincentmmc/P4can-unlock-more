#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enhance the existing firmware-update panel (panelOta) in dashboard_source.html.

The upstream firmware already ships a working OTA path:

    POST /update              multipart, any file field name, written via Update.h
    GET  /api/ota/status      {ok,inProgress,error,stage,updateError,attempt,...}
    otadata + app0(ota_0) + app1(ota_1)   4.5 MB each (large_fat_32MB.csv)

What was missing on the front end: the panel gave no version context, accepted
any file without a size check, had no drag-and-drop, and started writing the
flash on the first tap. This patch adds exactly that, without touching the
original upload routine.

Idempotent: each injected region is fenced by a /*P4CAN-OTA-*-START*/ marker.
Run order:  gen_feifan.py -> integrate_feifan.py -> patch_ota.py -> build_dashboard.py
"""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / 'firmware' / 'P4can-unlock-more'
DASH = SRC / 'dashboard_source.html'

# app0 / app1 size in large_fat_32MB.csv: 0x480000
APP_PART_BYTES = 0x480000

CSS = r"""/*P4CAN-OTA-CSS-START*/
body #panelOta .otaInfo{margin-top:10px;padding:14px 15px;border-radius:17px;background:var(--card);border:1px solid var(--line);display:grid;gap:10px}
body #panelOta .otaInfoRow{display:flex;align-items:baseline;justify-content:space-between;gap:12px;min-width:0}
body #panelOta .otaInfoK{font-size:11px;color:var(--muted);flex:0 0 auto}
body #panelOta .otaInfoV{font-size:12px;font-weight:640;color:var(--ink);text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
body #panelOta .otaInfoV.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-weight:500;font-size:11.5px}
body #panelOta .otaLast{margin-top:10px;padding:11px 13px;border-radius:14px;background:rgba(128,128,128,.09);font-size:11.5px;line-height:1.6;color:var(--ink);overflow-wrap:anywhere}
body #panelOta .otaLast.warn{background:rgba(214,158,46,.14)}
body #panelOta .otaLast.bad{background:rgba(206,74,74,.14)}
body #panelOta .otaDrop{border-radius:20px;outline:2px dashed transparent;outline-offset:3px;transition:outline-color .16s,background .16s}
body #panelOta .otaDrop.hot{outline-color:var(--ink);background:rgba(128,128,128,.07)}
body #panelOta #otaUpload{white-space:normal;line-height:1.4}
body #panelOta #otaUpload.confirm{background:#c0392b!important;color:#fff!important}
[data-theme="dark"] body #panelOta .otaLast.warn{background:rgba(224,175,70,.10);color:#e8b95a}
[data-theme="dark"] body #panelOta .otaLast.bad{background:rgba(240,120,120,.10);color:#f0908f}
/*P4CAN-OTA-CSS-END*/"""

PANEL = r"""<!--P4CAN-OTA-PANEL-START-->
<div class="otaInfo">
<div class="otaInfoRow"><span class="otaInfoK">Current firmware</span><span class="otaInfoV mono" id="otaFwVersion">—</span></div>
<div class="otaInfoRow"><span class="otaInfoK">Application partition</span><span class="otaInfoV mono">ota_0 / ota_1 · 4.5 MB</span></div>
<div class="otaInfoRow"><span class="otaInfoK">Upload endpoint</span><span class="otaInfoV mono">POST /update</span></div>
</div>
<div class="otaLast" id="otaLastResult">No update attempt recorded in this session.</div>
<!--P4CAN-OTA-PANEL-END-->"""

JS = r"""<!--P4CAN-OTA-JS-START-->
<script>
(function(){
  var panel=document.getElementById('panelOta');
  if(!panel)return;
  var MAX=__APP_PART__;
  var SMALL=200*1024;
  var fileEl=document.getElementById('otaFile');
  var nameEl=document.getElementById('otaFileName');
  var btn=document.getElementById('otaUpload');
  var msgEl=document.getElementById('otaMsg');
  var lastEl=document.getElementById('otaLastResult');
  var fwEl=document.getElementById('otaFwVersion');
  var baseLabel=btn?btn.textContent:'';
  var armed=false,armTimer=null;
  var badMagic=false,magicName='';
  var TEXT=__OTA_TEXT__;

  /* The translator is sealed inside its own IIFE, so DICT and cur are not
     reachable here. p4canLang is the key it seeds itself from, and setLang()
     rewrites it on every switch, so reading it keeps us in sync. */
  function isZh(){
    try{return localStorage.getItem('p4canLang')!=='en';}catch(e){return true;}
  }
  function T(en){
    if(isZh()&&Object.prototype.hasOwnProperty.call(TEXT,en))return TEXT[en];
    return en;
  }
  function Tf(tpl,vars){
    var s=T(tpl);
    for(var k in vars)if(Object.prototype.hasOwnProperty.call(vars,k))s=s.split('{'+k+'}').join(vars[k]);
    return s;
  }
  function fmt(n){
    n=Number(n)||0;
    if(n>=1048576)return (n/1048576).toFixed(2)+' MB';
    if(n>=1024)return Math.round(n/1024)+' KB';
    return n+' B';
  }
  function setMsg(kind,text){
    if(!msgEl)return;
    msgEl.textContent=text;
    msgEl.style.color=kind==='err'?'#c0392b':kind==='warn'?'#a97c18':'';
  }

  /* ---- current firmware version ---- */
  fetch('/api/system/stats',{cache:'no-store'})
    .then(function(r){return r.ok?r.json():null})
    .then(function(d){
      var v=d&&d.fwVersion;
      if(v&&fwEl){fwEl.textContent='Universal '+v;return;}
      if(fwEl){
        var s=document.getElementById('sysFw');
        var txt=s&&s.textContent?s.textContent.trim():'';
        fwEl.textContent=(txt&&txt!=='—')?txt.replace(/^P4-CAN\s*/,''):'—';
      }
    })
    .catch(function(){});

  /* ---- last attempt, from the firmware's own diagnostics ---- */
  fetch('/api/ota/status',{cache:'no-store'})
    .then(function(r){return r.ok?r.json():null})
    .then(function(d){
      if(!d||!lastEl)return;
      if(d.inProgress){
        lastEl.className='otaLast warn';
        lastEl.textContent=Tf('A flash is in progress · {v} received.',{v:fmt(d.receivedBytes)});
        return;
      }
      if(!Number(d.attempt)){
        lastEl.className='otaLast';
        lastEl.textContent=T('No update attempt recorded in this session.');
        return;
      }
      if(d.ok){
        lastEl.className='otaLast';
        lastEl.textContent=Tf('Last attempt #{n} succeeded · {v} written.',{n:d.attempt,v:fmt(d.receivedBytes)});
        return;
      }
      var t=Tf('Last attempt #{n} failed',{n:d.attempt});
      if(d.error)t+=' · '+d.error;
      if(d.stage)t+=' · stage '+d.stage;
      lastEl.className='otaLast bad';
      lastEl.textContent=t+'.';
    })
    .catch(function(){});

  /* ---- file inspection ---- */
  /* every ESP32 application image starts with 0xE9. merged / bootloader /
     partition-table images do not, and the device would silently reject them. */
  function probeMagic(f){
    badMagic=false;magicName=f?f.name:'';
    if(!f||!f.slice||typeof FileReader==='undefined')return;
    try{
      var fr=new FileReader();
      fr.onload=function(){
        var u=new Uint8Array(fr.result||[]);
        if(!u.length)return;
        if(magicName!==(fileEl&&fileEl.files&&fileEl.files[0]?fileEl.files[0].name:''))return;
        if(u[0]!==0xE9){
          badMagic=true;
          setMsg('err',Tf('Not an application image: first byte is 0x{b}, expected 0xE9. This looks like a bootloader, partition table or merged flash image — P4-CAN would reject it. Pick the .ino.bin.',
                          {b:u[0].toString(16).toUpperCase()}));
          if(armed)disarm();   /* 读头比点击慢时，也要把确认态撤回来 */
        }
      };
      fr.readAsArrayBuffer(f.slice(0,1));
    }catch(e){}
  }
  function inspect(){
    var f=fileEl&&fileEl.files&&fileEl.files[0];
    if(!f){if(nameEl)nameEl.textContent=T('No file selected');return null;}
    var size=fmt(f.size);
    if(nameEl)nameEl.textContent=f.name+' · '+size;
    if(f.size>MAX){
      setMsg('err',Tf('Too large: {v} exceeds the {m} application partition. This image cannot be installed over the air.',
                      {v:size,m:fmt(MAX)}));
    }else if(!/\.bin$/i.test(f.name)){
      setMsg('warn',T('Name does not end in .bin — confirm this is the Arduino application binary, not a merged flash image.'));
    }else if(f.size<SMALL){
      setMsg('warn',Tf('Only {v} — unusually small for an application image. Double-check the file.',{v:size}));
    }else{
      setMsg('ok',Tf('Ready · {v} will be written to the spare OTA slot.',{v:size}));
    }
    probeMagic(f);
    return f;
  }
  if(fileEl)fileEl.addEventListener('change',function(){if(armed)disarm();inspect();});

  /* ---- drag & drop ---- */
  var drop=panel.querySelector('.ota');
  if(drop){
    if(drop.parentElement)drop.parentElement.classList.add('otaDrop');
    var zone=drop.parentElement||drop;
    ['dragenter','dragover'].forEach(function(ev){
      zone.addEventListener(ev,function(e){e.preventDefault();zone.classList.add('hot');});
    });
    ['dragleave','dragend'].forEach(function(ev){
      zone.addEventListener(ev,function(e){e.preventDefault();zone.classList.remove('hot');});
    });
    zone.addEventListener('drop',function(e){
      e.preventDefault();zone.classList.remove('hot');
      var dt=e.dataTransfer;
      if(!dt||!dt.files||!dt.files.length||!fileEl)return;
      try{
        var tr=new DataTransfer();
        tr.items.add(dt.files[0]);
        fileEl.files=tr.files;
      }catch(err){
        setMsg('warn',T('This browser blocks programmatic file assignment — use the Choose button instead.'));
        return;
      }
      if(armed)disarm();
      inspect();
    });
  }

  /* ---- two-tap confirmation, called from the original upload handler ---- */
  function disarm(){
    armed=false;
    clearTimeout(armTimer);
    if(btn){
      btn.classList.remove('confirm');
      btn.textContent=baseLabel;
    }
  }
  window.p4canOtaConfirm=function(f){
    if(!f)return true;
    if(badMagic){
      setMsg('err',T('Refused: this file is not an ESP32 application image. Upload the .ino.bin produced by the build.'));
      disarm();
      return false;
    }
    if(armed){disarm();return true;}
    if(f.size>MAX){
      setMsg('err',Tf('Too large: {v} exceeds the {m} application partition. This image cannot be installed over the air.',
                      {v:fmt(f.size),m:fmt(MAX)}));
      return false;
    }
    armed=true;
    if(btn){
      btn.textContent=T('Confirm flash')+' · '+fmt(f.size);
      btn.classList.add('confirm');
    }
    setMsg('warn',Tf('Tap again to write {n} to the spare slot. P4-CAN restarts when the write completes.',{n:f.name}));
    clearTimeout(armTimer);
    armTimer=setTimeout(disarm,6000);
    return false;
  };

  /* leaving the panel must not leave a primed confirm button behind */
  var back=panel.querySelector('.backbtn');
  if(back)back.addEventListener('click',function(){if(armed)disarm();});

  /* The upstream handler builds its progress line by concatenation, so the
     exact-match translator can never catch it. Watch the node instead. */
  var FIXED=[['Preparing upload…','准备上传…'],
             ['Flash successful · rebooting','刷写成功 · 正在重启']];
  if(msgEl){
    new MutationObserver(function(){
      if(!isZh())return;
      var t=msgEl.textContent||'';
      var m=/^Uploading (\d+)%$/.exec(t);
      if(m){msgEl.textContent='正在上传 '+m[1]+'%';return;}
      for(var i=0;i<FIXED.length;i++){
        if(t===FIXED[i][0]){msgEl.textContent=FIXED[i][1];return;}
      }
    }).observe(msgEl,{childList:true,characterData:true,subtree:true});
  }
})();
</script>
<!--P4CAN-OTA-JS-END-->"""

DICT = {
    'Current firmware': '当前固件',
    'Application partition': '应用分区',
    'Upload endpoint': '上传端点',
    'No update attempt recorded in this session.': '本次会话还没有刷写记录。',
    'A flash is in progress · {v} received.': '正在刷写 · 已接收 {v}。',
    'Last attempt #{n} succeeded · {v} written.': '上次（第 {n} 次）成功 · 已写入 {v}。',
    'Last attempt #{n} failed': '上次（第 {n} 次）失败',
    'No file selected': '未选择文件',
    'Name does not end in .bin — confirm this is the Arduino application binary, not a merged flash image.':
        '文件名不以 .bin 结尾 — 请确认这是应用固件，不是整片 flash 镜像。',
    'Not an application image: first byte is 0x{b}, expected 0xE9. This looks like a bootloader, partition table or merged flash image — P4-CAN would reject it. Pick the .ino.bin.':
        '不是应用固件：首字节是 0x{b}，应为 0xE9。这看起来是引导程序、分区表或整片镜像 — 设备会拒收。请选 .ino.bin。',
    'Refused: this file is not an ESP32 application image. Upload the .ino.bin produced by the build.':
        '已拒绝：该文件不是 ESP32 应用镜像，请上传编译产物里的 .ino.bin。',
    'Too large: {v} exceeds the {m} application partition. This image cannot be installed over the air.':
        '文件过大：{v} 超过 {m} 的应用分区，无法在线刷入。',
    'Only {v} — unusually small for an application image. Double-check the file.':
        '仅 {v} — 作为应用固件偏小，请再确认文件。',
    'Ready · {v} will be written to the spare OTA slot.': '就绪 · 将把 {v} 写入备用 OTA 分区。',
    'Confirm flash': '确认刷入',
    'Tap again to write {n} to the spare slot. P4-CAN restarts when the write completes.':
        '再点一次，把 {n} 写入备用分区。写入完成后 P4-CAN 会重启。',
    'This browser blocks programmatic file assignment — use the Choose button instead.':
        '当前浏览器不允许程序写入 file 控件，请改用“选择文件”按钮。',
}

ANCHOR_PANEL = ('<div class="panelSub">Upload an Arduino application .bin. '
                'P4-CAN reboots automatically after a successful flash.</div>')
ANCHOR_HOOK = ("const f=$('otaFile').files[0],msg=$('otaMsg'),pr=$('otaProgress'),"
               "bar=$('otaBar');if(!f||otaUploading)return;")
HOOK_ADDED = ("\n if(typeof window.p4canOtaConfirm==='function'"
              "&&!window.p4canOtaConfirm(f))return;")


def strip_marked(text, start, end):
    return re.sub(re.escape(start) + r'.*?' + re.escape(end) + r'\n?', '', text, flags=re.S)


html = DASH.read_text(encoding='utf-8')
before = len(html)

for s, e in (('<!--P4CAN-OTA-PANEL-START-->', '<!--P4CAN-OTA-PANEL-END-->'),
             ('<!--P4CAN-OTA-JS-START-->', '<!--P4CAN-OTA-JS-END-->'),
             ('/*P4CAN-OTA-CSS-START*/', '/*P4CAN-OTA-CSS-END*/'),
             ('/*P4CAN-OTA-DICT-START*/', '/*P4CAN-OTA-DICT-END*/')):
    html = strip_marked(html, s, e)

# the confirm hook sits inline in the upstream handler, outside any marker
html = html.replace(HOOK_ADDED, '')

# ------------------------------------------------------------- 1. info panel
assert html.count(ANCHOR_PANEL) == 1, 'panelOta sub anchor not unique: %d' % html.count(ANCHOR_PANEL)
html = html.replace(ANCHOR_PANEL, ANCHOR_PANEL + '\n' + PANEL)

# ------------------------------------------------------------- 2. hook line
assert html.count(ANCHOR_HOOK) == 1, 'ota upload head not unique: %d' % html.count(ANCHOR_HOOK)
html = html.replace(ANCHOR_HOOK, ANCHOR_HOOK + HOOK_ADDED)

# ----------------------------------------------------------------- 3. styles
last_style = html.rfind('</style>')
assert last_style > 0, 'no </style> found'
html = html[:last_style] + CSS + '\n' + html[last_style:]

# ----------------------------------------------------------------- 4. script
assert html.count('</body>') == 1, 'expected exactly one </body>'
html = html.replace('</body>', JS + '\n</body>', 1)

# ------------------------------------------------------------------- 5. DICT
m = re.search(r'var DICT=\{', html)
assert m, 'DICT literal not found'
i = m.end() - 1
depth, j = 0, i
while j < len(html):
    c = html[j]
    if c == '{':
        depth += 1
    elif c == '}':
        depth -= 1
        if depth == 0:
            break
    j += 1
existing = json.loads(html[i:j + 1])

added, conflicts = {}, {}
for k, v in DICT.items():
    if k in existing:
        if existing[k] != v:
            conflicts[k] = (existing[k], v)
        continue
    added[k] = v

if added:
    payload = json.dumps(added, ensure_ascii=False, separators=(',', ':')).encode('ascii', 'backslashreplace').decode('ascii')
    inject = ('\n  /*P4CAN-OTA-DICT-START*/\n'
              '  Object.assign(DICT,' + payload + ');\n'
              '  /*P4CAN-OTA-DICT-END*/\n')
    anchor = "  var cur='zh';"
    assert html.count(anchor) == 1, 'cur anchor not unique'
    html = html.replace(anchor, inject + anchor)

html = html.replace('__APP_PART__', str(APP_PART_BYTES))
html = html.replace('__OTA_TEXT__', json.dumps(DICT, ensure_ascii=True))
DASH.write_text(html, encoding='utf-8')

print('DICT      : +%d entries, %d conflicts' % (len(added), len(conflicts)))
for k, (old, new) in list(conflicts.items())[:10]:
    print('   conflict %-46r existing=%r wanted=%r' % (k, old, new))
print('patched   : %d -> %d chars (+%d)' % (before, len(html), len(html) - before))
