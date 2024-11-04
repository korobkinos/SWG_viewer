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
        self.tag_list = QTableWidget(0, 1)
        self.tag_list.setHorizontalHeaderLabels(["Теги на графике"])
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
        # if isinstance(self.parent(), MainWindow):
        self.parent().plot_data.clear()  # Полностью очищает plot_data

    def add_line(self, key, label):
        """Добавить линию на график и в список тегов."""
        if key not in self.lines:
            color = pg.intColor(len(self.lines), hues=10)
            line = self.plot_widget.plot(pen=color, name=label)
            self.lines[key] = line
            self.y_data[key] = np.zeros(1000)

            # Добавляем тег в список
            row_position = self.tag_list.rowCount()
            self.tag_list.insertRow(row_position)
            self.tag_list.setItem(row_position, 0, QTableWidgetItem(label))

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
                    # if isinstance(self.parent(), MainWindow):
                    self.parent().remove_tag_from_plot_data(key)

                    self.tag_list.removeRow(selected_row)
                    break

    def update_line(self, key, new_value):
        """Обновить линию на графике с новыми значениями."""
        if key in self.lines:
            # Сдвигаем данные влево и добавляем новое значение справа
            self.y_data[key] = np.roll(self.y_data[key], -1)
            self.y_data[key][-1] = new_value
            self.lines[key].setData(np.arange(1000), self.y_data[key])
