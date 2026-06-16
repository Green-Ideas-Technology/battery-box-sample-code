import fcntl
import serial
import logging
import time


def compute_crc16(data: bytearray) -> int:
    """計算 CRC-16 (Modbus) 校驗和"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc = crc >> 1
    return crc


def build_rs485_packet(command: int, data_bytes: bytearray) -> bytearray:
    """構建 RS485 封包，格式：CC | 長度L | 長度H | 命令 | crcL | crcH | 資料..."""
    # 基本封包頭部
    header = bytearray([0xCC])

    # 計算長度 (命令1位元組 + 資料長度)
    data_len = len(data_bytes)
    len_low = data_len & 0xFF
    len_high = (data_len >> 8) & 0xFF

    # 組建命令部分
    cmd_part = bytearray([len_low, len_high, command])

    # 計算 CRC (不含CC)
    crc = compute_crc16(data_bytes)
    crc_low = crc & 0xFF
    crc_high = (crc >> 8) & 0xFF

    # 裝配完整封包
    return header + cmd_part + bytearray([crc_low, crc_high]) + data_bytes


class RS485LockManager:
    """
    RS485 串口鎖管理器，直接對 UART 設備上鎖

    這種方式直接對 UART 設備檔案描述符上鎖，任何程序打開同一個 UART 設備
    都會自動被鎖機制保護，無需額外的鎖檔案或命名約定。
    """

    def __init__(self, device_path: str, baud_rate: int, timeout: float = 1.0):
        self.device_path = device_path
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.serial_conn = None
        self.port_locked = False

    def __enter__(self):
        try:
            # 打開串口連接
            self.serial_conn = serial.Serial(
                port=self.device_path,
                baudrate=self.baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
            )

            # 直接對 UART 設備上排他鎖
            fcntl.flock(self.serial_conn.fileno(), fcntl.LOCK_EX)
            self.port_locked = True

            return self.serial_conn

        except Exception as e:
            if self.serial_conn:
                self.serial_conn.close()
            raise e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.port_locked and self.serial_conn and self.serial_conn.is_open:
            try:
                fcntl.flock(self.serial_conn.fileno(), fcntl.LOCK_UN)
                self.port_locked = False
            except Exception:
                pass  # 忽略釋放鎖時的錯誤

        if self.serial_conn:
            self.serial_conn.close()


class RS485Manager:
    """RS485 通訊管理器"""

    LEADING_CODE = 0xCC

    def __init__(
        self, device_path: str, baud_rate: int, logger: logging.Logger
    ):
        self.device_path = device_path
        self.baud_rate = baud_rate
        self.logger = logger

    def send_command(
        self,
        command: int,
        data: bytearray,
        expected_response_cmd: int = None,
        expect_response: bool = True,
        response_size: int = 50,
        timeout: float = 1.0,
    ):
        """
        發送命令並等待回應
        :param command: 要發送的命令
        :param data: 命令數據
        :param expected_response_cmd: 預期的回應命令，若為None則使用默認規則(0x80+command)
        :param expect_response: 是否期望有回應
        :param response_size: 預期的回應大小
        :param timeout: 等待回應的超時時間
        :return: (成功與否, 回應數據)
        """
        packet = build_rs485_packet(command, data)
        response = None

        try:
            # 直接對 UART 設備上鎖，自動管理串口連接
            lock_manager = RS485LockManager(
                self.device_path, self.baud_rate, timeout
            )
            with lock_manager as ser:
                self.logger.debug(
                    f"發送命令: 0x{command:02X}, 資料: {data.hex()}"
                )
                self.logger.debug(f"完整封包: {packet.hex()}")

                # 清空接收緩衝區
                ser.reset_input_buffer()

                # 發送命令
                ser.write(packet)

                # 若不需要回應，直接返回
                if not expect_response:
                    return True, None

                # 等待並讀取回應
                time.sleep(0.01)  # 短暫等待，確保資料已發送

                response = ser.read(response_size)
                if not response:
                    self.logger.warning(f"命令 0x{command:02X} 沒有回應")
                    return False, None

                self.logger.debug(f"接收到回應: {response.hex()}")

                # 檢查回應格式
                if len(response) < 6 or response[0] != self.LEADING_CODE:
                    self.logger.warning(f"回應格式錯誤: {response.hex()}")
                    return False, None

                # 檢查回應命令
                if expected_response_cmd is None:
                    # 使用預設規則
                    expected_response_cmd = 0x80 + (command & 0x7F)

                if response[3] != expected_response_cmd:
                    self.logger.warning(
                        f"回應命令錯誤: 預期 0x{expected_response_cmd:02X}, "
                        f"收到 0x{response[3]:02X}"
                    )
                    return False, None

                # 從第6個byte開始是實際數據
                return True, response

        except Exception as e:
            self.logger.exception(f"RS485通訊錯誤: {e}")
            return False, None

