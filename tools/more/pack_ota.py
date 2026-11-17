#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P4-CAN 固件 OTA 打包器
=====================

一条命令产出「网页上传即可刷入」的 .bin：

    python pack_ota.py                  # 全流程：重建页面 -> 编译 -> 出包 -> 校验
    python pack_ota.py --tag ff2        # 自定义标签，版本号变 v3.29.3-ff2
    python pack_ota.py --no-html        # 页面没改，跳过页面重建（省一次 gzip）
    python pack_ota.py --dry-run        # 只检查环境与配置文件，不编译

产物目录 ../ota/：
    P4can-unlock-more-v3.29.3-<tag>-ota.bin    可 OTA 上传的应用镜像
    P4can-unlock-more-v3.29.3-<tag>-full.bin   32 MB 整片线刷镜像
    manifest.json                       版本/大小/sha256/页面指纹，供核对

关键约束（写死，出错即中止）：
    * 只接受 .ino.bin（应用镜像），绝不把 merged/bootloader/partitions 当 OTA 包
    * 大小必须 <= 4,718,592 B（ota_0/ota_1 各 0x480000）
    * 首字节必须是 0xE9（ESP32 应用镜像 magic）
    * 内嵌的 gzip 页面解压后必须与 dashboard_source.html 逐字节一致
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent            # tools/more
REPO = HERE.parents[1]                            # 仓库根
SRC = REPO / "firmware" / "P4can-unlock-more"     # sketch 源码
SKETCH_NAME = "P4can-unlock-more"
BUILD = REPO / "build"
SKETCH = BUILD / SKETCH_NAME                      # 同步后的编译副本
OUTDIR = BUILD / "cli"                            # arduino-cli 输出
OTADIR = REPO / "dist"                            # 发布产物


def _find_acli():
    """arduino-cli 位置：环境变量 > PATH > tools/ 目录。"""
    env = os.environ.get("ARDUINO_CLI")
    if env and Path(env).exists():
        return Path(env)
    found = shutil.which("arduino-cli")
    if found:
        return Path(found)
    for name in ("arduino-cli.exe", "arduino-cli"):
        p = REPO / "tools" / name
        if p.exists():
            return p
    return REPO / "tools" / "arduino-cli.exe"


ACLI = _find_acli()

FQBN = ("esp32:esp32:esp32p4:ChipVariant=postv3,FlashSize=32M,"
        "PartitionScheme=app5M_fat24M_32MB,PSRAM=enabled,"
        "USBMode=hwcdc,CDCOnBoot=cdc,FlashMode=qio")
APP_PART_BYTES = 0x480000                          # 4,718,592
MAX_IMAGE = APP_PART_BYTES
FLASH_BYTES = 0x2000000                            # 32 MB，整片镜像大小

BASE_VERSION = "v3.29.3"

# 需要同步进 sketch 的源码文件类型
COPY_PATTERNS = ("*.h", "*.ino", "*.cpp", "*.c", "*.md", "*.json")


def say(msg=""):
    print(msg, flush=True)


def die(msg, code=1):
    print("\n[FAIL] " + msg, file=sys.stderr, flush=True)
    sys.exit(code)


def sha256_of(path, limit=None):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
            if limit and f.tell() > limit:
                break
    return h.hexdigest()


def run(cmd, cwd=None, capture=True, tail=30):
    p = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        if capture and p.stdout:
            lines = p.stdout.strip().splitlines()
            print("\n".join(lines[-tail:]), file=sys.stderr, flush=True)
        die("命令失败 (exit %d): %s" % (p.returncode, cmd))
    return (p.stdout or "") if capture else ""


# ---------------------------------------------------------------- 1. 页面重建
def rebuild_html():
    say("[1/7] 重建页面并注入 index_html.h")
    for name in ("gen_feifan.py", "integrate_feifan.py", "patch_ota.py"):
        script = HERE / name
        if not script.exists():
            say("      skip %s (不存在)" % name)
            continue
        run([sys.executable, str(script)], cwd=HERE)
        say("      ok   %s" % name)
    bd = SRC / "tools" / "build_dashboard.py"
    if not bd.exists():
        die("找不到 %s" % bd)
    run([sys.executable, str(bd)], cwd=SRC)
    h = SRC / "index_html.h"
    say("      index_html.h  %s B" % f"{h.stat().st_size:,}")


def _norm_ver(text):
    """把 FW_VERSION 那一行抹掉，用于比较「除版本号外内容是否相同」。"""
    return re.sub(r'#define\s+FW_VERSION\s+"[^"]*"', '#define FW_VERSION "?"', text)


def _same(a, b):
    if a.stat().st_size == b.stat().st_size and sha256_of(a) == sha256_of(b):
        return True
    if a.suffix == ".ino":
        return (_norm_ver(a.read_text(encoding="utf-8", errors="replace"))
                == _norm_ver(b.read_text(encoding="utf-8", errors="replace")))
    return False


# ------------------------------------------------------------ 2. 同步到 sketch
def sync_sketch(tag):
    say("[2/7] 同步源码到 sketch 目录 %s" % SKETCH.name)
    SKETCH.mkdir(parents=True, exist_ok=True)

    copied = 0
    for pat in COPY_PATTERNS:
        for f in SRC.glob(pat):
            dst = SKETCH / f.name
            # 内容比较而不是 mtime：改一个字符也可能不改时间戳
            if (not dst.exists()) or not _same(dst, f):
                shutil.copy2(f, dst)
                copied += 1
    for sub in ("assets", "fonts"):
        s = SRC / sub
        if s.is_dir():
            d = SKETCH / sub
            if d.exists():
                shutil.rmtree(d)
            shutil.copytree(s, d)
            copied += 1
    say("      同步 %d 项，源 index_html.h %s B"
        % (copied, f"{(SKETCH / 'index_html.h').stat().st_size:,}"))

    # 版本号打标，便于在页面上确认刷的是自己的包
    ino = SKETCH / (SKETCH_NAME + ".ino")
    text = ino.read_text(encoding="utf-8", errors="replace")
    newver = "%s-%s" % (BASE_VERSION, tag)
    text2 = re.sub(r'#define\s+FW_VERSION\s+"[^"]*"',
                   '#define FW_VERSION "%s"' % newver, text, count=1)
    if text2 == text and ('"%s"' % newver) not in text:
        die("无法改写 FW_VERSION，请检查 ino 第 70 行")
    if text2 != text:
        ino.write_text(text2, encoding="utf-8")
    say("      FW_VERSION -> %s" % newver)
    return newver


# ---------------------------------------------------------------- 3. 编译
def compile_fw():
    say("[3/7] 编译（首次约 3-5 分钟，增量约 1-2 分钟）")
    t0 = dt.datetime.now()
    out = run([str(ACLI), "compile", "-b", FQBN,
               "--build-path", str(OUTDIR), str(SKETCH)])
    secs = (dt.datetime.now() - t0).total_seconds()
    for line in out.splitlines():
        if "Sketch uses" in line or "Global variables" in line:
            say("      " + line.strip())
    say("      耗时 %.0f 秒" % secs)
    return secs


# ---------------------------------------------------------------- 4. 取包
def collect_bin(tag, version):
    say("[4/7] 提取可 OTA 的应用镜像")
    cand = OUTDIR / (SKETCH_NAME + ".ino.bin")
    if not cand.exists():
        die("找不到应用镜像 %s" % cand)

    blob = cand.read_bytes()
    n = len(blob)

    if n > MAX_IMAGE:
        die("镜像 %s B 超过分区上限 %s B，无法 OTA" % (f"{n:,}", f"{MAX_IMAGE:,}"))
    if blob[0] != 0xE9:
        die("首字节 0x%02X 不是 ESP32 应用镜像 magic 0xE9" % blob[0])

    OTADIR.mkdir(parents=True, exist_ok=True)
    name = "P4can-unlock-more-v%s-%s-ota.bin" % (BASE_VERSION.lstrip("v"), tag)
    dst = OTADIR / name
    shutil.copyfile(cand, dst)
    say("      %s  %s B  (%.0f%% of %s)"
        % (name, f"{n:,}", n * 100.0 / MAX_IMAGE, f"{MAX_IMAGE:,}"))
    return dst, blob


def collect_full(tag):
    """整片镜像：bootloader + 分区表 + 应用，只能线刷，用于首次烧录或救砖。"""
    say("[5/7] 提取整片镜像（线刷用）")
    cand = OUTDIR / (SKETCH_NAME + ".ino.merged.bin")
    if not cand.exists():
        say("      skip：没生成 merged.bin")
        return None, None
    blob = cand.read_bytes()
    n = len(blob)
    if n != FLASH_BYTES:
        die("merged.bin 大小 %s B，应为 %s B（32MB 整片）" % (f"{n:,}", f"{FLASH_BYTES:,}"))
    # ESP32-P4 的整片布局：0x2000 bootloader、0x8000 分区表、0x10000 app（0x0 是空白）
    if blob[0x2000] != 0xE9:
        die("0x2000 处不是 bootloader（magic 0x%02X）" % blob[0x2000])
    if blob[0x8000:0x8002] != b"\xAA\x50":
        die("0x8000 处不是分区表（magic %s），merged 镜像有问题" % blob[0x8000:0x8002].hex())
    if blob[0x10000] != 0xE9:
        die("0x10000 处不是应用镜像（magic 0x%02X）" % blob[0x10000])
    name = "P4can-unlock-more-v%s-%s-full.bin" % (BASE_VERSION.lstrip("v"), tag)
    dst = OTADIR / name
    shutil.copyfile(cand, dst)
    say("      %s  %s B  (32 MB 整片，含 bootloader + 分区表)"
        % (name, f"{n:,}"))
    return dst, blob


# ------------------------------------------------------- 5. 页面指纹一致性
def verify_embedded_html(blob, dst):
    say("[6/7] 校验镜像内嵌页面与源码一致")
    src = (SRC / "dashboard_source.html").read_bytes()
    found = None
    for m in re.finditer(b"\x1f\x8b\x08", blob):
        off = m.start()
        try:
            d = zlib.decompressobj(16 + zlib.MAX_WBITS)
            out = d.decompress(blob[off:off + 900000], 2_000_000)
        except Exception:
            continue
        if len(out) > 100_000:
            found = out
            break
    if found is None:
        die("镜像里找不到内嵌页面（gzip 流）")
    if found != src:
        die("镜像内嵌页面与 dashboard_source.html 不一致！\n"
            "      源码 %s B / 镜像 %s B\n"
            "      多半是同步漏了 index_html.h，重跑本脚本。" % (len(src), len(found)))
    say("      逐字节一致  %s B  sha256 %s…"
        % (f"{len(src):,}", hashlib.sha256(src).hexdigest()[:16]))
    return hashlib.sha256(src).hexdigest()


# ----------------------------------------------------------- 6.清单与摘要
def write_manifest(dst, blob, full_dst, full_blob, version, tag, secs, html_sha):
    say("[7/7] 写清单")
    man = {
        "product": "P4can-unlock-more",
        "base_version": BASE_VERSION,
        "fw_version": version,
        "tag": tag,
        "ota": {
            "file": dst.name,
            "size": len(blob),
            "size_human": "%.2f MB" % (len(blob) / 1048576.0),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "app_partition_bytes": APP_PART_BYTES,
            "headroom_bytes": APP_PART_BYTES - len(blob),
            "upload_endpoint": "POST /update",
            "status_endpoint": "GET /api/ota/status",
            "how": "连 P4 热点 -> 设置 -> 固件更新 -> 选此文件 -> 点两下确认",
        },
        "full": {
            "file": full_dst.name if full_dst else None,
            "size": len(full_blob) if full_blob else 0,
            "sha256": hashlib.sha256(full_blob).hexdigest() if full_blob else None,
            "how": "USB 线刷：esptool write_flash 0x0 <full.bin>，只能在电脑上做",
        },
        "html_sha256": html_sha,
        "html_bytes": (SRC / "dashboard_source.html").stat().st_size,
        "built_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "build_seconds": int(secs),
        "fqbn": FQBN,
        "partition_scheme": "app5M_fat24M_32MB",
        "note": "OTA 只能写 app 分区；bootloader/分区表变了必须用 full 线刷",
    }
    (OTADIR / "manifest.json").write_text(
        json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")

    say("")
    say("=" * 66)
    say("  两种包都已就绪")
    say("=" * 66)
    say("  [升级包]  网页上传即可刷")
    say("    文件    %s" % dst.name)
    say("    大小    %s B  (%.2f MB)   余量 %s B"
        % (f"{len(blob):,}", len(blob) / 1048576.0, f"{APP_PART_BYTES - len(blob):,}"))
    say("    sha256  %s" % hashlib.sha256(blob).hexdigest())
    if full_dst:
        say("  [完整包]  线刷，救砖/首次烧录用")
        say("    文件    %s" % full_dst.name)
        say("    大小    %s B  (32 MB 整片)" % f"{len(full_blob):,}")
        say("    sha256  %s" % hashlib.sha256(full_blob).hexdigest())
    say("  版本      %s" % version)
    say("  清单      %s" % (OTADIR / "manifest.json").name)
    say("")
    say("  升级：手机连 P4 热点 -> 设置 -> 固件更新 -> 选升级包 -> 点两下")
    say("=" * 66)
    return man


def preflight():
    say("[0/7] 环境检查")
    if not ACLI.exists():
        die("缺少 %s，先运行 tools 里的下载步骤" % ACLI)
    if not SRC.is_dir():
        die("找不到源码目录 %s" % SRC)
    core = run([str(ACLI), "core", "list"])
    if "esp32:esp32" not in core:
        die("未安装 esp32 core")
    line = [l for l in core.splitlines() if "esp32:esp32" in l]
    say("      arduino-cli  ok    %s" % (line[0].split()[1] if line else ""))
    say("      源码         %s" % SRC.name)
    say("      FQBN         app5M_fat24M_32MB / 32M / PSRAM / hwcdc")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="more" + dt.date.today().strftime("%m%d"))
    ap.add_argument("--no-html", action="store_true", help="跳过页面重建")
    ap.add_argument("--dry-run", action="store_true", help="只检查环境")
    a = ap.parse_args()

    tag = re.sub(r"[^A-Za-z0-9._-]", "", a.tag) or "ff"
    preflight()
    if a.dry_run:
        say("\n[dry-run] 环境就绪，未编译。")
        return

    if a.no_html:
        say("[1/7] 跳过页面重建")
    else:
        rebuild_html()

    version = sync_sketch(tag)
    secs = compile_fw()
    dst, blob = collect_bin(tag, version)
    full_dst, full_blob = collect_full(tag)
    html_sha = verify_embedded_html(blob, dst)
    write_manifest(dst, blob, full_dst, full_blob, version, tag, secs, html_sha)


if __name__ == "__main__":
    main()
