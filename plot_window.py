import json
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QTableWidget, QPushButton, QWidget, QTableWidgetItem

# Файл для хранения настроек и конфигурации таблицы
config_file = 'config.json'
table_config_file = 'table_config.json'

class PlotWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Отложенный импорт
        if parent:
            from main_window import MainWindow
            assert isinstance(parent, MainWindow)
        self.setWindowTitle("Графики")
        self.resize(800, 600)
        self.setWindowModality(Qt.NonModal)  # Устанавливаем немодальное окно

        # Виджет графика
        self.plot_widget = pg.PlotWidget(title="")
        self.plot_widget.setLabel("left", "Value")
        self.plot_widget.setLabel("bottom", "Time")
        self.plot_widget.addLegend()

        # Словари для линий и данных
        self.lines = {}
        self.y_data = {}

        # Добавляем таблицу тегов и кнопку для удаления
        self.tag_list = QTableWidget(0, 3)
        self.tag_list.setHorizontalHeaderLabels(["Address", "Current Value", "Comment"])
        self.tag_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.delete_tag_btn = QPushButton("Удалить с графика")
        self.delete_tag_btn.clicked.connect(self.delete_selected_tag)

        # Основной макет окна
        layout = QVBoxLayout()
        layout.addWidget(self.plot_widget)
        layout.addWidget(self.tag_list)
        layout.addWidget(self.delete_tag_btn)

        # Устанавливаем центральный виджет
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def update_tag_value(self, label, current_value, comment):
        """Обновить текущее значение и комментарий для тега в таблице графиков."""
        for row in range(self.tag_list.rowCount()):
            if self.tag_list.item(row, 0).text() == label:  # Ищем тег по адресу
                # Приводим значение к целому, если это не тип REAL
                if "DWORD" in label or "WORD" in label:
                    current_value = int(current_value)  # Приведение к целому
                else:
                    current_value = float(current_value)  # Для REAL оставляем как float

                self.tag_list.setItem(row, 1, QTableWidgetItem(str(current_value)))  # Обновляем Current Value
                self.tag_list.setItem(row, 2, QTableWidgetItem(comment))  # Обновляем Comment
                break


    def clear_and_load_graph_data(self, plot_state):
        """Очищает все текущие данные с графика и загружает новые данные из plot_state."""
        print("Очистка графиков и загрузка новых данных...")  # Отладка
        self.clear_all_graph_data()  # очищаем текущие графики

        for row, column_name in plot_state:
            # Извлекаем адрес и значение из основной таблицы
            address_item = self.parent().table.item(row, 0)
            if address_item:
                address = address_item.text()
                label = f"{address} ({column_name})"

                # Проверяем, получен ли индекс столбца
                column_index = self.parent().get_column_index(column_name)
                if column_index is None:
                    print(f"Ошибка: Индекс для столбца {column_name} не найден.")  # Отладка
                    continue

                # Получаем текущее значение и комментарий
                current_value_item = self.parent().table.item(row, column_index)
                current_value = float(current_value_item.text()) if current_value_item else 0.0
                comment_item = self.parent().table.item(row, 5)
                comment = comment_item.text() if comment_item else ""

                print(
                    f"Добавление линии на график: {label} со значением {current_value} и комментарием '{comment}'")  # Отладка

                # Добавляем линию на график
                self.add_line((row, column_name), label, current_value, comment)
            else:
                print(f"Ошибка: Адрес для строки {row} не найден.")  # Отладка

    def closeEvent(self, event):
        """Обработчик закрытия окна для сохранения конфигурации графиков."""
        # if isinstance(self.parent(), MainWindow):
        self.parent().save_plot_data()
        event.accept()  # Закрываем окно

    def save_plot_data(self):
        """Сохранение текущей конфигурации графиков в файл."""
        config = {
            'plot_data': [(row, col) for row, col in self.plot_data],
        }
        with open(table_config_file, 'w') as f:
            json.dump(config, f, indent=4)

    def clear_all_graph_data(self):
        """Полностью очищает график и таблицу тегов."""
        self.plot_widget.clear()  # Удаляет все линии с графика
        self.lines.clear()  # Очищает словарь линий
        self.y_data.clear()  # Очищает данные для графика
        self.tag_list.setRowCount(0)  # Очищает таблицу тегов

    def add_line(self, key, label, current_value=0.0, comment=""):
        """Добавить линию на график и в список тегов."""
        if key not in self.lines:
            color = pg.intColor(len(self.lines), hues=10)
            line = self.plot_widget.plot(pen=color, name=label)
            self.lines[key] = line
            self.y_data[key] = np.zeros(1000)

            # Добавляем строку с адресом, текущим значением и комментарием в таблицу тегов
            row_position = self.tag_list.rowCount()
            self.tag_list.insertRow(row_position)
            self.tag_list.setItem(row_position, 0, QTableWidgetItem(label))  # Address
            self.tag_list.setItem(row_position, 1, QTableWidgetItem(str(current_value)))  # Current Value
            self.tag_list.setItem(row_position, 2, QTableWidgetItem(comment))  # Comment

    def remove_line(self, key):
        """Удалить линию с графика и из списка тегов."""
        if key in self.lines:
            self.plot_widget.removeItem(self.lines[key])
            del self.lines[key]
            del self.y_data[key]

            # Удалить тег из списка
            for row in range(self.tag_list.rowCount()):
                if self.tag_list.item(row, 0).text() == key[1]:  # Совпадение по метке
                    self.tag_list.removeRow(row)
                    break


    def delete_selected_tag(self):
        """Удалить выбранный тег из графика и списка тегов."""
        selected_row = self.tag_list.currentRow()
        if selected_row >= 0:
            tag_label = self.tag_list.item(selected_row, 0).text()
            for key in list(self.lines.keys()):
                if self.lines[key].name() == tag_label:
                    self.remove_line(key)

                    # Удаляем тег из plot_data в MainWindow
                    self.parent().remove_tag_from_plot_data(key)

                    self.tag_list.removeRow(selected_row)
                    break

    def update_line_value(self, key, new_value):
        """Обновить текущее значение для линии в таблице и на графике."""
        if key in self.lines:
            # Сдвигаем данные влево и добавляем новое значение справа
            self.y_data[key] = np.roll(self.y_data[key], -1)
            self.y_data[key][-1] = new_value
            self.lines[key].setData(np.arange(1000), self.y_data[key])

            # Обновляем значение в таблице
            for row in range(self.tag_list.rowCount()):
                if self.tag_list.item(row, 0).text() == key[1]:  # Найти нужный тег по адресу
                    self.tag_list.setItem(row, 1, QTableWidgetItem(str(new_value)))  # Обновить Current Value
                    break


    def update_line(self, key, new_value):
        """Обновить линию на графике с новыми значениями."""
        if key in self.lines:
            # Сдвигаем данные влево и добавляем новое значение справа
            self.y_data[key] = np.roll(self.y_data[key], -1)
            self.y_data[key][-1] = new_value
            self.lines[key].setData(np.arange(1000), self.y_data[key])
