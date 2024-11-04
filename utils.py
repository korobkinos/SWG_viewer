

def dword_to_bit_string(dword):
    # Объединяем два 16-битных слова в одно 32-битное число
    lower_word = dword[0]  # Младшее слово
    upper_word = dword[1]  # Старшее слово
    combined_dword = (upper_word << 16) | lower_word

    # Преобразуем число в двоичную строку и удаляем префикс '0b'
    bit_string = bin(combined_dword)[2:].zfill(32)

    # Добавляем символы подчеркивания через каждые 4 бита
    formatted_bit_string = "_".join([bit_string[i:i+4] for i in range(0, len(bit_string), 4)])

    # Возвращаем строку в формате 2#...
    return f"2#{formatted_bit_string}"

