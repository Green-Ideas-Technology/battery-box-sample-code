from dataclasses import dataclass
from enum import IntEnum
from typing import List


class BatteryType(IntEnum):
    BATTERY_A = 0
    BATTERY_B = 1


class BatteryStatus(IntEnum):
    READY = 0
    POLLING = 1
    NO_RESPONSE = 2


@dataclass
class BspBsmPlbModbus:
    """對應原始 C 中的 BspBsmPlbModbus 結構"""

    battery_id: int = 0  # 電池 ID
    bms_polling_status: int = 0  # BMS 輪詢狀態
    bat_cell_voltage: List[int] = None  # 32 個 Cell 電壓
    max_battery_voltage: int = 0  # 最大電池電壓
    min_battery_voltage: int = 0  # 最小電池電壓
    pack_voltage: int = 0  # PACK 電壓
    bat_total_voltage: int = 0  # 總電壓

    charging_current_low: int = 0  # 充電電流低位元
    discharging_current_low: int = 0  # 放電電流低位元
    battery_capacity_lookup: int = 0  # 電池容量查表
    soc: int = 0  # SOC

    soh: int = 0  # SOH
    device_check_code: int = 0  # 裝置確認碼

    plc_overall_status: int = 0  # 綜合狀態 (PLC使用)
    plc_overall_status2: int = 0  # 綜合狀態 2

    charge_coulomb_calc_high: int = 0  # 充電庫倫計算高位
    charge_coulomb_calc_low: int = 0  # 充電庫倫計算低位
    discharge_coulomb_calc_high: int = 0  # 放電庫倫計算高位
    discharge_coulomb_calc_low: int = 0  # 放電庫倫計算低位

    charging_current_high: int = 0  # 充電電流高位元
    discharging_current_high: int = 0  # 放電電流高位元

    nc: List[int] = None  # 保留欄位
    temperature: List[int] = None  # 溫度1~5

    charging_count: int = 0  # 充放電次數

    ov_alert_low: int = 0  # 過壓警告低位
    ov_alert_high: int = 0  # 過壓警告高位
    ov_protect_low: int = 0  # 過壓保護低位
    ov_protect_high: int = 0  # 過壓保護高位

    uv_alert_low: int = 0  # 欠壓警告低位
    uv_alert_high: int = 0  # 欠壓警告高位
    uv_protect_low: int = 0  # 欠壓保護低位
    uv_protect_high: int = 0  # 欠壓保護高位

    cell_balance_status_low: int = 0  # 各 cell 平衡狀態低位
    cell_balance_status_high: int = 0  # 各 cell 平衡狀態高位

    voltage_current_status: int = 0  # 電壓及電流偵測狀態
    t1_t2_status: int = 0  # T1 & T2 偵測狀態
    t3_t4_status: int = 0  # T3 & T4 偵測狀態
    t5_temperature_status: int = 0  # T5 溫度或溫度線狀態
    overall_status: int = 0  # 綜合狀態

    battery_capacity_coulomb_high: int = 0  # 電池容量高位
    battery_capacity_coulomb_low: int = 0  # 電池容量低位

    def __post_init__(self):
        if self.bat_cell_voltage is None:
            self.bat_cell_voltage = [0] * 32
        if self.nc is None:
            self.nc = [0] * 7
        if self.temperature is None:
            self.temperature = [0] * 5


class ApsStatus(IntEnum):
    NORMAL_OUTPUT = 0x0000
    CHARGING = 0x0001
    READY = 0x0008
    SUSPEND = 0x0020
    NO_BATTERY = 0x0010


@dataclass
class AlarmInfo:
    """對應原始 C 中的 NOTICE_ALARM_FRAME 警報狀態結構"""

    # 維護旗標
    need_maintenance: bool = False  # 是否需要維護

    # LTC4015 警報 (A0)
    ltc4015_temp_95: bool = False   # bit0: 溫度超過 95°C
    ltc4015_temp_105: bool = False  # bit1: 溫度超過 105°C
    ltc4015_error: bool = False     # bit7: LTC4015 錯誤

    # 電池警報 (A1)
    bata_temp_65: bool = False  # bit0: BatA 溫度超過 65°C
    bata_temp_75: bool = False  # bit1: BatA 溫度超過 75°C
    batb_temp_65: bool = False  # bit4: BatB 溫度超過 65°C
    batb_temp_75: bool = False  # bit5: BatB 溫度超過 75°C

    # 系統資訊 (A2)
    system_reboot_ltc4015: bool = False       # bit0: 系統重啟; LTC4015 錯誤 (after 30sec)
    system_reboot_uart: bool = False          # bit1: 系統重啟; UART 命令 (after 30sec)
    system_stop_ltc4015_temp: bool = False    # bit2: 系統停止; LTC4015 溫度過高 (after 30sec)
    system_stop_bata_temp: bool = False       # bit3: 系統停止; 電池_A 溫度過高 (after 30sec)
    system_stop_batb_temp: bool = False       # bit4: 系統停止; 電池_B 溫度過高 (after 30sec)
    output_12v_disable_uart: bool = False     # bit5: 12V 輸出停用; UART 命令 (after Xsec)
    output_12v_disable_battery: bool = False  # bit6: 12V 輸出停用; 電池電量不足 (after 60sec)

    # 原始位元組
    raw_ltc4015: int = 0  # A0 原始值
    raw_battery: int = 0  # A1 原始值
    raw_system: int = 0   # A2 原始值


@dataclass
class Bsp4015Info:
    """對應原始 C 中的 Bsp4015Info 結構"""

    battery_a_voltage: int = 0  # A電池電壓
    battery_a_current: int = 0  # A電池電流
    battery_b_voltage: int = 0  # B電池電壓
    battery_b_current: int = 0  # B電池電流
    charging_voltage: int = 0  # 充電電壓
    charging_current: int = 0  # 充電電流

    die_temperature: int = 0  # 硬體溫度
    aps_status: int = 0  # APS狀態
    act: int = 0  # 使用電池
    battery_slot_status: int = 0  # 電池插槽狀態
    output_enable: int = 0  # 12V 輸出狀態

