import re
from time import sleep
from PySide6.QtCore import QThread, Signal
from modbus import ModbusClient, FloatModbusClient
from utils import *

# Класс потока, который будет считывать значения с заданным интервалом
class CounterThread(QThread):
    updated_value = Signal(int, list)  # Добавили индекс адреса
    connection_lost = Signal(int)      # Сигнал для уведомления об обрыве связи

    def __init__(self, index, address, host='192.168.56.2', port=502, interval=100):
        super().__init__()
        self.index = index
        self.address = address
        self.interval = interval / 1000.0  # Переводим миллисекунды в секунды
        self.is_running = True
        self.host = host
        self.port = port
        self.mb_client = ModbusClient(host=host, port=port, auto_open=True, timeout=1)  # Тайм-аут 1 секунда
        self.mb_float_read_from_client = FloatModbusClient(host=host, port=port, auto_open=True, timeout=1)

    def run(self):
        max_retries = 3  # Максимальное количество попыток чтения данных

        # Проверка формата адреса на наличие бита (например, 6463.2)
        bit_match = re.match(r"^(\d+)\.(\d+)$", str(self.address))
        if bit_match:
            # Битовый адрес
            register = int(bit_match.group(1))
            bit_position = int(bit_match.group(2))
        else:
            # Обычный адрес
            register = int(self.address)
            bit_position = None

        while self.is_running:
            try:
                # Проверяем и открываем соединение, если оно закрыто
                if not self.mb_client.is_open:
                    self.mb_client.open()

                # Значения по умолчанию для данных
                float_value = [0.0]
                word1 = 0
                word2 = 0
                dword_value = 0
                bit_string = 'Ошибка'

                # Попытка чтения float данных с несколькими повторами
                for attempt in range(max_retries):
                    float_result = self.mb_float_read_from_client.read_float(register, 1)
                    if float_result is not None and isinstance(float_result, list):
                        float_value = float_result
                        break  # Успешное чтение, прерываем цикл
                    elif attempt == max_retries - 1:
                        print(
                            f"Error reading float value from address {register}: data is None after {max_retries} attempts")

                # Попытка чтения holding registers с несколькими повторами
                for attempt in range(max_retries):
                    holding_registers = self.mb_client.read_holding_registers(register, 2)
                    if isinstance(holding_registers, list) and len(holding_registers) >= 2:
                        word1 = holding_registers[0]
                        word2 = holding_registers[1]
                        dword_value = (word2 << 16) | word1
                        bit_string = dword_to_bit_string(holding_registers)

                        # Если это битовый адрес, извлекаем конкретный бит
                        if bit_position is not None:
                            bit_value = (word1 >> bit_position) & 1
                            word1 = bit_value  # Обновляем значение для WORD, чтобы передать только бит

                        break  # Успешное чтение, прерываем цикл
                    elif attempt == max_retries - 1:
                        print(
                            f"Error reading holding registers from address {register}: data is None after {max_retries} attempts")

                # Эмитируем сигнал с обновленными данными
                self.updated_value.emit(self.index, [
                    float_value[0], dword_value, word1, bit_string
                ])

            except Exception as e:
                print(f"Error reading values from address {register}: {e}")
                # Эмитируем сигнал об обрыве связи
                self.connection_lost.emit(self.index)

            sleep(self.interval)

    def stop(self):
        self.is_running = False
        self.mb_client.close()  # Закрываем соединение
        self.wait()
