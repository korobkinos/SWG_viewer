import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("app_icon.ico"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
