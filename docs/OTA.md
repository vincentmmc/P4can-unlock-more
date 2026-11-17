# 固件更新（OTA）

上游固件本来就带一条可用的 OTA 通道，缺的只是前端。这一版把前端补齐，
并把打包流程固化成一条 7 步脚本，避免手工拼包出错。脚本与源码不随仓库发布，
流程本身记录在下面第 4 节，便于你核对手里这个包是怎么来的。

## 1. 两种包

| 包 | 大小 | 写入方式 | 用途 |
|---|---|---|---|
| `*-ota.bin` | 约 1.4 MB | 网页上传（`POST /update`） | 日常更新 |
| `*-full.bin` | 32 MB | USB + esptool（`0x0`） | 首次烧录、救砖、换分区表 |

OTA 只能写 **app 分区**。bootloader、分区表、flash 参数改动必须走完整包线刷。

## 2. 分区与上限

`large_fat_32MB.csv` → `app5M_fat24M_32MB`：

| 分区 | 偏移 | 大小 |
|---|---|---|
| `ota_0`（app0） | `0x10000` | `0x480000` = 4,718,592 B |
| `ota_1`（app1） | `0x490000` | `0x480000` = 4,718,592 B |
| `otadata` | 两分区之后 | 2 × 4 KB |

当前镜像约 1.43 MB，占分区 **30%**，余量充足 —— 页面继续加功能也不会顶到上限。

`otadata` 记录当前从哪个分区启动，新镜像写进另一个分区并校验通过后才切换；
校验失败时引导器自动回落到旧分区，所以 OTA 失败一般是**变回旧版本**而不是变砖。

## 3. 刷写流程

1. 手机或电脑连 P4 热点（默认 `192.168.4.1`）
2. **设置 → 固件更新**
3. 选 `*-ota.bin`（拖拽也行）
4. 面板会先做本地预检：大小不超上限、扩展名是 `.bin`、文件非空
5. 点一下进入待确认，再点一下才开始写 —— 防误触
6. 进度条走完自动重启，版本号在页面顶部

失败时面板显示 `Update.errorString()` 的中文释义，常见：

| 错误 | 含义 |
|---|---|
| `No ERROR` | 未开始或已完成 |
| `Not Enough Space` | 镜像超过目标分区 |
| `Magic Bytes Mismatch` | 不是 ESP32 应用镜像（多半传了整片包） |
| `Image MD5 Mismatch` | 传输中断或文件损坏，重传 |

## 4. 出包流程（内部记录）

出包走一条固定脚本（不随仓库发布），按顺序做下面 7 步，任一步不合规直接中止：

| 步骤 | 动作 | 失败后果 |
|---|---|---|
| 1 | `gen_feifan.py` → `integrate_feifan.py` → `patch_ota.py` → `build_dashboard.py` | 页面注入失败，中止 |
| 2 | 源码同步到 `build/P4can-unlock-more/`，改写 `FW_VERSION` 为 `v3.29.3-<tag>` | 改不动版本号，中止 |
| 3 | `arduino-cli compile` | 编译错误，中止 |
| 4 | 取 `.ino.bin`，校验大小与 `0xE9` | 超分区 / 非应用镜像，中止 |
| 5 | 取 `.merged.bin`，校验 32 MB 与三个关键偏移 | 整片布局不对，中止 |
| 6 | **逐字节比对**镜像内嵌 gzip 与 `dashboard_source.html` | 页面没进镜像，中止 |
| 7 | 写 `dist/manifest.json` | — |

第 6 步是这套流程里最值钱的一步：`index_html.h` 是生成物，很容易出现
「改了 `dashboard_source.html` 但忘了重新 gzip」的情况，那样刷进去的还是旧页面，
而且从版本号上看不出来。逐字节比对能直接拦住。

## 5. 验收清单

刷完在设备上确认：

- [ ] 顶部版本号是 `v3.29.3-<tag>`，与 `manifest.json` 的 `fw_version` 一致
- [ ] 底部导航有「更多功能」，8 组都在
- [ ] 中英切换后，散文全部跟随，帧 ID / 位域保持原样
- [ ] 设置 → 固件更新 面板显示分区余量与当前版本
- [ ] 选一个 `.txt` 会被拒；选 32 MB 完整包会被 `Magic Bytes Mismatch` 拒
- [ ] 故意断网中断一次上传，重启后仍是旧版本（回滚生效）

## 6. 离线校验

```bash
# 镜像头与段表
esptool.py --chip esp32p4 image_info P4can-unlock-more-v3.29.3-more1117-ota.bin

# 整片布局
python - <<'PY'
b = open('P4can-unlock-more-v3.29.3-more1117-full.bin','rb').read()
print(len(b), b[0x2000], b[0x8000:0x8002], b[0x10000])
# 期望：33554432 233 b'\xaaP' 233
PY

# 哈希
sha256sum P4can-unlock-more-v3.29.3-more1117-*.bin
```

`image_info` 应显示 `Checksum: valid`、`Validation Hash: valid`，段数 8 段左右。

## 7. 已知限制

- OTA 期间不要断电，虽然会回滚，但连续两次失败会停在 bootloader 等线刷
- 浏览器上传走 multipart，慢速链路（WiFi 信号差）建议用电脑
- 固件更新面板只在 `设置` 页保留一份，「更多功能」页里刻意没有入口，
  避免两个地方各刷一半
