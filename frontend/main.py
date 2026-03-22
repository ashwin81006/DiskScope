import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def apply_dark_theme(app):
    app.setStyleSheet("""
        QWidget {
            background-color: #181818;
            color: #eaeaea;
            font-size: 13px;
        }

        QTreeView, QTableView {
            background-color: #1f1f1f;
            alternate-background-color: #252526;
            border: none;
            gridline-color: #333;
        }
        QTreeView::item:hover, QTableView::item:hover {
    background-color: #2a2d2e;
}
        QTreeView::item, QTableView::item {
            padding: 6px;
        }

        QTreeView::item:selected, QTableView::item:selected {
            background-color: #0078d7;
            color: white;
        }

        QHeaderView::section {
            background-color: #2d2d30;
            color: #ffffff;
            padding: 6px;
            border: none;
            font-weight: bold;
        }

        QPushButton {
            background-color: #2d2d30;
            border-radius: 6px;
            padding: 6px 14px;
        }

        QPushButton:hover {
            background-color: #3e3e42;
        }

        QProgressBar {
            border: none;
            background: #2a2a2a;
            height: 6px;
        }

        QProgressBar::chunk {
            background-color: #4caf50;
            border-radius: 3px;
        }
        QTreeView::item:hover, QTableView::item:hover {
    background-color: #2a2d2e;
}
    """)


def main():
    app = QApplication(sys.argv)
    apply_dark_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()