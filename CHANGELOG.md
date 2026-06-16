# 更新日誌

此專案的所有重要變更都將記錄在此檔案中。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
版本號遵循 [語意化版本](https://semver.org/lang/zh-TW/)。

## [未發布]

## [0.2.0] - 2026-06-16

### 新增

- `AlarmInfo` dataclass，對應 M3 韌體 `NOTICE_ALARM_FRAME` 結構，包含 LTC4015 高溫、電池高溫及系統重啟/停止/12V 停用等警報欄位
- `M3Controller.get_alarm_status()` 方法，發送 `CMD_QUERY_ALARM`（`0x46`）並解析回應

## [0.1.0] - 2026-06-16

### 新增

- `rs485_manager.py`：RS485 通訊基礎層
  - `compute_crc16()`：CRC-16 Modbus 計算
  - `build_rs485_packet()`：封包組建
  - `RS485LockManager`：以 `fcntl.flock` 對 UART 設備上排他鎖，支援多程序互斥
  - `RS485Manager.send_command()`：統一的發送／接收介面
- `battery_structures.py`：資料結構定義
  - `BatteryType`、`BatteryStatus` 列舉
  - `BspBsmPlbModbus`：BMS Modbus 完整資料結構
  - `ApsStatus`：APS 狀態列舉
  - `Bsp4015Info`：LTC4015 充電 IC 狀態結構
- `m3_controller.py`：M3 控制器操作介面
  - `M3Controller.get_4015_status()`：查詢充電 IC 電壓、電流、溫度與 APS 狀態
  - `M3Controller.get_batteries_info()`：查詢電池 A／B 完整 BMS 資料
  - `M3Controller.get_firmware_version()`：查詢 M3 韌體版本

[未發布]: https://github.com/example/battery-box-sample-code/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/example/battery-box-sample-code/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/example/battery-box-sample-code/releases/tag/v0.1.0
