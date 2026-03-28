import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def apply_dark_theme(app):
    app.setStyleSheet("""
        /* Global Styles */
        QWidget {
            background-color: #181818;
            color: #eaeaea;
            font-size: 13px;
            font-family: "Segoe UI", "Microsoft YaHei", "WenQuanYi Micro Hei", sans-serif;
        }

        /* Tree and Table Views */
        QTreeView, QTableView {
            background-color: #1f1f1f;
            alternate-background-color: #252526;
            border: none;
            gridline-color: #333;
            selection-background-color: #0078d7;
            selection-color: white;
            outline: none;
        }
        
        QTreeView::item, QTableView::item {
            padding: 8px;
            border-radius: 4px;
        }
        
        QTreeView::item:hover, QTableView::item:hover {
            background-color: rgba(0, 120, 215, 0.2);
        }
        
        QTreeView::item:selected, QTableView::item:selected {
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #0078d7, stop:1 #005a9e);
            color: white;
        }

        /* Header Styles */
        QHeaderView::section {
            background-color: #2d2d30;
            color: #ffffff;
            padding: 8px;
            border: none;
            font-weight: bold;
            font-size: 12px;
        }
        
        QHeaderView::section:hover {
            background-color: #3e3e42;
        }

        /* Scrollbars */
        QScrollBar:vertical {
            background: #2a2a2a;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4caf50, stop:1 #2196f3);
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #5cb85c, stop:1 #42a5f5);
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }
        
        QScrollBar:horizontal {
            background: #2a2a2a;
            height: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4caf50, stop:1 #2196f3);
            border-radius: 6px;
            min-width: 20px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #5cb85c, stop:1 #42a5f5);
        }

        /* Status Bar */
        QStatusBar {
            background-color: #2d2d30;
            color: #888;
            padding: 4px;
        }
        
        /* Tool Tips */
        QToolTip {
            background-color: #2d2d30;
            color: #eaeaea;
            border: 1px solid #0078d7;
            padding: 5px;
            border-radius: 4px;
        }
        
        /* Menu Bar */
        QMenuBar {
            background-color: #2d2d30;
            color: #eaeaea;
        }
        
        QMenuBar::item:selected {
            background-color: #0078d7;
        }
        
        QMenu {
            background-color: #2d2d30;
            color: #eaeaea;
            border: 1px solid #444;
        }
        
        QMenu::item:selected {
            background-color: #0078d7;
        }
        
        /* Tab Widget */
        QTabWidget::pane {
            background: transparent;
            border: none;
        }
        
        QTabBar::tab {
            background: rgba(45, 45, 48, 0.6);
            color: #aaa;
            padding: 10px 24px;
            margin-right: 2px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-weight: bold;
        }
        
        QTabBar::tab:selected {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #0078d7, stop:1 #005a9e);
            color: white;
        }
        
        QTabBar::tab:hover:!selected {
            background: rgba(0, 120, 215, 0.3);
            color: white;
        }
        
        /* Progress Bar */
        QProgressBar {
            border: none;
            background: rgba(42, 42, 46, 0.6);
            height: 4px;
            border-radius: 2px;
        }
        
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4caf50, stop:0.5 #2196f3, stop:1 #9c27b0);
            border-radius: 2px;
        }
        
        /* Line Edits */
        QLineEdit {
            background-color: #2d2d30;
            border: 1px solid #444;
            border-radius: 4px;
            padding: 6px;
            color: #eaeaea;
        }
        
        QLineEdit:focus {
            border-color: #0078d7;
        }
        
        /* Combo Box */
        QComboBox {
            background-color: #2d2d30;
            border: 1px solid #444;
            border-radius: 4px;
            padding: 6px;
            color: #eaeaea;
        }
        
        QComboBox::drop-down {
            border: none;
        }
        
        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 4px solid #eaeaea;
            margin-right: 4px;
        }
        
        /* Check Box */
        QCheckBox {
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border-radius: 3px;
            background-color: #2d2d30;
            border: 1px solid #444;
        }
        
        QCheckBox::indicator:checked {
            background-color: #0078d7;
            border-color: #0078d7;
        }
        
        /* Radio Button */
        QRadioButton {
            spacing: 8px;
        }
        
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border-radius: 8px;
            background-color: #2d2d30;
            border: 1px solid #444;
        }
        
        QRadioButton::indicator:checked {
            background-color: #0078d7;
            border-color: #0078d7;
        }
        
        /* Group Box */
        QGroupBox {
            border: 1px solid #444;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        
        /* Splitter */
        QSplitter::handle {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #2d2d30, stop:1 #3e3e42);
            width: 2px;
            margin: 20px 0;
        }
        
        QSplitter::handle:hover {
            background: #0078d7;
        }
        
        /* Animation for loading states */
        @keyframes pulse {
            0% { opacity: 0.6; }
            50% { opacity: 1; }
            100% { opacity: 0.6; }
        }
        
        QLabel[loading="true"] {
            animation: pulse 1.5s ease-in-out infinite;
        }
    """)


def main():
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    
    # Set application metadata
    app.setApplicationName("DiscScope")
    app.setApplicationDisplayName("DiscScope - Advanced Disk Analyzer")
    app.setApplicationVersion("2.0.0")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Center window on screen
    screen = app.primaryScreen().geometry()
    window_geometry = window.geometry()
    x = (screen.width() - window_geometry.width()) // 2
    y = (screen.height() - window_geometry.height()) // 2
    window.move(x, y)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()