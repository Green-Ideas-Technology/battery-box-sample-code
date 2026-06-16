# Battery Box Sample Code

電池盒（Battery Box）M3 控制器通訊協議的範例程式碼，示範如何在上位平台上透過 RS485 串列介面實作查詢指令與解析回應封包。

## 封包格式

```
| CC | LEN_L | LEN_H | CMD | CRC_L | CRC_H | DATA... |
```

| 欄位 | 大小 | 說明 |
|------|------|------|
| `CC` | 1 byte | 起始碼，固定 `0xCC` |
| `LEN` | 2 bytes | DATA 長度（little-endian uint16）|
| `CMD` | 1 byte | 命令碼 |
| `CRC` | 2 bytes | CRC-16 Modbus，計算範圍為 DATA 欄位（little-endian）|
| `DATA` | N bytes | 命令資料 |

回應命令碼規則：`response_cmd = request_cmd | 0x80`

## 支援命令

| 命令 | 請求 CMD | 回應 CMD | 說明 |
|------|----------|----------|------|
| 查詢 LTC4015 充電 IC 狀態 | `0x40` | `0x80` | 電壓、電流、溫度、APS 狀態 |
| 查詢電池 BMS 資訊 | `0x44` | `0x84` | SOC、SOH、Cell 電壓、溫度等完整 BMS 資料 |
| 查詢警報狀態 | `0x46` | `0x86` | LTC4015 高溫、電池高溫、系統重啟/停止條件 |
| 查詢韌體版本 | `0x70` | `0xF0` | M3 控制器韌體版本字串 |

## 使用方式

```python
import logging
from rs485_manager import RS485Manager
from m3_controller import M3Controller, M3ControllerError
from battery_structures import BatteryType

logger = logging.getLogger(__name__)

rs485 = RS485Manager(device_path="/dev/ttyS0", baud_rate=115200, logger=logger)
m3 = M3Controller(rs485_manager=rs485, logger=logger)

# 查詢 LTC4015 狀態
err, status = m3.get_4015_status()
if err == M3ControllerError.OK:
    print(f"電池A電壓: {status.battery_a_voltage / 1000}V")

# 查詢電池 BMS 資訊
err, bms = m3.get_batteries_info(BatteryType.BATTERY_A)
if err == M3ControllerError.OK:
    print(f"SOC: {bms.soc}%")

# 查詢警報狀態
err, alarm = m3.get_alarm_status()
if err == M3ControllerError.OK and alarm.need_maintenance:
    print("系統需要維護")

# 查詢韌體版本
err, version = m3.get_firmware_version()
if err == M3ControllerError.OK:
    print(f"韌體版本: {version}")
```

## 依賴套件

```
pyserial
```

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `rs485_manager.py` | RS485 通訊基礎層（封包組建、CRC、串口鎖管理）|
| `battery_structures.py` | 資料結構定義（對應 M3 韌體的 C 結構體）|
| `m3_controller.py` | M3 控制器操作介面 |

## 更新紀錄

詳見 [CHANGELOG.md](CHANGELOG.md)。
