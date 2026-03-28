from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeView, QTableView, QProgressBar,
    QFileDialog, QFileIconProvider, QLabel, QHeaderView,
    QTabWidget, QSplitter, QApplication, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QFont, QColor, QLinearGradient, QBrush, QPalette
from PyQt6.QtCore import QFileInfo, Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty
from controllers.scan_controller import ScanController
import os
import datetime
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class AnimatedButton(QPushButton):
    """Custom button with hover animations"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.opacity_value = 1.0  # Initialize here
        self.animation = QPropertyAnimation(self, b"opacity")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
    def enterEvent(self, event):
        self.animation.stop()
        self.animation.setEndValue(0.8)
        self.animation.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.animation.stop()
        self.animation.setEndValue(1.0)
        self.animation.start()
        super().leaveEvent(event)
        
    def get_opacity(self):
        return self.opacity_value
        
    def set_opacity(self, value):
        self.opacity_value = value
        self.setGraphicsEffect(None)
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(10)
        effect.setColor(QColor(0, 120, 215, int(value * 100)))
        effect.setOffset(0, 0)
        self.setGraphicsEffect(effect)
        
    opacity = pyqtProperty(float, get_opacity, set_opacity)

class ModernProgressBar(QProgressBar):
    """Custom progress bar with gradient"""
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
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
        """)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DiscScope - Advanced Disk Analyzer")
        self.resize(1400, 800)
        
        # Set window transparency and effects
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Apply modern window frame
        self.setStyleSheet("""
            QMainWindow {
                background-color: rgba(24, 24, 28, 0.95);
                border-radius: 12px;
            }
        """)
        
        # Create central widget with rounded corners
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        central_widget.setStyleSheet("""
            #CentralWidget {
                background-color: rgba(24, 24, 28, 0.98);
                border-radius: 12px;
            }
        """)
        self.setCentralWidget(central_widget)

        self.icon_provider = QFileIconProvider()
        self.controller = ScanController(self)

        self.last_progress = 0
        self.top_files_data = []

        # For batch loading
        self._batch_timer = None
        self._batch_parent = None
        self._batch_children = None
        self._batch_index = 0
        self._batch_size = 100

        self._batch_table_timer = None
        self._batch_table_children = None
        self._batch_table_index = 0
        
        # Animation timers
        self.glow_timer = QTimer()
        self.glow_value = 0
        self.glow_direction = 1
        self.btn_select = None  # Initialize before _setup_ui

        self._setup_ui()
        self._setup_animations()

    def _setup_animations(self):
        """Setup UI animations"""
        self.glow_timer.timeout.connect(self._animate_glow)
        self.glow_timer.start(50)
        
    def _animate_glow(self):
        """Animate glow effect on buttons"""
        self.glow_value += 0.05 * self.glow_direction
        if self.glow_value >= 1.0:
            self.glow_value = 1.0
            self.glow_direction = -1
        elif self.glow_value <= 0.2:
            self.glow_value = 0.2
            self.glow_direction = 1
            
        # Update button styles only if button exists
        if hasattr(self, 'btn_select') and self.btn_select:
            self.btn_select.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #2d2d30, stop:0.5 #3e3e42, stop:1 #2d2d30);
                    border: 1px solid rgba(0, 120, 215, {0.3 + self.glow_value * 0.4});
                    border-radius: 8px;
                    padding: 10px 24px;
                    font-weight: bold;
                    font-size: 14px;
                    color: #ffffff;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #3e3e42, stop:0.5 #4e4e52, stop:1 #3e3e42);
                    border: 1px solid rgba(0, 120, 215, 0.8);
                }}
            """)

    def _setup_ui(self):
        central = self.centralWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Top bar with gradient
        top_bar = QHBoxLayout()
        top_bar.setSpacing(15)
        
        # Logo/Title
        title_label = QLabel("🚀 DISC SCOPE")
        title_font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("""
            color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4caf50, stop:0.5 #2196f3, stop:1 #9c27b0);
            padding: 5px;
        """)
        
        self.btn_select = AnimatedButton("📁 SELECT FOLDER")
        self.btn_select.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2d2d30, stop:0.5 #3e3e42, stop:1 #2d2d30);
                border: 1px solid rgba(0, 120, 215, 0.5);
                border-radius: 8px;
                padding: 10px 24px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3e3e42, stop:0.5 #4e4e52, stop:1 #3e3e42);
                border: 1px solid #0078d7;
            }
        """)
        
        self.progress = ModernProgressBar()
        self.stats = QLabel("🎯 Ready to analyze")
        self.stats.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 12px;
                padding: 5px 12px;
                background: rgba(45, 45, 48, 0.6);
                border-radius: 6px;
            }
        """)
        
        top_bar.addWidget(title_label)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_select)
        top_bar.addWidget(self.progress)
        top_bar.addWidget(self.stats)
        
        # Content area with glass morphism effect
        content = QHBoxLayout()
        content.setSpacing(15)
        
        # Tree view with modern styling
        self.tree = QTreeView()
        self.tree.setStyleSheet("""
            QTreeView {
                background: rgba(31, 31, 35, 0.8);
                border: 1px solid rgba(68, 68, 68, 0.5);
                border-radius: 8px;
                outline: none;
            }
            QTreeView::item {
                padding: 8px;
                border-radius: 4px;
            }
            QTreeView::item:hover {
                background: rgba(0, 120, 215, 0.2);
            }
            QTreeView::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078d7, stop:1 #005a9e);
                color: white;
            }
        """)
        
        # Table view with modern styling
        self.table = QTableView()
        self.table.setStyleSheet("""
            QTableView {
                background: rgba(31, 31, 35, 0.8);
                border: 1px solid rgba(68, 68, 68, 0.5);
                border-radius: 8px;
                gridline-color: rgba(68, 68, 68, 0.3);
                outline: none;
            }
            QTableView::item {
                padding: 8px;
            }
            QTableView::item:hover {
                background: rgba(0, 120, 215, 0.2);
            }
            QTableView::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078d7, stop:1 #005a9e);
                color: white;
            }
        """)
        
        # Models
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["📁 Name", "📊 Size"])
        self.table_model = QStandardItemModel()
        self.table_model.setHorizontalHeaderLabels(
            ["📄 Name", "💾 Size", "📋 Type", "📑 Files", "📂 Folders", "🕒 Modified", "🕐 Accessed"]
        )
        
        # Set header styling
        for model in [self.tree_model, self.table_model]:
            model.setHeaderData(0, Qt.Orientation.Horizontal, QColor(200, 200, 200), Qt.ItemDataRole.ForegroundRole)
            
        self.tree.setModel(self.tree_model)
        self.table.setModel(self.table_model)
        
        # UX improvements
        self.tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.tree.setAlternatingRowColors(True)
        
        # Set column widths
        self.tree.setColumnWidth(0, 450)
        self.table.setColumnWidth(0, 350)
        self.table.horizontalHeader().setStretchLastSection(True)
        
        # Signals
        self.btn_select.clicked.connect(self.select_folder)
        self.tree.clicked.connect(self.on_tree_click)
        self.tree.expanded.connect(self.on_tree_expand)
        self.table.doubleClicked.connect(self.on_table_double_click)
        
        # Tabs with modern styling
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
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
        """)
        
        # Details tab
        details_tab = QWidget()
        details_layout = QVBoxLayout()
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.addWidget(self.table)
        details_tab.setLayout(details_layout)
        
        # Top Files tab with enhanced styling
        top_files_tab = QWidget()
        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add header for top files
        top_header = QLabel("🏆 LARGEST FILES")
        top_header.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #4caf50;
                padding: 10px;
                background: rgba(76, 175, 80, 0.1);
                border-radius: 6px;
                margin-bottom: 5px;
            }
        """)
        
        self.top_files_table = QTableView()
        self.top_files_table.setStyleSheet("""
            QTableView {
                background: rgba(31, 31, 35, 0.8);
                border: 1px solid rgba(68, 68, 68, 0.5);
                border-radius: 8px;
            }
            QTableView::item {
                padding: 8px;
            }
            QTableView::item:hover {
                background: rgba(0, 120, 215, 0.2);
            }
            QTableView::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078d7, stop:1 #005a9e);
            }
        """)
        
        self.top_files_model = QStandardItemModel()
        self.top_files_model.setHorizontalHeaderLabels(["🏷️ Name", "📊 Size", "📍 Path"])
        self.top_files_table.setModel(self.top_files_model)
        self.top_files_table.setColumnWidth(0, 300)
        self.top_files_table.setIconSize(QSize(24, 24))
        self.top_files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.top_files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.top_files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.top_files_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.top_files_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.top_files_table.setAlternatingRowColors(True)
        
        top_layout.addWidget(top_header)
        top_layout.addWidget(self.top_files_table)
        top_files_tab.setLayout(top_layout)
        
        # Chart tab with enhanced styling
        chart_tab = QWidget()
        chart_layout = QVBoxLayout()
        chart_layout.setContentsMargins(0, 0, 0, 0)
        
        chart_header = QLabel("📊 STORAGE DISTRIBUTION")
        chart_header.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2196f3;
                padding: 10px;
                background: rgba(33, 150, 243, 0.1);
                border-radius: 6px;
                margin-bottom: 5px;
            }
        """)
        
        self.figure = Figure(figsize=(8, 6), dpi=100, facecolor='#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background: transparent;")
        
        chart_layout.addWidget(chart_header)
        chart_layout.addWidget(self.canvas)
        chart_tab.setLayout(chart_layout)
        
        self.tabs.addTab(details_tab, "📋 DETAILS")
        self.tabs.addTab(top_files_tab, "🏆 TOP FILES")
        self.tabs.addTab(chart_tab, "📊 CHART")
        
        # Splitter with modern handle
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.tree)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 5)
        splitter.setHandleWidth(4)
        splitter.setSizes([450, 950])
        
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2d2d30, stop:1 #3e3e42);
                width: 2px;
                margin: 20px 0;
            }
            QSplitter::handle:hover {
                background: #0078d7;
            }
        """)
        
        content.addWidget(splitter)
        main_layout.addLayout(top_bar, 0)
        main_layout.addLayout(content, 1)
        central.setLayout(main_layout)

    def load_top_files(self):
        self.top_files_model.removeRows(0, self.top_files_model.rowCount())
        
        sorted_files = sorted(
            self.top_files_data,
            key=lambda x: x.get("size", 0),
            reverse=True
        )[:50]
        
        for idx, f in enumerate(sorted_files):
            path = f.get("path", "")
            size = f.get("size", 0)
            name = os.path.basename(path)
            
            # Add rank for top files
            rank = idx + 1
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "📄"
            display_name = f"{medal} {name}"
            
            name_item = QStandardItem(display_name)
            size_item = QStandardItem(self.format_size(size))
            path_item = QStandardItem(path)
            
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            
            is_folder = os.path.isdir(path)
            icon = self.get_icon(path, is_folder)
            name_item.setData(icon, Qt.ItemDataRole.DecorationRole)
            
            # Color coding for top 3
            if rank == 1:
                name_item.setForeground(QColor(255, 215, 0))  # Gold
            elif rank == 2:
                name_item.setForeground(QColor(192, 192, 192))  # Silver
            elif rank == 3:
                name_item.setForeground(QColor(205, 127, 50))  # Bronze
                
            self.top_files_model.appendRow([name_item, size_item, path_item])
        
        self.top_files_model.layoutChanged.emit()
        self.top_files_table.viewport().update()
        
    def format_size(self, size):
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    
    def load_chart(self, node):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        self.figure.patch.set_facecolor("#1e1e1e")
        ax.set_facecolor("#1e1e1e")
        
        children = node.get("children", [])
        if not children:
            return
        
        children = sorted(children, key=lambda x: x.get("size", 0), reverse=True)
        TOP_N = 6
        top = children[:TOP_N]
        rest = children[TOP_N:]
        
        labels, sizes = [], []
        for child in top:
            labels.append(child.get("name", ""))
            sizes.append(child.get("size", 0))
        
        if rest:
            labels.append("Others")
            sizes.append(sum(c.get("size", 0) for c in rest))
        
        colors = ["#4CAF50", "#2196F3", "#FFC107", "#E91E63", "#9C27B0", "#00BCD4", "#9E9E9E"]
        
        # Add explosion effect for largest slice
        explode = [0.05] + [0] * (len(labels) - 1) if labels else []
        
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            autopct='%1.1f%%',
            startangle=140,
            colors=colors[:len(sizes)],
            explode=explode,
            textprops={'color': 'white', 'fontsize': 10, 'weight': 'bold'},
            wedgeprops={'edgecolor': '#1e1e1e', 'linewidth': 2}
        )
        
        # Style the percentage text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
            autotext.set_weight('bold')
        
        ax.axis('equal')
        self.canvas.draw()
    
    def get_icon(self, path, is_folder=True):
        info = QFileInfo(os.path.abspath(path))
        if info.exists():
            return self.icon_provider.icon(info)
        return self.icon_provider.icon(
            QFileIconProvider.IconType.Folder if is_folder else QFileIconProvider.IconType.File
        )
    
    def get_file_times(self, path):
        try:
            stat = os.stat(path)
            return (
                datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                datetime.datetime.fromtimestamp(stat.st_atime).strftime("%Y-%m-%d %H:%M")
            )
        except:
            return "-", "-"
    
    def update_progress(self, val):
        if val < self.last_progress:
            return
        self.last_progress = val
        self.progress.setValue(val)
        if val >= 100:
            self.stats.setText("✅ Scan complete!")
    
    def update_status(self, text):
        self.stats.setText(f"🔄 {text}")
    
    def select_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path:
            print("[UI] Selected folder:", path)
            self.tree_model.removeRows(0, self.tree_model.rowCount())
            self.table_model.removeRows(0, self.table_model.rowCount())
            self.progress.setValue(0)
            self.last_progress = 0
            self.update_status("Scanning...")
            self.controller.start_scan(path)
    
    def build_path_map(self, node):
        self.path_map[node["path"]] = node
        for child in node.get("children", []):
            self.build_path_map(child)
    
    def load_data(self, data):
        self.tree_model.removeRows(0, self.tree_model.rowCount())
        self.top_files_data = data.get("largest_files", [])
        root = data.get("tree", {})
        
        self.full_data = root
        self.path_map = {}
        self.build_path_map(root)
        
        root_item = QStandardItem(root.get("name", ""))
        root_item.setData(root)
        root_item.setIcon(self.get_icon(root.get("path", ""), True))
        size_item = QStandardItem(self.format_size(root.get("size", 0)))
        self.tree_model.appendRow([root_item, size_item])
        
        if root.get("children"):
            dummy = QStandardItem("Loading...")
            root_item.appendRow([dummy, QStandardItem("")])
        
        info = data.get("scan_info", {})
        
        self.stats.setText(
            f"📊 Size: {self.format_size(info.get('size',0))}   "
            f"📁 Folders: {info.get('dirs',0)}   "
            f"📄 Files: {info.get('files',0)}"
        )
        
        self.load_top_files()
        self.load_chart(root)
        print("[UI] load_data finished")
    
    def on_tree_expand(self, index):
        item = self.tree_model.itemFromIndex(index)
        node = item.data()
        if not node:
            return
        
        if item.rowCount() > 0:
            first_child = item.child(0, 0)
            if first_child and first_child.text() == "Loading...":
                item.removeRows(0, item.rowCount())
            else:
                return
        
        real_node = self.path_map.get(node.get("path"))
        if not real_node:
            return
        
        children = real_node.get("children", [])
        if not children:
            return
        
        self._batch_load_tree_children(item, children)
    
    def _batch_load_tree_children(self, parent_item, children):
        self._batch_parent = parent_item
        self._batch_children = children
        self._batch_index = 0
        if self._batch_timer:
            self._batch_timer.stop()
        self._batch_timer = QTimer()
        self._batch_timer.timeout.connect(self._process_next_tree_batch)
        self._batch_timer.start(10)
    
    def _process_next_tree_batch(self):
        start = self._batch_index
        end = min(start + self._batch_size, len(self._batch_children))
        for i in range(start, end):
            child = self._batch_children[i]
            name_item = QStandardItem(child.get("name", ""))
            name_item.setData(child)
            size_item = QStandardItem(self.format_size(child.get("size", 0)))
            is_folder = child.get("dirs", 0) > 0 or child.get("children")
            name_item.setIcon(self.get_icon(child.get("path", ""), is_folder))
            
            if child.get("children"):
                dummy = QStandardItem("Loading...")
                dummy.setData(None)
                name_item.appendRow([dummy, QStandardItem("")])
            
            self._batch_parent.appendRow([name_item, size_item])
            QApplication.processEvents()
        
        self._batch_index = end
        if self._batch_index >= len(self._batch_children):
            self._batch_timer.stop()
            self._batch_parent = None
            self._batch_children = None
    
    def load_children(self, node):
        self.table_model.removeRows(0, self.table_model.rowCount())
        MAX_ITEMS = 500
        
        real_node = self.path_map.get(node.get("path"))
        if not real_node:
            return
        
        children = real_node.get("children", [])
        if len(children) > MAX_ITEMS:
            print(f"[UI] Limiting children: {len(children)} → {MAX_ITEMS}")
            children = children[:MAX_ITEMS]
        if not children:
            return
        self._batch_load_table_children(children)
    
    def _batch_load_table_children(self, children):
        self._batch_table_children = children
        self._batch_table_index = 0
        if self._batch_table_timer:
            self._batch_table_timer.stop()
        self._batch_table_timer = QTimer()
        self._batch_table_timer.timeout.connect(self._process_next_table_batch)
        self._batch_table_timer.start(10)
    
    def _process_next_table_batch(self):
        start = self._batch_table_index
        end = min(start + self._batch_size, len(self._batch_table_children))
        for i in range(start, end):
            child = self._batch_table_children[i]
            is_folder = child.get("dirs", 0) > 0 or child.get("children")
            
            name = QStandardItem(child.get("name", ""))
            name.setData(child)
            size = QStandardItem(self.format_size(child.get("size", 0)))
            type_item = QStandardItem("📁 Folder" if is_folder else "📄 File")
            files = QStandardItem(str(child.get("files", 0) if is_folder else 1))
            dirs = QStandardItem(str(child.get("dirs", 0) if is_folder else 0))
            modified, accessed = self.get_file_times(child.get("path", ""))
            name.setIcon(self.get_icon(child.get("path", ""), is_folder))
            
            self.table_model.appendRow([
                name, size, type_item, files, dirs,
                QStandardItem(modified), QStandardItem(accessed)
            ])
        
        self._batch_table_index = end
        if self._batch_table_index >= len(self._batch_table_children):
            self._batch_table_timer.stop()
            self._batch_table_children = None
    
    def on_tree_click(self, index):
        item = self.tree_model.itemFromIndex(index)
        node = item.data()
        if not node:
            return
        
        if node.get("dirs", 0) == 0 and node.get("files", 0) == 0:
            self.table_model.removeRows(0, self.table_model.rowCount())
            modified, accessed = self.get_file_times(node.get("path", ""))
            
            name = QStandardItem(node.get("name", ""))
            name.setData(node)
            name.setIcon(self.get_icon(node.get("path", ""), False))
            
            self.table_model.appendRow([
                name,
                QStandardItem(self.format_size(node.get("size", 0))),
                QStandardItem("📄 File"),
                QStandardItem("1"),
                QStandardItem("0"),
                QStandardItem(modified),
                QStandardItem(accessed)
            ])
            return
        
        QTimer.singleShot(0, lambda: self.load_children(node))
    
    def expand_tree_to_path(self, target_path):
        def match(item):
            node = item.data()
            if node and node.get("path") == target_path:
                return item
            for i in range(item.rowCount()):
                res = match(item.child(i, 0))
                if res:
                    return res
            return None
        
        root = self.tree_model.invisibleRootItem()
        for i in range(root.rowCount()):
            item = root.child(i, 0)
            found = match(item)
            if found:
                index = self.tree_model.indexFromItem(found)
                parent = index
                while parent.isValid():
                    self.tree.expand(parent)
                    parent = parent.parent()
                self.tree.setCurrentIndex(index)
                self.tree.scrollTo(index)
                break
    
    def on_table_double_click(self, index):
        item = self.table_model.itemFromIndex(index)
        node = item.data()
        if not node:
            return
        
        path = node.get("path", "")
        is_folder = node.get("dirs", 0) > 0 or node.get("children")
        
        if is_folder:
            self.load_children(node)
            self.expand_tree_to_path(path)
        else:
            os.startfile(path)