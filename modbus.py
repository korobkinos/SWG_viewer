#!/usr/bin/env python3

""" How-to add float support to ModbusClient. """

from pyModbusTCP.client import ModbusClient
from pyModbusTCP.utils import (decode_ieee, encode_ieee, long_list_to_word,
                               word_list_to_long)


class FloatModbusClient(ModbusClient):
    """A ModbusClient class with float support."""

    def read_float(self, address, number=1):
        """Read float(s) with read holding registers."""
        reg_l = self.read_holding_registers(address, number * 2)
        if reg_l:
            results = []
            for i in range(number):
                reg1 = reg_l[i * 2]  # первый регистр
                reg2 = reg_l[i * 2 + 1]  # второй регистр
                # Объединение в 32-битное значение (little-endian)
                float_value = (reg2 << 16) | reg1
                decoded_value = decode_ieee(float_value)  # декодирование значения
                results.append(round(decoded_value, 6))  # округление до 6 знаков после запятой
            return results
        else:
            return None

    def write_float(self, address, floats_list):
        """Write float(s) with write multiple registers."""
        b32_l = [encode_ieee(f) for f in floats_list]
        b16_l = long_list_to_word(b32_l)
        return self.write_multiple_registers(address, b16_l)

# ip_cpu = '192.168.56.2'
# port = '502'