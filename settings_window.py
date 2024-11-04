from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QSpinBox, QCheckBox, QLabel, QPushButton

# Класс для окна настроек подключения
class SettingsWindow(QWidget):
    settings_saved = Signal(str, int, int, bool)  # Добавляем параметр online

    def __init__(self, ip, port, interval, online):
        super().__init__()
        self.setWindowFlags(Qt.Window)  # Устанавливаем флаг Qt.Window
        self.setWindowTitle("Настройки")
        self.setGeometry(400, 400, 300, 220)
        self.online = online  # Сохраняем начальное состояние

        # Остальной код вашего конструктора
        # Создаем интерфейс настроек
        self.layout = QFormLayout(self)

        # Поле для ввода IP-адреса
        self.ip_input = QLineEdit(self)
        self.ip_input.setText(ip)

        # Поле для ввода порта
        self.port_input = QLineEdit(self)
        self.port_input.setText(str(port))

        # Поле для ввода интервала опроса
        self.interval_input = QSpinBox(self)
        self.interval_input.setRange(10, 10000)  # Устанавливаем диапазон от 10 до 10000 мс
        self.interval_input.setValue(interval)
        self.interval_input.setSuffix(" мс")

        # Переключатель "Онлайн / Оффлайн"
        self.online_checkbox = QCheckBox("Онлайн")
        self.online_checkbox.setChecked(self.online)  # Устанавливаем начальное состояние
        self.online_checkbox.stateChanged.connect(self.toggle_online_status)

        # Добавляем элементы интерфейса
        self.layout.addRow(QLabel("IP-адрес:"), self.ip_input)
        self.layout.addRow(QLabel("Порт:"), self.port_input)
        self.layout.addRow(QLabel("Интервал опроса:"), self.interval_input)
        self.layout.addRow(self.online_checkbox)

        # Кнопка сохранения настроек
        self.save_button = QPushButton("OK", self)
        self.save_button.clicked.connect(self.save_config)
        self.layout.addRow(self.save_button)

        # Статус подключения
        self.status_label = QLabel("", alignment=Qt.AlignCenter)
        self.layout.addRow(self.status_label)


    def toggle_online_status(self, state):
        """Обрабатывает переключение состояния Онлайн/Оффлайн."""
        self.online = self.online_checkbox.isChecked()
        print(f"Checkbox toggled, online is now: {self.online}")  # Отладка

    def save_config(self):
        ip = self.ip_input.text()
        port = int(self.port_input.text())
        interval = self.interval_input.value()

        # Проверка состояния чекбокса для актуального `online`
        online = self.online_checkbox.isChecked()
        print(f"Saving config with online={online}")  # Отладка

        # Эмитируем сигнал после сохранения настроек
        self.settings_saved.emit(ip, port, interval, online)
        self.close()  # Закрыть окно после сохранения
