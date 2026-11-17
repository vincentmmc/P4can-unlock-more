#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补齐看板中文词条（主要是「实验 / LAB」页）。

`dashboard_source.html` 里的 P4CAN-ZH 块是一张 en -> zh 精确匹配表，
上游只覆盖了首页 / 设备 / 设置，实验页整页仍是英文。这个脚本把缺的词条
合并进 DICT，幂等：已有词条一律保留（先插入者胜），只补新的。

    python tools/more/patch_zh.py

注意：只写 en -> zh 单向映射。切回英文靠页面自己的 textMemo 还原原文，
所以这里不需要反向词条 —— 加了反而会和 `2 次` / `闪 2 次` 这类撞车。
"""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DASH = REPO / 'firmware' / 'P4can-unlock-more' / 'dashboard_source.html'

START = '<!--P4CAN-ZH-START-->'
END = '<!--P4CAN-ZH-END-->'
DYN_START = '<!--P4CAN-ZH-DYN-START-->'
DYN_END = '<!--P4CAN-ZH-DYN-END-->'

# 运行时状态兜底
# ----------------
# 实验页的「驾驶状态」不是静态文本：renderR79Summary() 每 500 ms 用英文重新
# 写一遍 #r79TxBig / #r79TxSub。中文包的 MutationObserver 能翻，但下一次渲染
# 又覆盖回英文，视觉上会闪。这里只盯这几个已知节点，按 ' · ' 分段查表。
DYN_JS = r'''<!--P4CAN-ZH-DYN-START-->
<script>
(function(){
  var IDS=['r79TxBig','r79TxSub','labGearBig','homeR79State','homeR79Reason'];
  var RULES=[
    [/^Waiting$/,'等待中'],[/^Active$/,'激活'],[/^Park standby$/,'驻车待机'],
    [/^Ready$/,'就绪'],[/^AP Wait$/,'AP 等待'],[/^AP engaged$/,'AP 已启用'],
    [/^Summon$/,'召唤'],[/^CAN OFFLINE$/,'CAN 离线'],[/^DEFAULT$/,'默认'],
    [/^WAIT TEMPLATE$/,'等待模板'],[/^BUSY$/,'处理中'],[/^BLOCKED$/,'已拦截'],
    [/^SUSPENDED$/,'已挂起'],[/^READY$/,'就绪'],[/^ACTIVE$/,'激活']
  ];
  function zh(s){
    if(!s)return s;
    var parts=String(s).split(' · '),out=[],i,k,p,n;
    for(i=0;i<parts.length;i++){
      p=parts[i].trim(); n=null;
      for(k=0;k<RULES.length;k++){
        if(RULES[k][0].test(p)){n=p.replace(RULES[k][0],RULES[k][1]);break;}
      }
      out.push(n===null?parts[i]:n);
    }
    return out.join(' · ');
  }
  function isZh(){try{return localStorage.getItem('p4canLang')!=='en';}catch(e){return true;}}
  function tick(){
    if(!isZh())return;
    for(var i=0;i<IDS.length;i++){
      var el=document.getElementById(IDS[i]); if(!el)continue;
      var t=el.textContent; if(!t)continue;
      var n=zh(t);
      if(n!==t)el.textContent=n;
    }
  }
  setInterval(tick,600);
  tick();
})();
</script>
<!--P4CAN-ZH-DYN-END-->'''


# ---------------------------------------------------------------- 词表
# 约定：
#   散文、控件标题、状态标签  -> 翻译
#   帧 ID、位域表达式、纯数值  -> 保留原文（DICT 里不出现，页面就不动它）
#   `N s` / `N ms` 由页面正则自动处理，不要在这里重复
ZH_EXTRA = {
    # ---- 实验页主页
    'Research tools. Read-only unless marked experimental.': '研究工具。除标注实验性外均为只读。',
    'Research Tools': '研究工具',
    'Driving State · live': '驾驶状态 · 实时',
    'Waiting': '等待中',
    'R79 TX · Reason —': 'R79 发送 · 原因 —',
    'ALC STATE': 'ALC 状态',
    'Lane': '车道',
    'LEFT': '左',
    'RIGHT': '右',
    'R79 AP Control': 'R79 AP 控制',
    'Block or delay R79 during AP.': 'AP 期间拦截或延迟 R79。',
    'R79 Status': 'R79 状态',
    'View R79 send status.': '查看 R79 发送状态。',
    'Summon Heartbeat Override': '召唤心跳覆盖',
    'Test Summon heartbeat signals.': '测试召唤心跳信号。',
    'Auto Lane Change Enable': '自动变道使能',
    'Test lane-change enable signals.': '测试变道使能信号。',
    'CAN Research Capture': 'CAN 研究抓包',
    'Record and download CAN signals.': '录制并下载 CAN 信号。',
    'Driver Monitoring Capture': '驾驶员监测抓包',
    'Record driver-monitoring signals.': '录制驾驶员监测信号。',
    'EXP': '实验性',

    # ---- R79 AP 控制面板
    'Set R79 behavior during AP and manual driving independently.': '分别设置 AP 与手动驾驶时的 R79 行为。',
    'Allow R79 During Manual Driving': '手动驾驶时允许 R79',
    'OFF keeps the default AP behavior': '关闭则保持默认 AP 行为',
    'Separate setting · default OFF': '独立设置 · 默认关闭',
    'AP Policy': 'AP 策略',
    'Block during AP': 'AP 期间拦截',
    'Delay after AP': 'AP 后延迟',
    'AP DELAY (S)': 'AP 延迟 (秒)',
    'Gate state': '门控状态',
    'Remaining': '剩余',
    'ON bypasses only manual D/R suppression. Existing AP policy and transport safety remain active.':
        '开启仅绕过手动挡 D/R 抑制，AP 策略与传输安全仍然生效。',
    'Loading saved settings…': '正在载入已保存设置…',

    # ---- 召唤心跳面板
    '0x3F8 UI_driverAssistControl · UI_summonHeartbeat bits 2–3 · raw values 0–3.':
        '0x3F8 UI_driverAssistControl · UI_summonHeartbeat bit 2–3 · 原始值 0–3。',
    'Continuous Override': '持续覆盖',
    'Applies the selected raw value to every valid stock frame': '对每一帧有效的原厂帧应用所选原始值',
    'Raw Value': '原始值',
    'Two-bit field · 0, 1, 2 or 3': '两位字段 · 0、1、2 或 3',
    'RUNTIME STATE': '运行状态',
    'GATE': '门控',
    'Stock raw / age': '原厂原始值 / 时效',
    'Selected / last applied': '所选 / 上次应用',
    'Applied / TX fail / blocked': '已应用 / 发送失败 / 拦截',
    'Session-only experimental override. It is OFF after every reboot and CAN full-recovery. Other 0x3F8 fields are preserved and existing transport safety checks remain active.':
        '仅本次会话的实验性覆盖，每次重启与 CAN 完全恢复后都会关闭。0x3F8 的其它字段保持原样，现有传输安全检查仍然生效。',
    'Loading session state…': '正在载入会话状态…',

    # ---- 自动变道使能面板
    'Experimental 0x293 UI_autoLaneChangeEnable injection. Independent from the production CAN B 0x3F8 compositor.':
        '实验性 0x293 UI_autoLaneChangeEnable 注入，与正式的 CAN B 0x3F8 合成器相互独立。',
    '0x293 UI_chassisControl · UI_autoLaneChangeEnable bits 24–25 → raw 1 · AP active':
        '0x293 UI_chassisControl · UI_autoLaneChangeEnable bit 24–25 → 原始值 1 · AP 激活',
    '0x293 TX Target': '0x293 发送目标',
    '0x293 TX A OK / FAIL': '0x293 发送 A 成功 / 失败',
    '0x293 TX B OK / FAIL': '0x293 发送 B 成功 / 失败',
    'Independent from Confirm-Free 0x3F8 target · same-bus stock template only':
        '与免确认 0x3F8 目标相互独立 · 仅用同总线原厂模板',
    'Requests / completed / blocked': '请求 / 完成 / 拦截',
    'Gate-blocked A / B': '门控拦截 A / B',
    'Fast attempts / OK / FAIL': '快速尝试 / 成功 / 失败',
    'MUX1 RX / TX OK / FAIL': 'MUX1 接收 / 发送 成功 / 失败',

    # ---- CAN 研究抓包面板
    'BODY + CHASSIS + PARTY research recorder with automatic multi-segment re-arm.':
        'BODY + CHASSIS + PARTY 三路研究录制器，支持自动多段续录。',
    'SNAPSHOT: latest state sets · RAW: actual BODY + CHASSIS + PARTY RX frames. Recorder never transmits CAN.':
        '快照：最新状态集合 · 原始：真实的 BODY + CHASSIS + PARTY 接收帧。录制器从不发送 CAN。',
    'CAPTURE STATE': '录制状态',
    'CAPTURE MODE': '录制模式',
    'Snapshot plan': '快照计划',
    'PRE WINDOW': '前置窗口',
    'POST WINDOW': '后置窗口',
    'PRE BUFFER': '前置缓冲',
    'REMAINING POST': '剩余后置',
    'RAW PRE ring / archive': '原始前置 环形 / 归档',
    'RAW PRE actual coverage': '原始前置 实际覆盖',
    'RAW TRANSITION': '原始切换',
    'PRE ready / slots': '前置就绪 / 槽位',
    'SAMPLES / CAPACITY': '样本 / 容量',
    'SEGMENTS / MAX': '分段 / 上限',
    'Pre 2 s · trigger · POST 5 s': '前置 2 秒 · 触发 · 后置 5 秒',
    'PRE 2 s · trigger · POST 5 s': '前置 2 秒 · 触发 · 后置 5 秒',
    'PRE 0 · trigger 0 rows · POST 0 / 4': '前置 0 · 触发 0 行 · 后置 0 / 4',
    'OBSERVED IDs': '观测到的 ID',
    'Last segment snapshots': '上次分段快照',
    'CURRENT / LAST': '当前 / 上次',
    'Download Research CSV': '下载研究数据 CSV',
    'Reset CAN Research Capture': '重置 CAN 研究抓包',
    'AUTO last transition': '自动 上次切换',
    'AUTO qualified / segments / merged': '自动 合格 / 分段 / 合并',
    'AUTO LEFT OPEN / BLOCKED': '自动左窗 开 / 拦截',
    'Quiet arm / fire / guard': '静默 待命 / 触发 / 保护',
    'Periodic': '周期',
    'Periodic OK / FAIL': '周期 成功 / 失败',
    'STATE': '状态',
    'SNAPSHOT': '快照',
    'Memory': '内存',
    'Storage': '存储',
    'Transport': '传输',

    # ---- 驾驶员监测抓包面板
    'Driver Monitoring bit43': '驾驶员监测 bit43',
    'Download Driver Monitoring CSV': '下载驾驶员监测 CSV',
    'Reset Driver Monitoring Capture': '重置驾驶员监测抓包',
    'DRIVER INTERACTION': '驾驶员交互',
    'FRONT · NORMAL': '前 · 正常',
    'FRONT · NO TORQUE': '前 · 无扭矩',
    'TORQUE + LOOK AWAY': '扭矩 + 分心',
    'SCREEN GLANCE': '看屏幕',
    'SIDE LOOK': '侧视',
    'LOOK DOWN': '低头',
    'Last interaction transition': '上次交互切换',

    # ---- 驾驶员车窗测试面板
    'Driver Window Test': '驾驶员车窗测试',
    'Model YL only · PARK required · clones fresh CAN B 0x3C2 MUX0 and sets byte 6 bits [3:2] to Auto Down value 2.':
        '仅 Model YL · 需挂 P 挡 · 克隆最新的 CAN B 0x3C2 MUX0，并把 byte6 的 bit[3:2] 设为 Auto Down 值 2。',
    'Test window opening in Park.': '在 P 挡测试车窗开启。',
    'OPEN DRIVER WINDOW · AUTO DOWN': '打开驾驶员车窗 · 自动下降',
    'Fixed R79 Policy': '固定 R79 策略',
    'Bit 18 policy': 'Bit 18 策略',
    'Mode 1 / Mode 2 · bit19=0 · bit47 follows HW3 policy · manual D/R suppression':
        '模式 1 / 2 · bit19=0 · bit47 跟随 HW3 策略 · 手动挡 D/R 抑制',
    'Transport and scheduler are fixed in v3.7. Bit 18 is configured from Settings.':
        '传输与调度在 v3.7 已固定。Bit 18 在「设置」中配置。',
    'LABEL A': '标签 A',
    'LABEL B': '标签 B',
    'LABEL C': '标签 C',
    'LABEL D': '标签 D',
    'Save Labels': '保存标签',

    # ---- 各面板通用状态行
    'READY': '就绪',
    'ACTIVE': '激活',
    'AVAILABILITY': '可用性',
    'ACTION STATE': '动作状态',
    'TEST': '测试',
    'Capture': '抓包',
    'Captured data': '已抓数据',
    'Runtime / template': '运行 / 模板',
    'Requests / ignored / dropped': '请求 / 忽略 / 丢弃',
    'TX OK / FAIL': '发送 成功 / 失败',
    'BOTH': '双路',
    'CAN A stock / age / RX': 'CAN A 原厂 / 时效 / 接收',
    'CAN B stock / age / RX': 'CAN B 原厂 / 时效 / 接收',
    'STOCK A / B': '原厂 A / B',
    'Last TX raw': '上次发送原始值',
    'Last forced TX': '上次强制发送',
    'Stock 0x3C2 age': '原厂 0x3C2 时效',
    'OFF · 0': '关 · 0',
    'WARMUP': '预热',
    'Read-only production status for the selected R79 transmitter.': '所选 R79 发送器的只读正式状态。',

    # ---- 更多功能页：开源地址
    'Open source:': '开源项目地址：',
}

# 帧号 + 描述的组合串，逐条保留前缀、翻译后半段
FRAME_LABELS = {
    '0x239 View Range': '0x239 可视距离',
    '0x239 Virtual Lane Width': '0x239 虚拟车道宽度',
    '0x239 age —': '0x239 时效 —',
    '0x247 raw': '0x247 原始值',
    '0x247 · bus / age / count': '0x247 · 总线 / 时效 / 计数',
    '0x370 raw': '0x370 原始值',
    '0x370 · bus · EPAS hands-on / torque / age / count': '0x370 · 总线 · EPAS 握持 / 扭矩 / 时效 / 计数',
    '0x389 raw': '0x389 原始值',
    '0x389 · bus / age / count': '0x389 · 总线 / 时效 / 计数',
    '0x399 raw': '0x399 原始值',
    '0x399 · bus · DAS hands-on / age / count': '0x399 · 总线 · DAS 握持 / 时效 / 计数',
    '0x5D9 raw': '0x5D9 原始值',
    '0x5D9 · bus / age / count': '0x5D9 · 总线 / 时效 / 计数',
}
ZH_EXTRA.update(FRAME_LABELS)


def inject_dyn(block):
    """把运行时状态兜底脚本放进 P4CAN-ZH 块（幂等）。"""
    if DYN_START in block:
        return re.sub(re.escape(DYN_START) + r'.*?' + re.escape(DYN_END),
                      lambda _m: DYN_JS, block, flags=re.S), False
    return block.rstrip('\n') + '\n' + DYN_JS + '\n', True


def main():
    html = DASH.read_text(encoding='utf-8')
    i, j = html.find(START), html.find(END)
    if i < 0 or j < 0:
        raise SystemExit('找不到 P4CAN-ZH 块，先确认页面还是中文语言版')
    block = html[i:j]

    m = re.search(r'var DICT=(\{.*?\});\s*\n', block, re.S)
    if not m:
        raise SystemExit('P4CAN-ZH 块里找不到 var DICT={...};')
    old = json.loads(m.group(1))

    added, skipped = [], []
    merged = dict(old)
    for en, zh in ZH_EXTRA.items():
        if en in merged:
            if merged[en] != zh:
                skipped.append((en, merged[en], zh))
            continue
        merged[en] = zh
        added.append(en)

    block2 = block
    if added:
        payload = json.dumps(merged, ensure_ascii=False, separators=(',', ': '))
        block2 = (block[:m.start()] + 'var DICT=' + payload + ';\n' + block[m.end():])

    block2, dyn_new = inject_dyn(block2)

    if block2 == block:
        print('中文包已是最新：%d 条词条，动态兜底已就位' % len(merged))
        if skipped:
            print('注意：%d 条已存在且译法不同（保留原译）' % len(skipped))
            for en, keep, want in skipped[:8]:
                print('  %-50s 保留 %r / 建议 %r' % (en[:50], keep, want))
        return

    DASH.write_text(html[:i] + block2 + html[j:], encoding='utf-8')

    print('中文词条  %d -> %d（新增 %d）' % (len(old), len(merged), len(added)))
    if dyn_new:
        print('注入运行时状态兜底：%d 个节点' % 5)
    if skipped:
        print('已存在但译法不同，保留原译：%d 条' % len(skipped))
        for en, keep, want in skipped[:8]:
            print('  %-50s 保留 %r' % (en[:50], keep))


if __name__ == '__main__':
    main()
