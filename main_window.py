import json
import re

from PySide6.QtGui import QColor, QPixmap, QPainter, QAction
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QTableWidget, QPushButton, QFileDialog, QMessageBox, QLineEdit,
    QHeaderView, QFormLayout, QTableWidgetItem, QMenu
)
from PySide6.QtCore import QSize, QTimer, Qt
from pyModbusTCP.client import ModbusClient

from data_acquisition import CounterThread
from plot_window import PlotWindow, table_config_file
from settings_window import SettingsWindow
from config_manager import save_config, load_config


# Основной класс приложения
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Устанавливаем текущий путь конфигурации в None до загрузки
        self.current_config_path = None

        # Установка начальных значений для конфигурации
        self.ip = "192.168.56.2"
        self.port = 502
        self.interval = 100
        self.online = False  # По умолчанию приложение оффлайн
        self.mb_client = None  # Инициализация клиента как None

        # Инициализация графиков и линий
        self.plot_data = []  # Список для хранения добавленных тегов на график

        # Инициализация графиков и линий
        self.plot_lines = {}  # Словарь для хранения линий графика

        # Добавляем метку для отображения пути к текущей конфигурации
        self.config_path_label = QLabel("Конфигурация не загружена", self)

        # Создаем элементы интерфейса
        self.setWindowTitle("SWG Viewer")
        # self.resize(self.config.get('window_size', QSize(1000, 600)))

        self.connection_status_indicator = QLabel()
        self.connection_status_indicator.setPixmap(
            self.create_circle_pixmap(QColor('red')))  # Начальное состояние offline


        # Кнопка для открытия окна графика
        self.plot_button = QPushButton("Графики", self)
        self.plot_button.clicked.connect(self.open_plot_window)

        # Инициализируем состояние подключения
        self.connection_status_label = QLabel("")
        self.update_connection_status()

        # Таймер для периодической проверки состояния подключения
        self.connection_timer = QTimer(self)
        self.connection_timer.timeout.connect(self.update_connection_status)
        self.connection_timer.start(5000)  # Проверка каждые 5 секунд

        # Устанавливаем размер окна из конфигурации
        # self.resize(self.config.get('window_size', QSize(800, 400)))
        self.mb_client = ModbusClient(host=self.ip, port=self.port, auto_open=True, timeout=1)
        # Список адресов и потоков
        self.addresses = []
        self.threads = []

        # Поля ввода для номера горелки и слова
        self.burner_number_input = QLineEdit(self)
        self.burner_number_input.setPlaceholderText("Введите номер горелки (0-20)")
        self.burner_number_input.editingFinished.connect(self.update_address_from_burner_word)

        self.word_input = QLineEdit(self)
        self.word_input.setPlaceholderText("Введите слово (1-31)")
        self.word_input.editingFinished.connect(self.update_address_from_burner_word)

        self.calculate_button = QPushButton("Вычислить адрес", self)
        self.calculate_button.clicked.connect(self.calculate_address)

        # Поле ввода для комментария
        self.comment_input = QLineEdit(self)
        self.comment_input.setPlaceholderText("Введите комментарий")

        # Поле ввода для адреса
        self.address_input = QLineEdit(self)
        self.address_input.setPlaceholderText("Введите Modbus адрес")
        # self.address_input.editingFinished.connect(self.handle_address_input)

        # Кнопки для добавления и удаления строк
        self.add_button = QPushButton("Добавить", self)
        self.add_button.clicked.connect(self.add_address)

        self.pending_deletions = []  # Список для хранения удаленных ключей
        self.remove_button = QPushButton("Удалить", self)
        self.remove_button.clicked.connect(self.remove_selected_address)

        # Кнопка для открытия окна настроек подключения
        self.settings_button = QPushButton("Настройки", self)
        self.settings_button.clicked.connect(self.open_settings_window)

        self.save_button = QPushButton("Сохранить", self)
        self.save_button.clicked.connect(self.save_config)

        self.load_button = QPushButton("Загрузить", self)
        self.load_button.clicked.connect(self.load_config)

        # Инициализация окна графика как None, чтобы избежать ошибки при загрузке
        self.plot_window = None

        # Кнопки для управления графиком
        self.add_to_plot_btn = QPushButton("Добавить на график")
        self.remove_from_plot_btn = QPushButton("Удалить с графика")
        self.add_to_plot_btn.setEnabled(False)
        self.remove_from_plot_btn.setEnabled(False)
        self.add_to_plot_btn.clicked.connect(self.add_selected_to_plot)
        self.remove_from_plot_btn.clicked.connect(self.remove_selected_from_plot)

        # Таблица для отображения данных
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Address", "REAL", "DWORD", "WORD", "BOOL", "Комментарий"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Interactive)  # Разрешаем изменять ширину столбцов

        # Включаем возможность обработки контекстного меню для заголовка таблицы
        self.table.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.horizontalHeader().customContextMenuRequested.connect(self.show_column_menu)


        # Обработчик изменения ячейки
        self.table.itemChanged.connect(self.handle_item_changed)
        self.table.itemSelectionChanged.connect(self.handle_selection_change)

        # Метка состояния подключения
        self.connection_status_label = QLabel("")
        self.update_connection_status()  # Устанавливаем начальный статус

        # Таймер для периодической проверки состояния подключения
        self.connection_timer = QTimer(self)
        self.connection_timer.timeout.connect(self.update_connection_status)
        self.connection_timer.start(5000)  # Проверка каждые 5 секунд

        # Макет для ввода данных и кнопок
        input_layout = QFormLayout()
        input_layout.addRow("Номер горелки:", self.burner_number_input)
        input_layout.addRow("Слово:", self.word_input)
        input_layout.addRow(self.calculate_button)
        input_layout.addRow("Вычисленный адрес:", self.address_input)
        input_layout.addRow("Комментарий:", self.comment_input)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.settings_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.load_button)

        # Основной макет
        layout = QVBoxLayout()

        button_layout.addWidget(self.add_to_plot_btn)
        # button_layout.addWidget(self.remove_from_plot_btn)
        layout.addLayout(input_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self.plot_button)
        layout.addWidget(self.table)
        layout.addWidget(self.connection_status_label)  # Добавляем метку состояния подключения
        layout.addWidget(self.config_path_label)  # Добавляем метку в нижнюю часть окна
        self.setLayout(layout)

        # Таймер для обновления графика
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(self.interval)

        # Загружаем конфигурацию, если она доступна
        try:
            self.load_config()
        except FileNotFoundError:
            # Если файл не найден, просто оставляем начальные значения
            self.config_path_label.setText("Конфигурация не загружена")

    def show_column_menu(self, pos):
        """Показать меню для выбора видимых столбцов."""
        menu = QMenu(self)

        # Добавляем чекбоксы для каждого столбца
        for col in range(self.table.columnCount()):
            column_name = self.table.horizontalHeaderItem(col).text()
            action = QAction(column_name, self)
            action.setCheckable(True)
            action.setChecked(not self.table.isColumnHidden(col))
            action.toggled.connect(lambda checked, col=col: self.set_column_visibility(col, checked))
            menu.addAction(action)

        # Отображаем меню под курсором
        header = self.table.horizontalHeader()
        menu.exec(header.mapToGlobal(pos))

    def set_column_visibility(self, col, visible):
        """Устанавливает видимость указанного столбца."""
        self.table.setColumnHidden(col, not visible)


    def save_plot_data(self):
        """Сохранение текущей конфигурации графиков в файл и обновление plot_data."""
        if self.plot_window:
            self.plot_data = [(row, col) for row, col in self.plot_window.lines]

            config = {
                'plot_data': self.plot_data,
            }
            with open(table_config_file, 'w') as f:
                json.dump(config, f, indent=4)

    def remove_tag_from_plot_data(self, key):
        """Удалить тег из plot_data для поддержания синхронизации."""
        if key in self.plot_data:
            self.plot_data.remove(key)
        self.save_plot_data()  # Сохранение после удаления

    def handle_address_input(self):
        """Обработка ввода адреса для чтения значений из Modbus."""
        address_text = self.address_input.text().strip()

        # Проверка, существует ли объект mb_client
        if not hasattr(self, 'mb_client'):
            print("Error: mb_client is not initialized")
            return

        # Проверяем, соответствует ли формат "число.число"
        match = re.match(r"^(\d+)\.(\d+)$", address_text)
        if match:
            # Извлекаем номер регистра и бита
            register = int(match.group(1))
            bit_position = int(match.group(2))

            # Проверка, что номер бита находится в диапазоне от 0 до 15
            if 0 <= bit_position <= 15:
                # Чтение регистра Modbus
                holding_registers = self.mb_client.read_holding_registers(register, 1)
                if isinstance(holding_registers, list) and len(holding_registers) > 0:
                    # Получаем значение регистра
                    register_value = holding_registers[0]

                    # Извлекаем значение бита с помощью побитового сдвига и побитовой операции И
                    bit_value = (register_value >> bit_position) & 1

                    # Проверяем, выбрана ли строка в таблице
                    current_row = self.table.currentRow()
                    if current_row == -1:
                        # Если строка не выбрана, добавляем новую строку
                        current_row = self.table.rowCount()
                        self.table.insertRow(current_row)
                        self.table.setItem(current_row, 0, QTableWidgetItem(address_text))  # Вставляем адрес

                    # Обновляем поле WORD: 1 для True, 0 для False
                    self.table.setItem(current_row, 3, QTableWidgetItem(str(bit_value)))

                    # Устанавливаем DWORD и REAL в 0, так как это битовый адрес
                    self.table.setItem(current_row, 1, QTableWidgetItem("0.0"))  # REAL
                    self.table.setItem(current_row, 2, QTableWidgetItem("0"))  # DWORD
                else:
                    print(f"Error: Could not read register {register}")
            else:
                print("Error: Bit position must be between 0 and 15")
        else:
            print("Error: Invalid address format. Use 'register.bit', e.g., 1492.1")

    def closeEvent(self, event):
        """Закрываем все дочерние окна при закрытии главного окна."""
        # Закрываем окно настроек, если оно открыто
        if hasattr(self, 'settings_window') and self.settings_window is not None:
            self.settings_window.close()
        # Закрываем окно графика, если оно открыто
        if hasattr(self, 'plot_window') and self.plot_window is not None:
            self.plot_window.close()
        # Останавливаем все потоки
        self.stop_all_threads()
        # Закрываем главное окно
        event.accept()

    def open_plot_window(self):
        """Открыть окно графика и восстановить линии графиков из данных."""
        if not self.plot_window:
            self.plot_window = PlotWindow(self)  # Создаем новое окно

        # Восстанавливаем линии из plot_data
        self.update_graphs()

        # Отображаем окно
        self.plot_window.show()

    def add_selected_to_plot(self):
        """Добавить выбранную строку и столбец на график с меткой."""
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            column = selected[0].column()
            column_name = self.table.horizontalHeaderItem(column).text()
            key = (row, column_name)

            # Добавляем тег в plot_data, если его там нет
            if key not in self.plot_data:
                self.plot_data.append(key)

            # Если окно графиков открыто, добавляем линию на график
            if self.plot_window and self.plot_window.isVisible():
                address_item = self.table.item(row, 0)
                address = address_item.text() if address_item else "Unknown"
                self.plot_window.add_line(key, f"{address} ({column_name})")

    def remove_selected_from_plot(self):
        """Удалить выбранную линию с графика и из сохраненных данных."""
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            column = selected[0].column()
            column_name = self.table.horizontalHeaderItem(column).text()
            key = (row, column_name)

            # Удаляем тег из plot_data, если он там есть
            if key in self.plot_data:
                self.plot_data.remove(key)

            # Если окно графиков открыто, удаляем линию с графика
            if self.plot_window and self.plot_window.isVisible():
                self.plot_window.remove_line(key)

    def handle_selection_change(self):
        """Активируем кнопки добавления и удаления графика при выборе строки и столбца."""
        selected_items = self.table.selectedItems()
        if selected_items:
            selected_item = selected_items[0]
            # Проверяем, выбран ли нужный столбец (REAL, DWORD или WORD)
            if selected_item.column() in [1, 2, 3]:  # Столбцы для REAL, DWORD, WORD
                self.add_to_plot_btn.setEnabled(True)
                self.remove_from_plot_btn.setEnabled(True)
            else:
                self.add_to_plot_btn.setEnabled(False)
                self.remove_from_plot_btn.setEnabled(False)
        else:
            self.add_to_plot_btn.setEnabled(False)
            self.remove_from_plot_btn.setEnabled(False)

    def update_plot(self):
        """Обновляем линии графика с данными из таблицы."""
        if self.plot_window is None:
            return  # Окно графика не открыто

        for key in self.plot_window.lines:
            row, column_name = key
            column_index = {"REAL": 1, "DWORD": 2, "WORD": 3}.get(column_name, None)
            if column_index is not None:
                item = self.table.item(row, column_index)
                if item:
                    try:
                        new_value = float(item.text())
                    except ValueError:
                        new_value = 0.0
                    self.plot_window.update_line(key, new_value)

    def load_config(self):
        """Загрузка всех настроек из одного файла конфигурации."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Загрузить конфигурацию", "", "JSON Files (*.json)")
        if not file_path:
            return  # Если файл не выбран, выходим из функции

        try:
            # Чтение данных из файла
            with open(file_path, 'r') as f:
                config = json.load(f)

            # Если окно графика открыто, очищаем его, иначе просто сохраняем данные
            if self.plot_window is not None:
                for line in list(self.plot_window.lines.values()):
                    self.plot_window.plot_widget.removeItem(line)
                self.plot_window.lines.clear()
                self.plot_window.y_data.clear()

            # Сохраняем состояние графиков для последующего восстановления
            self.plot_data = config.get("plot_state", [])

            # Если окно графиков открыто, восстанавливаем линии графика
            if self.plot_window is not None:
                self.update_graphs()

            # Обновляем текущий путь конфигурации
            self.current_config_path = file_path
            self.config_path_label.setText(f"Текущая конфигурация: {file_path}")

        except FileNotFoundError:
            self.config_path_label.setText("Файл конфигурации не найден.")
        except json.JSONDecodeError:
            self.config_path_label.setText("Ошибка чтения файла конфигурации.")

    def update_graphs(self):
        """Восстановить графики из plot_data при открытии окна графика."""
        for row, column_name in self.plot_data:
            key = (row, column_name)
            if self.plot_window and key not in self.plot_window.lines:
                address_item = self.table.item(row, 0)
                address = address_item.text() if address_item else "Unknown"
                self.plot_window.add_line(key, f"{address} ({column_name})")

    def open_settings_window(self):
        """Открыть окно настроек подключения."""
        print(f"Opening settings with current online status: {self.online}")  # Отладка
        # Создаем окно настроек без родителя
        self.settings_window = SettingsWindow(self.ip, self.port, self.interval, self.online)
        self.settings_window.settings_saved.connect(self.update_connection_params)
        self.settings_window.show()

    def update_connection_params(self, ip, port, interval, online):
        """Обновить параметры подключения и состояние онлайн."""
        self.ip = ip
        self.port = port
        self.interval = interval
        self.online = online  # Обновляем состояние подключения

        print(f"Update connection: IP={self.ip}, port={self.port}, interval={self.interval}, online={self.online}")

        if self.online:
            self.connect_to_modbus()  # Подключаемся
            self.start_all_threads()  # Запускаем потоки
        else:
            self.stop_all_threads()  # Останавливаем потоки
            self.disconnect_from_modbus()  # Отключаемся
            self.reset_tag_values()  # Сбрасываем значения тегов

        self.update_connection_status()
        print(f"Current online status after update: {self.online}")

    def reset_tag_values(self):
        """Обнуляет значения всех тегов в таблице."""
        for row in range(self.table.rowCount()):
            self.table.setItem(row, 1, QTableWidgetItem("0.0"))  # REAL
            self.table.setItem(row, 2, QTableWidgetItem("0"))    # DWORD
            self.table.setItem(row, 3, QTableWidgetItem("0"))    # WORD
            self.table.setItem(row, 4, QTableWidgetItem("Ошибка"))  # BOOL
        print("All tag values reset to zero.")

    def start_all_threads(self):
        """Запуск всех потоков для чтения данных."""
        self.threads = []  # Сбрасываем список потоков
        for row in range(self.table.rowCount()):
            address_item = self.table.item(row, 0)
            if address_item:
                address = address_item.text()
                thread = CounterThread(row, address, self.ip, self.port, self.interval)
                thread.updated_value.connect(self.update_table)
                thread.connection_lost.connect(self.handle_connection_lost)
                self.threads.append(thread)
                thread.start()
        print("All threads started")

    def stop_all_threads(self):
        """Останавливаем все потоки чтения данных."""
        for thread in self.threads:
            # Отключаем сигналы от потока
            try:
                thread.updated_value.disconnect(self.update_table)
                thread.connection_lost.disconnect(self.handle_connection_lost)
            except TypeError:
                pass  # Сигнал уже отключен

            thread.stop()  # Останавливаем поток
            thread.wait()  # Дожидаемся завершения потока
        self.threads.clear()
        print("All threads stopped")

    def connect_to_modbus(self):
        """Подключиться к серверу Modbus."""
        if not self.mb_client.is_open:
            try:
                self.mb_client = ModbusClient(host=self.ip, port=self.port, auto_open=True, timeout=1)
                self.mb_client.open()
                if self.mb_client.is_open:
                    print("Connected to Modbus server.")
                    self.connection_status_label.setText(f"IP: {self.ip} - online")
            except Exception as e:
                print(f"Failed to connect to Modbus server: {e}")
                self.connection_status_label.setText(f"IP: {self.ip} - offline")

    def disconnect_from_modbus(self):
        """Отключиться от сервера Modbus."""
        if self.mb_client and self.mb_client.is_open:
            self.mb_client.close()
            print("Disconnected from Modbus server.")
        self.connection_status_label.setText(f"IP: {self.ip} - offline")

    def handle_connection_lost(self, index):
        """Обработчик обрыва связи"""
        self.connection_status_label.setText(f"IP: {self.ip} - offline")
        print(f"Connection lost at row {index}")

    def update_connection_status(self):
        """Проверяет состояние подключения и обновляет метку состояния с индикатором."""
        if self.mb_client and self.mb_client.is_open and self.online:
            status_text = f"IP: {self.ip} - online"
            color = "green"
            print("Status: Online")
        else:
            status_text = f"IP: {self.ip} - offline"
            color = "red"
            print("Status: Offline")

        # Обновляем статус с индикатором
        self.connection_status_label.setText(f"{status_text} <span style='color:{color};'>●</span>")


    # Метод для создания цветного кругового индикатора
    def create_circle_pixmap(self, color):
        pixmap = QPixmap(10, 10)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 10, 10)
        painter.end()
        return pixmap

    def calculate_address(self):
        # Получаем номер горелки и слово
        try:
            burner_number = int(self.burner_number_input.text())
            word = int(self.word_input.text())
            if 0 <= burner_number <= 20 and 1 <= word <= 31:
                # Вычисляем адрес Modbus
                address = 1344 + (word - 1) * 2 + 64 * burner_number
                self.address_input.setText(str(address))
            else:
                self.address_input.setText("0")  # При недопустимых значениях
        except ValueError:
            self.address_input.setText("0")

    def update_address_from_burner_word(self):
        """Пересчитывает адрес на основе номера горелки и слова."""
        address_text = self.address_input.text().strip()

        # Проверяем, соответствует ли формат "число.число"
        match = re.match(r"^(\d+)\.(\d+)$", address_text)
        if match:
            # Если адрес в формате "регистр.бит"
            register = int(match.group(1))
            bit_position = int(match.group(2))

            if 0 <= bit_position <= 15:
                # Устанавливаем "Вычисленный адрес" для битового адреса
                self.address_input.setText(f"{register}.{bit_position}")
            else:
                self.address_input.setText("Введите корректный адрес")
        else:
            # Если адрес в обычном формате, обрабатываем его как раньше
            try:
                burner_number = int(self.burner_number_input.text())
                word = int(self.word_input.text())
                if 0 <= burner_number <= 20 and 1 <= word <= 31:
                    # Вычисляем адрес Modbus
                    address = 1344 + (word - 1) * 2 + 64 * burner_number
                    self.address_input.setText(str(address))
                else:
                    self.address_input.setText("Введите корректный адрес")
            except ValueError:
                self.address_input.setText("Введите корректный адрес")

    def update_burner_word_from_address(self):
        """Пересчитывает номер горелки и слово на основе адреса."""
        try:
            address = int(self.address_input.text())
            if address >= 1344:
                burner_number = (address - 1344) // 64
                word = ((address - 1344) % 64) // 2 + 1
                if 0 <= burner_number <= 20 and 1 <= word <= 31:
                    self.burner_number_input.setText(str(burner_number))
                    self.word_input.setText(str(word))
                else:
                    self.burner_number_input.setText("0")
                    self.word_input.setText("0")
            else:
                self.burner_number_input.setText("0")
                self.word_input.setText("0")
        except ValueError:
            self.burner_number_input.setText("0")
            self.word_input.setText("0")

    def add_address(self):
        # Отключаем сигналы, чтобы предотвратить срабатывание handle_item_changed
        self.table.blockSignals(True)

        # Получаем текст из поля "Вычисленный адрес" и комментарий
        address_text = self.address_input.text().strip()
        comment_text = self.comment_input.text().strip() if hasattr(self, 'comment_input') else ""

        # Проверяем, существует ли уже строка с таким адресом
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0) and self.table.item(row, 0).text() == address_text:
                QMessageBox.warning(self, "Ошибка", "Адрес уже существует в таблице.")
                self.table.blockSignals(False)
                return  # Выходим из функции, если адрес уже существует

        # Добавляем новую строку в таблицу
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        self.table.setItem(row_position, 0, QTableWidgetItem(address_text))  # Адрес
        self.table.setItem(row_position, 1, QTableWidgetItem("0.0"))  # REAL
        self.table.setItem(row_position, 2, QTableWidgetItem("0"))  # DWORD
        self.table.setItem(row_position, 3, QTableWidgetItem("0"))  # WORD
        self.table.setItem(row_position, 4, QTableWidgetItem("Ошибка"))  # BOOL
        self.table.setItem(row_position, 5, QTableWidgetItem(comment_text))  # Комментарий

        # Включаем обработку сигналов обратно после завершения добавления
        self.table.blockSignals(False)

        # Если приложение в режиме online, запускаем поток для этого адреса
        if self.online:
            thread = CounterThread(row_position, address_text, self.ip, self.port, self.interval)
            thread.updated_value.connect(self.update_table)
            thread.connection_lost.connect(self.handle_connection_lost)
            self.threads.insert(row_position, thread)
            thread.start()

    def remove_selected_address(self):
        selected_row = self.table.currentRow()
        if selected_row >= 0:
            # Останавливаем и удаляем соответствующий поток
            if selected_row < len(self.threads):
                thread = self.threads.pop(selected_row)
                thread.stop()
                thread.wait()

            # Удаляем строку из таблицы
            self.table.removeRow(selected_row)

            # Обновляем индексы потоков
            for i in range(selected_row, len(self.threads)):
                self.threads[i].index = i  # Обновляем индекс потока

        else:
            QMessageBox.warning(self, "Ошибка", "Выберите строку для удаления.")

    def handle_item_changed(self, item):
        if not self.online:
            return  # Не выполняем никаких действий в режиме "offline"
        """Обработчик для изменений ячеек в таблице."""
        row = item.row()
        column = item.column()

        if column == 0:  # Если изменяется столбец Address
            address_text = item.text().strip()

            # Проверка формата "число.число" для битового адреса
            bit_match = re.match(r"^(\d+)\.(\d+)$", address_text)
            if bit_match:
                # Битовый адрес
                register = int(bit_match.group(1))
                bit_position = int(bit_match.group(2))

                if 0 <= bit_position <= 15:
                    # Останавливаем текущий поток для этой строки, если он существует
                    if row < len(self.threads) and self.threads[row] is not None:
                        self.threads[row].stop()
                        self.threads[row].wait()

                    # Удаляем старый поток из списка
                    if row < len(self.threads):
                        self.threads.pop(row)

                    # Чтение регистра Modbus
                    holding_registers = self.mb_client.read_holding_registers(register, 1)
                    if isinstance(holding_registers, list) and len(holding_registers) > 0:
                        register_value = holding_registers[0]
                        bit_value = (register_value >> bit_position) & 1

                        # Обновляем значения в таблице: WORD — значение бита, DWORD и REAL — 0
                        self.table.setItem(row, 1, QTableWidgetItem("0.0"))  # REAL
                        self.table.setItem(row, 2, QTableWidgetItem("0"))  # DWORD
                        self.table.setItem(row, 3, QTableWidgetItem(str(bit_value)))  # WORD
                        self.table.setItem(row, 4, QTableWidgetItem("True" if bit_value else "False"))  # BOOL

                        # Перезапускаем поток для нового адреса
                        thread = CounterThread(row, f"{register}.{bit_position}", self.ip, self.port, self.interval)
                        thread.updated_value.connect(self.update_table)
                        self.threads.insert(row, thread)
                        thread.start()
                    else:
                        QMessageBox.warning(self, "Ошибка", f"Не удалось прочитать регистр {register}")
                else:
                    QMessageBox.warning(self, "Ошибка", "Введите корректный бит от 0 до 15.")
            elif address_text.isdigit():
                # Обычный адрес
                register = int(address_text)

                # Останавливаем текущий поток для этой строки, если он существует
                if row < len(self.threads) and self.threads[row] is not None:
                    self.threads[row].stop()
                    self.threads[row].wait()

                # Удаляем старый поток из списка
                if row < len(self.threads):
                    self.threads.pop(row)

                # Перезапускаем поток для обычного регистра
                thread = CounterThread(row, register, self.ip, self.port, self.interval)
                thread.updated_value.connect(self.update_table)
                self.threads.insert(row, thread)
                thread.start()
            else:
                QMessageBox.warning(self, "Ошибка", "Введите корректный адрес в формате 'число' или 'число.число'")
            # Если приложение в режиме online, перезапускаем поток
            if self.online:
                # Останавливаем текущий поток для этой строки, если он существует
                if row < len(self.threads) and self.threads[row] is not None:
                    self.threads[row].stop()
                    self.threads[row].wait()

                # Удаляем старый поток из списка
                if row < len(self.threads):
                    self.threads.pop(row)

                # Создаем и запускаем новый поток
                thread = CounterThread(row, address_text, self.ip, self.port, self.interval)
                thread.updated_value.connect(self.update_table)
                self.threads.insert(row, thread)
                thread.start()

    def update_table(self, index, values):
        if not self.online:
            return  # Не обновляем таблицу в режиме "offline"
        # Обновляем значения в таблице
        self.table.setItem(index, 1, QTableWidgetItem(str(values[0])))
        self.table.setItem(index, 2, QTableWidgetItem(str(values[1])))
        self.table.setItem(index, 3, QTableWidgetItem(str(values[2])))
        self.table.setItem(index, 4, QTableWidgetItem(values[3]))

    def save_config(self):
        """Сохранение всех настроек в один файл конфигурации."""
        # Открыть диалог для сохранения файла
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить конфигурацию", "", "JSON Files (*.json)")
        if not file_path:
            return  # Если файл не выбран, выходим из функции

        # Формируем данные для сохранения
        config_data = {
            "connection": {
                "ip": self.ip,
                "port": self.port,
                "interval": self.interval
            },
            "window_size": [self.width(), self.height()],
            "table_data": [],
            "column_widths": [self.table.columnWidth(i) for i in range(self.table.columnCount())],
            "plot_state": [(key[0], key[1]) for key in self.plot_window.lines] if self.plot_window else []
        }

        # Сохраняем данные таблицы
        for row in range(self.table.rowCount()):
            address_item = self.table.item(row, 0)
            comment_item = self.table.item(row, 5)
            if address_item and comment_item:
                config_data["table_data"].append({
                    "address": address_item.text(),
                    "comment": comment_item.text()
                })

        # Сохраняем данные в выбранный файл
        with open(file_path, 'w') as f:
            json.dump(config_data, f, indent=4)

        # Обновляем текущий путь конфигурации
        self.current_config_path = file_path
        self.config_path_label.setText(f"Текущая конфигурация: {file_path}")

        # Показать сообщение об успешном сохранении
        message_box = QMessageBox(self)
        message_box.setWindowTitle("Сохранение")
        message_box.setText("Конфигурация успешно сохранена!")
        message_box.setWindowModality(Qt.ApplicationModal)
        message_box.exec()

    def load_config(self):
        """Загрузка всех настроек из одного файла конфигурации."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Загрузить конфигурацию", "", "JSON Files (*.json)")
        if not file_path:
            return  # Если файл не выбран, выходим из функции

        try:
            # Чтение данных из файла
            with open(file_path, 'r') as f:
                config = json.load(f)

            # Закрываем и удаляем текущее окно графиков перед загрузкой новой конфигурации
            if self.plot_window is not None:
                self.plot_window.close()
                self.plot_window = None

            # Загрузка настроек подключения
            connection = config.get("connection", {})
            self.ip = connection.get("ip", "192.168.56.2")
            self.port = connection.get("port", 502)
            self.interval = connection.get("interval", 100)

            # Загрузка данных окна
            window_size = config.get("window_size", [800, 400])
            self.resize(QSize(window_size[0], window_size[1]))

            # Загрузка данных таблицы
            self.table.setRowCount(0)  # Очищаем таблицу перед загрузкой
            for row_data in config.get("table_data", []):
                row_position = self.table.rowCount()
                self.table.insertRow(row_position)
                self.table.setItem(row_position, 0, QTableWidgetItem(str(row_data["address"])))
                self.table.setItem(row_position, 1, QTableWidgetItem("0.0"))
                self.table.setItem(row_position, 2, QTableWidgetItem("0"))
                self.table.setItem(row_position, 3, QTableWidgetItem("0"))
                self.table.setItem(row_position, 4, QTableWidgetItem("Ошибка"))

                comment_item = QTableWidgetItem(row_data["comment"])
                comment_item.setFlags(comment_item.flags() | Qt.ItemIsEditable)
                self.table.setItem(row_position, 5, comment_item)

            # Сохраняем состояние графиков для отложенной загрузки
            plot_state = config.get("plot_state", [])
            self.plot_data = plot_state  # Сохраняем данные графиков для открытия

            # Обновляем текущий путь конфигурации
            self.current_config_path = file_path
            self.config_path_label.setText(f"Текущая конфигурация: {file_path}")

        except FileNotFoundError:
            self.config_path_label.setText("Файл конфигурации не найден.")
        except json.JSONDecodeError:
            self.config_path_label.setText("Ошибка чтения файла конфигурации.")

