import re
from time import sleep
from PySide6.QtCore import QThread, Signal
from modbus import ModbusClient, FloatModbusClient
from utils import *

# Класс потока, который будет считывать значения с заданным интервалом
class CounterThread(QThread):
    updated_value = Signal(int, list)  # Индекс адреса
    connection_lost = Signal(int)  # Обрыв связи

    def __init__(self, index, address, host='192.168.56.2', port=502, interval=500):
        super().__init__()
        self.index = index
        self.address = address
        self.interval = interval / 1000.0  # Переводим миллисекунды в секунды
        self.is_running = True
        self.host = host
        self.port = port
        self.mb_client = ModbusClient(host=host, port=port, auto_open=True, timeout=1)
        self.mb_float_read_from_client = FloatModbusClient(host=host, port=port, auto_open=True, timeout=1)
        self.register = 0

    def run(self):
        max_retries = 3  # Установите одну попытку для экономии ресурсов

        if not self.address:
            print(f"Ошибка: пустой адрес для потока {self.index}")
            self.connection_lost.emit(self.index)
            return

        try:
            self.register = int(self.address)
        except ValueError:
            print(f"Ошибка: недопустимый адрес '{self.address}' для потока {self.index}")
            self.connection_lost.emit(self.index)
            return

        bit_match = re.match(r"^(\d+)\.(\d+)$", str(self.address))
        if bit_match:
            self.register = int(bit_match.group(1))
            bit_position = int(bit_match.group(2))
        else:
            self.register = int(self.address)
            bit_position = None

        while self.is_running:
            try:
                if not self.mb_client.is_open:
                    self.mb_client.open()

                float_value, word1, word2, dword_value, bit_string = None, 0, 0, 0, 'Ошибка'

                # Попытка чтения float с одной попыткой
                float_result = self.mb_float_read_from_client.read_float(self.register, 1)
                if float_result and isinstance(float_result, list):
                    float_value = float_result[0]

                # Попытка чтения holding registers
                holding_registers = self.mb_client.read_holding_registers(self.register, 2)
                if isinstance(holding_registers, list) and len(holding_registers) >= 2:
                    word1, word2 = holding_registers[0], holding_registers[1]
                    dword_value = (word2 << 16) | word1
                    bit_string = dword_to_bit_string(holding_registers)

                    if bit_position is not None:
                        bit_value = (word1 >> bit_position) & 1
                        word1 = bit_value

                # Проверка перед обновлением значений
                if float_value is not None and holding_registers is not None:
                    self.updated_value.emit(self.index, [
                        float_value, dword_value, word1, bit_string
                    ])
                else:
                    print(f"Failed to read from address {self.register}")

            except Exception as e:
                print(f"Connection error at address {self.register}: {e}")
                self.connection_lost.emit(self.index)

            sleep(self.interval)

    def stop(self):
        self.is_running = False
        self.mb_client.close()
        self.wait()