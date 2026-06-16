import logging
import struct
from enum import IntEnum
from rs485_manager import RS485Manager
from battery_structures import BspBsmPlbModbus, Bsp4015Info, BatteryType


class M3ControllerError(IntEnum):
    OK = 0
    FAIL = 1
    INVALID_RESPONSE = 2
    TIMEOUT = 3


class M3Controller:
    """M3 控制器類，用於與電池盒內的M3通訊"""

    def __init__(self, rs485_manager: RS485Manager, logger: logging.Logger):
        self.rs485 = rs485_manager
        self.logger = logger

    def get_4015_status(self) -> tuple[M3ControllerError, Bsp4015Info]:
        """
        獲取4015充電IC的狀態
        :return: (錯誤碼, 4015狀態)
        """
        self.logger.debug("開始獲取4015狀態")

        # 準備命令數據
        command = 0x40
        data = bytearray([0x00])  # 假設原始C代碼中的 dummy 值

        # 發送命令，明確指定預期回應命令為 0x80
        success, response = self.rs485.send_command(
            command, data, expected_response_cmd=0x80, expect_response=True
        )

        if not success or response is None:
            self.logger.error("獲取4015狀態失敗: 無回應")
            return M3ControllerError.TIMEOUT, None

        # 檢查回應格式，將預期回應從 0x80 改為 0x80
        if len(response) < 6 or response[0] != 0xCC or response[3] != 0x80:
            self.logger.error(f"無效的4015狀態回應: {response.hex()}")
            return M3ControllerError.INVALID_RESPONSE, None

        try:
            # 從第6個byte開始是4015狀態數據
            frame_data = response[6:]
            self.logger.debug(f"完整回應: {response.hex()}")
            self.logger.debug(f"幀數據: {frame_data.hex()}")

            # 首先解析RTC部分 (BspM3Rtc / EEPROM_RTC_TIME_FRAME)
            # RTC結構: UINT16 Year, UINT8 Month, Day, WeekDay, Hour, Minute, Second
            rtc_size = 8  # 2 + 1*6

            # 跳過RTC部分，直接解析Bsp4015Info
            status_data = frame_data[rtc_size:]
            self.logger.debug(f"狀態數據: {status_data.hex()}")

            # 解析數據到Bsp4015Info結構
            status = Bsp4015Info()

            # 檢查數據長度是否足夠
            min_required_size = 29  # 至少需要29個字節才能解析11個必要欄位
            self.logger.debug(f"最少需要的數據大小: {min_required_size}字節")
            self.logger.debug(f"實際獲取的數據大小: {len(status_data)}字節")
            if len(status_data) < min_required_size:
                self.logger.error(
                    f"4015狀態數據長度不足，需要{min_required_size}字節，實際有{len(status_data)}字節"
                )
                return M3ControllerError.INVALID_RESPONSE, None

            # 逐一解析各欄位並輸出
            offset = 0

            # 解析6個int32_t: 電池電壓和電流值
            status.battery_a_voltage = struct.unpack(
                "<i", status_data[offset : offset + 4]
            )[0]
            self.logger.debug(
                f"電池A電壓原始值: {status.battery_a_voltage} ({status.battery_a_voltage / 1000}V)"
            )
            offset += 4

            status.battery_a_current = struct.unpack(
                "<i", status_data[offset : offset + 4]
            )[0]
            self.logger.debug(
                f"電池A電流原始值: {status.battery_a_current} ({status.battery_a_current / 1000}A)"
            )
            offset += 4

            status.battery_b_voltage = struct.unpack(
                "<i", status_data[offset : offset + 4]
            )[0]
            self.logger.debug(
                f"電池B電壓原始值: {status.battery_b_voltage} ({status.battery_b_voltage / 1000}V)"
            )
            offset += 4

            status.battery_b_current = struct.unpack(
                "<i", status_data[offset : offset + 4]
            )[0]
            self.logger.debug(
                f"電池B電流原始值: {status.battery_b_current} ({status.battery_b_current / 1000}A)"
            )
            offset += 4

            status.charging_voltage = struct.unpack(
                "<i", status_data[offset : offset + 4]
            )[0]
            self.logger.debug(
                f"充電電壓原始值: {status.charging_voltage} ({status.charging_voltage / 1000}V)"
            )
            offset += 4

            status.charging_current = struct.unpack(
                "<i", status_data[offset : offset + 4]
            )[0]
            self.logger.debug(
                f"充電電流原始值: {status.charging_current} ({status.charging_current / 1000}A)"
            )
            offset += 4

            # 解析1個uint32_t: 溫度
            status.die_temperature = struct.unpack(
                "<I", status_data[offset : offset + 4]
            )[0]
            self.logger.debug(
                f"硬體溫度原始值: {status.die_temperature} ({status.die_temperature / 10}°C)"
            )
            offset += 4

            # 解析1個uint16_t: APS狀態
            status.aps_status = struct.unpack(
                "<H", status_data[offset : offset + 2]
            )[0]
            self.logger.debug(f"APS狀態原始值: 0x{status.aps_status:04X}")
            offset += 2

            # 解析3個uint8_t: act, battery_slot_status, output_enable
            status.act = status_data[offset]
            self.logger.debug(f"使用電池原始值: {status.act}")
            offset += 1

            status.battery_slot_status = status_data[offset]
            self.logger.debug(
                f"電池插槽狀態原始值: {status.battery_slot_status}"
            )
            offset += 1

            status.output_enable = status_data[offset]
            self.logger.debug(f"12V輸出狀態原始值: {status.output_enable}")
            offset += 1

            # 查看是否有剩餘數據 (reserved字段)
            if len(status_data) > offset:
                reserved_data = status_data[offset:]
                self.logger.debug(f"剩餘保留數據: {reserved_data.hex()}")

            # 輸出整體摘要
            self.logger.debug("成功獲取4015狀態 - 摘要：")
            self.logger.debug(
                f"電池A: {status.battery_a_voltage / 1000}V / {status.battery_a_current / 1000}A"
            )
            self.logger.debug(
                f"電池B: {status.battery_b_voltage / 1000}V / {status.battery_b_current / 1000}A"
            )
            self.logger.debug(
                f"充電: {status.charging_voltage / 1000}V / {status.charging_current / 1000}A"
            )
            self.logger.debug(f"溫度: {status.die_temperature / 10}°C")
            self.logger.debug(
                f"狀態: APS=0x{status.aps_status:04X}, 使用電池={status.act}, 插槽狀態={status.battery_slot_status}, 輸出={status.output_enable}"
            )

            return M3ControllerError.OK, status

        except Exception as e:
            self.logger.exception(f"解析4015狀態數據時發生錯誤: {e}")
            return M3ControllerError.FAIL, None

    def get_batteries_info(
        self, battery_type: BatteryType
    ) -> tuple[M3ControllerError, BspBsmPlbModbus]:
        """
        獲取電池BMS信息
        :param battery_type: 電池類型 (A或B)
        :return: (錯誤碼, BMS信息)
        """
        self.logger.debug(f"開始獲取電池{battery_type.name}信息")

        # 準備命令數據
        command = 0x44
        data = bytearray([battery_type.value])  # 0代表A電池, 1代表B電池

        # 發送命令
        success, response = self.rs485.send_command(
            command,
            data,
            expected_response_cmd=0x84,
            expect_response=True,
            response_size=200,
        )  # BMS數據較大

        if not success or response is None:
            self.logger.error(f"獲取電池{battery_type.name}信息失敗: 無回應")
            return M3ControllerError.TIMEOUT, None

        # 檢查回應格式
        if len(response) < 6 or response[0] != 0xCC or response[3] != 0x84:
            self.logger.error(
                f"無效的電池{battery_type.name}信息回應: {response.hex()}"
            )
            return M3ControllerError.INVALID_RESPONSE, None

        try:
            # 從第6個byte開始是Frame數據
            frame_data = response[6:]
            self.logger.debug(f"完整回應: {response.hex()}")
            self.logger.debug(f"幀數據: {frame_data.hex()}")

            # 首先解析RTC部分 (BspM3Rtc)
            # RTC結構: UINT16 Year, UINT8 Month, Day, WeekDay, Hour, Minute, Second
            rtc_offset = 0
            rtc_year = struct.unpack(
                "<H", frame_data[rtc_offset : rtc_offset + 2]
            )[0]
            rtc_offset += 2
            rtc_month = frame_data[rtc_offset]
            rtc_offset += 1
            rtc_day = frame_data[rtc_offset]
            rtc_offset += 1
            rtc_day_of_week = frame_data[rtc_offset]
            rtc_offset += 1
            rtc_hour = frame_data[rtc_offset]
            rtc_offset += 1
            rtc_minute = frame_data[rtc_offset]
            rtc_offset += 1
            rtc_second = frame_data[rtc_offset]
            rtc_offset += 1

            # 創建BMS信息結構
            bms_info = BspBsmPlbModbus()

            self.logger.debug(
                f"RTC時間: {rtc_year}-{rtc_month:02d}-{rtc_day:02d} {rtc_hour:02d}:{rtc_minute:02d}:{rtc_second:02d} (星期{rtc_day_of_week})"
            )

            # 解析電池ID和BMS輪詢狀態
            bms_info.battery_id = frame_data[rtc_offset]
            self.logger.debug(f"電池ID: {bms_info.battery_id}")
            rtc_offset += 1
            bms_info.bms_polling_status = frame_data[rtc_offset]
            self.logger.debug(
                f"BMS輪詢狀態: 0x{bms_info.bms_polling_status:02X}"
            )
            rtc_offset += 1

            # 跳過reserved (2字節)
            rtc_offset += 2

            # 現在我們到了BspBsmPlbModbus結構的開始
            bms_data = frame_data[rtc_offset:]
            self.logger.debug(f"BMS數據: {bms_data.hex()}")

            # 檢查數據長度是否足夠
            min_required_size = 32 * 2  # 最少需要32個單元電壓 (64字節)
            if len(bms_data) < min_required_size:
                self.logger.error(
                    f"BMS數據長度不足，需要至少{min_required_size}字節，實際有{len(bms_data)}字節"
                )
                return M3ControllerError.INVALID_RESPONSE, None

            # 解析32個電池單元電壓 (每個2字節)
            offset = 0
            bms_info.bat_cell_voltage = []
            for i in range(32):
                if offset + 2 <= len(bms_data):
                    cell_voltage = struct.unpack(
                        "<H", bms_data[offset : offset + 2]
                    )[0]
                    bms_info.bat_cell_voltage.append(cell_voltage)
                    # 只顯示非零值以減少日誌輸出
                    if cell_voltage > 0:
                        self.logger.debug(
                            f"電池單元{i + 1}電壓: {cell_voltage}mV ({cell_voltage / 1000:.3f}V)"
                        )
                    offset += 2
                else:
                    bms_info.bat_cell_voltage.append(0)

            # 檢查剩餘數據是否足夠
            if len(bms_data) < offset + 46:  # 至少需要再46個字節解析基本字段
                self.logger.error(f"BMS數據不完整，無法解析電壓和電流信息")
                return M3ControllerError.INVALID_RESPONSE, None

            # 解析電壓相關參數
            bms_info.max_battery_voltage = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            self.logger.debug(
                f"最大電池電壓: {bms_info.max_battery_voltage}mV ({bms_info.max_battery_voltage / 1000:.3f}V)"
            )
            offset += 2

            bms_info.min_battery_voltage = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            self.logger.debug(
                f"最小電池電壓: {bms_info.min_battery_voltage}mV ({bms_info.min_battery_voltage / 1000:.3f}V)"
            )
            offset += 2

            bms_info.pack_voltage = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            self.logger.debug(
                f"PACK電壓: {bms_info.pack_voltage}mV ({bms_info.pack_voltage / 1000:.3f}V)"
            )
            offset += 2

            bms_info.bat_total_voltage = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            self.logger.debug(
                f"總電壓: {bms_info.bat_total_voltage / 100:.3f}V"
            )
            offset += 2

            # 解析充放電電流與容量
            bms_info.charging_current_low = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            self.logger.debug(
                f"充電電流: {bms_info.charging_current_low / 100:.3f}A"
            )
            offset += 2
            bms_info.discharging_current_low = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            self.logger.debug(
                f"放電電流: {bms_info.discharging_current_low / 100:.3f}A"
            )
            offset += 2
            bms_info.battery_capacity_lookup = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            self.logger.debug(
                f"電池容量查表: {bms_info.battery_capacity_lookup}mAh"
            )
            offset += 2
            bms_info.soc = struct.unpack("<H", bms_data[offset : offset + 2])[
                0
            ]
            # 通常SOC是以0.1%為單位
            self.logger.debug(f"SOC: {bms_info.soc}%")
            offset += 2

            # 解析狀態和校驗碼
            bms_info.soh = struct.unpack("<H", bms_data[offset : offset + 2])[
                0
            ]
            # 通常SOH也是以0.1%為單位
            self.logger.debug(f"SOH: {bms_info.soh}%")
            offset += 2
            bms_info.device_check_code = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            self.logger.debug(
                f"設備檢查碼: 0x{bms_info.device_check_code:04X}"
            )
            offset += 2

            # 解析PLC狀態
            bms_info.plc_overall_status = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            self.logger.debug(
                f"PLC綜合狀態: 0x{bms_info.plc_overall_status:04X}"
            )
            offset += 2
            bms_info.plc_overall_status2 = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            self.logger.debug(
                f"PLC綜合狀態2: 0x{bms_info.plc_overall_status2:04X}"
            )
            offset += 2

            # 如果數據足夠，繼續解析剩餘字段
            if len(bms_data) < offset + 4:
                self.logger.warning("BMS數據部分不完整，無法解析庫倫計算")
                return M3ControllerError.OK, bms_info

            bms_info.charge_coulomb_calc_high = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2
            bms_info.charge_coulomb_calc_low = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2

            charge_coulomb = (
                bms_info.charge_coulomb_calc_high << 16
            ) | bms_info.charge_coulomb_calc_low
            self.logger.debug(f"充電庫倫計算: {charge_coulomb}")

            # 7. 庫倫計算 (放電)
            if len(bms_data) < offset + 4:
                self.logger.warning("BMS數據部分不完整，無法解析放電庫倫計算")
                return M3ControllerError.OK, bms_info

            bms_info.discharge_coulomb_calc_high = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2
            bms_info.discharge_coulomb_calc_low = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2

            discharge_coulomb = (
                bms_info.discharge_coulomb_calc_high << 16
            ) | bms_info.discharge_coulomb_calc_low
            self.logger.debug(f"放電庫倫計算: {discharge_coulomb}")

            # 8. 電流高位
            if len(bms_data) < offset + 4:
                self.logger.warning(f"BMS數據部分不完整，無法解析電流高位")
                return M3ControllerError.OK, bms_info

            bms_info.charging_current_high = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2
            bms_info.discharging_current_high = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2

            # 計算完整電流值
            charging_current = (
                bms_info.charging_current_high << 16
            ) | bms_info.charging_current_low
            discharging_current = (
                bms_info.discharging_current_high << 16
            ) | bms_info.discharging_current_low
            self.logger.debug(
                f"完整充電電流: {charging_current}mA ({charging_current / 1000:.3f}A)"
            )
            self.logger.debug(
                f"完整放電電流: {discharging_current}mA ({discharging_current / 1000:.3f}A)"
            )

            # 9. 保留字段 (NC01-NC07)
            if len(bms_data) < offset + 14:
                self.logger.warning("BMS數據部分不完整，無法解析保留字段")
                return M3ControllerError.OK, bms_info

            nc_values = []
            for i in range(7):
                if offset + 2 <= len(bms_data):
                    nc = struct.unpack("<H", bms_data[offset : offset + 2])[0]
                    nc_values.append(nc)
                    offset += 2

            bms_info.nc = nc_values

            # 10. 溫度資訊
            if len(bms_data) < offset + 10:
                self.logger.warning("BMS數據部分不完整，無法解析溫度資訊")
                return M3ControllerError.OK, bms_info

            temp_values = []
            for i in range(5):
                if offset + 2 <= len(bms_data):
                    temp = struct.unpack("<H", bms_data[offset : offset + 2])[
                        0
                    ]
                    temp_values.append(temp)
                    self.logger.debug(f"溫度{i + 1}: {temp / 100:.2f}°C")
                    offset += 2

            bms_info.temperature = temp_values

            # 11. 充放電次數
            if len(bms_data) < offset + 2:
                self.logger.warning("BMS數據部分不完整，無法解析充放電次數")
                return M3ControllerError.OK, bms_info

            bms_info.charging_count = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            self.logger.debug(f"充放電次數: {bms_info.charging_count}")
            offset += 2

            # 12. 過壓/欠壓狀態
            if len(bms_data) < offset + 16:
                self.logger.warning("BMS數據部分不完整，無法解析過壓/欠壓狀態")
                return M3ControllerError.OK, bms_info

            # 過壓警告
            bms_info.ov_alert_low = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2
            bms_info.ov_alert_high = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2

            # 過壓保護
            bms_info.ov_protect_low = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2
            bms_info.ov_protect_high = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2

            # 欠壓警告
            bms_info.uv_alert_low = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2
            bms_info.uv_alert_high = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2

            # 欠壓保護
            bms_info.uv_protect_low = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2
            bms_info.uv_protect_high = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2

            # 組合成32位狀態
            ov_alert = (bms_info.ov_alert_high << 16) | bms_info.ov_alert_low
            ov_protect = (
                bms_info.ov_protect_high << 16
            ) | bms_info.ov_protect_low
            uv_alert = (bms_info.uv_alert_high << 16) | bms_info.uv_alert_low
            uv_protect = (
                bms_info.uv_protect_high << 16
            ) | bms_info.uv_protect_low

            self.logger.debug(f"過壓警告狀態: 0x{ov_alert:08x}")
            self.logger.debug(f"過壓保護狀態: 0x{ov_protect:08x}")
            self.logger.debug(f"欠壓警告狀態: 0x{uv_alert:08x}")
            self.logger.debug(f"欠壓保護狀態: 0x{uv_protect:08x}")

            # 13. Cell平衡狀態
            if len(bms_data) < offset + 4:
                self.logger.warning("BMS數據部分不完整，無法解析Cell平衡狀態")
                return M3ControllerError.OK, bms_info

            bms_info.cell_balance_status_low = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2
            bms_info.cell_balance_status_high = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2

            cell_balance = (
                bms_info.cell_balance_status_high << 16
            ) | bms_info.cell_balance_status_low
            self.logger.debug(f"Cell平衡狀態: 0x{cell_balance:08x}")

            # 14. 其他狀態
            if len(bms_data) < offset + 10:
                self.logger.warning("BMS數據部分不完整，無法解析其他狀態")
                return M3ControllerError.OK, bms_info

            bms_info.voltage_current_status = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            self.logger.debug(
                f"電壓電流偵測狀態: 0x{bms_info.voltage_current_status:04X}"
            )
            offset += 2

            bms_info.t1_t2_status = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            self.logger.debug(f"T1&T2偵測狀態: 0x{bms_info.t1_t2_status:04X}")
            offset += 2

            bms_info.t3_t4_status = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            self.logger.debug(f"T3&T4偵測狀態: 0x{bms_info.t3_t4_status:04X}")
            offset += 2

            bms_info.t5_temperature_status = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            self.logger.debug(
                f"T5溫度狀態: 0x{bms_info.t5_temperature_status:04X}"
            )
            offset += 2

            bms_info.overall_status = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            self.logger.debug(f"綜合狀態: 0x{bms_info.overall_status:04X}")
            offset += 2

            # 15. 庫倫計算之電池容量
            if len(bms_data) < offset + 4:
                self.logger.warning(
                    "BMS數據部分不完整，無法解析庫倫計算之電池容量"
                )
                return M3ControllerError.OK, bms_info

            bms_info.battery_capacity_coulomb_high = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2
            bms_info.battery_capacity_coulomb_low = struct.unpack(
                "<H", bms_data[offset : offset + 2]
            )[0]
            offset += 2

            battery_capacity_coulomb = (
                bms_info.battery_capacity_coulomb_high << 16
            ) | bms_info.battery_capacity_coulomb_low
            self.logger.debug(
                f"庫倫計算電池容量: {battery_capacity_coulomb}mAh"
            )

            # 檢查是否還有其他數據
            if offset < len(bms_data):
                self.logger.debug(
                    f"還有{len(bms_data) - offset}字節未解析的數據: {bms_data[offset:].hex()}"
                )

            self.logger.debug(f"成功獲取電池{battery_type.name}信息")
            return M3ControllerError.OK, bms_info

        except Exception as e:
            self.logger.exception(
                f"解析電池{battery_type.name}信息數據時發生錯誤: {e}"
            )
            return M3ControllerError.FAIL, None

    def get_firmware_version(self) -> tuple[M3ControllerError, str]:
        """
        查詢M3控制器的韌體版本
        :return: (錯誤碼, 版本字符串)
        """
        self.logger.debug("開始查詢M3韌體版本")

        # 準備命令數據 - 根據協議，請求版本命令為0x70，數據為00
        command = 0x70
        data = bytearray([0x00])  # 只需要發送一個字節

        # 發送命令，預期回應命令為0xF0，設定回應尺寸為22字节(標頭6字节 + 版本信息16字节)
        success, response = self.rs485.send_command(
            command,
            data,
            expected_response_cmd=0xF0,
            expect_response=True,
            response_size=22,
        )

        if not success or response is None:
            self.logger.error("查詢M3韌體版本失敗: 無回應")
            return M3ControllerError.TIMEOUT, "Unknown"

        # 檢查回應格式
        if (
            len(response) < 6 + 16
            or response[0] != 0xCC
            or response[3] != 0xF0
        ):
            self.logger.error(f"無效的M3韌體版本回應: {response.hex()}")
            return M3ControllerError.INVALID_RESPONSE, "Unknown"

        try:
            # 從第6個byte開始是16字節的韌體版本信息
            version_data = response[6 : 6 + 16]
            self.logger.debug(f"完整回應: {response.hex()}")
            self.logger.debug(f"版本數據: {version_data.hex()}")

            # 嘗試解析為ASCII字符串
            version_str = ""
            try:
                # 過濾非ASCII字符和空字元
                version_str = "".join(
                    chr(b) for b in version_data if 32 <= b <= 126
                )
                version_str = version_str.strip()
            except Exception:
                # 如果無法解析為字符串，則顯示為十六進制
                version_str = version_data.hex()

            if not version_str:
                version_str = "Unknown"

            self.logger.info(f"M3韌體版本: {version_str}")
            return M3ControllerError.OK, version_str

        except Exception as e:
            self.logger.exception(f"解析M3韌體版本數據時發生錯誤: {e}")
            return M3ControllerError.FAIL, "Unknown"
