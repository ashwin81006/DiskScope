from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeView, QTableView, QProgressBar,
    QFileDialog, QFileIconProvider, QLabel, QHeaderView,
    QTabWidget, QSplitter, QApplication, QGraphicsBlurEffect,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QFrame,
    QMessageBox
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QFont, QColor, QLinearGradient, QBrush, QPalette
from PyQt6.QtCore import QFileInfo, Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty
from controllers.scan_controller import ScanController
import os
import datetime
import traceback
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.patches as mpatches

class AnimatedButton(QPushButton):
    """Custom button with hover animations"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.opacity_value = 1.0
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_animation.setDuration(200)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
    def enterEvent(self, event):
        self.opacity_animation.stop()
        self.opacity_animation.setEndValue(0.8)
        self.opacity_animation.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.opacity_animation.stop()
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.start()
        super().leaveEvent(event)

class ModernProgressBar(QProgressBar):
    """Custom progress bar with animation"""
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #2a2a2a;
                height: 4px;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4caf50, stop:0.5 #2196f3, stop:1 #9c27b0);
                border-radius: 2px;
            }
        """)
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setDuration(500)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
    def setValue(self, value):
        self.animation.stop()
        self.animation.setEndValue(value)
        self.animation.start()

class InteractiveChart:
    """Class to handle interactive chart with animations"""
    def __init__(self, figure, canvas, main_window):
        self.figure = figure
        self.canvas = canvas
        self.main_window = main_window
        self.current_data = None
        self.selected_wedge = None
        self.pick_connected = False
        
    def create_chart(self, node):
        """Create interactive pie chart"""
        try:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            self.figure.patch.set_facecolor("#1e1e1e")
            ax.set_facecolor("#1e1e1e")
            
            self.current_data = node
            
            # Check if node has children
            if not node or not node.get("children"):
                # Show a message if no children
                ax.text(0.5, 0.5, "No data available\nClick on a folder in the tree", 
                       ha='center', va='center', color='white', fontsize=12, transform=ax.transAxes)
                ax.axis('off')
                self.canvas.draw()
                return
            
            children = node.get("children", [])
            if not children:
                ax.text(0.5, 0.5, "No data available\nClick on a folder in the tree", 
                       ha='center', va='center', color='white', fontsize=12, transform=ax.transAxes)
                ax.axis('off')
                self.canvas.draw()
                return
            
            # Sort by size
            children = sorted(children, key=lambda x: x.get("size", 0), reverse=True)
            TOP_N = 6
            top = children[:TOP_N]
            rest = children[TOP_N:]
            
            self.labels = []
            self.sizes = []
            self.node_data = []  # Store node data for each segment
            
            for child in top:
                self.labels.append(child.get("name", "Unknown"))
                self.sizes.append(child.get("size", 0))
                self.node_data.append(child)
            
            if rest:
                self.labels.append("Others")
                rest_size = sum(c.get("size", 0) for c in rest)
                self.sizes.append(rest_size)
                self.node_data.append({
                    "name": "Others", 
                    "children": rest, 
                    "size": rest_size,
                    "is_others": True
                })
            
            colors = ["#4CAF50", "#2196F3", "#FFC107", "#E91E63", "#9C27B0", "#00BCD4", "#9E9E9E"]
            
            # Create pie chart with clickable wedges
            self.wedges, self.texts, self.autotexts = ax.pie(
                self.sizes,
                labels=self.labels,
                autopct='%1.1f%%',
                startangle=140,
                colors=colors[:len(self.sizes)],
                textprops={'color': 'white', 'fontsize': 10, 'weight': 'bold'},
                wedgeprops={'edgecolor': '#1e1e1e', 'linewidth': 2}
            )
            
            # Make wedges clickable
            for i, wedge in enumerate(self.wedges):
                wedge.set_picker(True)
                wedge.set_pickradius(5)
                # Store data in wedge for later use
                wedge.node_data = self.node_data[i] if i < len(self.node_data) else None
                wedge.label_text = self.labels[i] if i < len(self.labels) else ""
                wedge.index = i
            
            # Connect click event (only once)
            if not self.pick_connected:
                self.canvas.mpl_connect('pick_event', self.on_pick)
                self.pick_connected = True
            
            # Style the percentage text
            for autotext in self.autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(10)
                autotext.set_weight('bold')
            
            # Add instruction text
            ax.text(0.5, -0.1, "Click on any segment to see details", 
                   ha='center', va='center', color='#888', fontsize=9, transform=ax.transAxes)
            
            ax.axis('equal')
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error creating chart: {e}")
            traceback.print_exc()
    
    def on_pick(self, event):
        """Handle click on pie chart wedge"""
        try:
            if event.artist not in self.wedges:
                return
            
            wedge = event.artist
            if not hasattr(wedge, 'node_data') or not wedge.node_data:
                return
            
            # Animate the wedge (expand effect)
            self.animate_wedge(wedge)
            
            # Show details in a new tab
            node_data = wedge.node_data
            label = wedge.label_text
            
            # Create a details tab
            self.main_window.create_details_tab(label, node_data)
            
        except Exception as e:
            print(f"Error handling pick event: {e}")
            traceback.print_exc()
    
    def animate_wedge(self, wedge):
        """Animate wedge expansion"""
        try:
            # Store original properties
            original_radius = wedge.get_radius()
            original_linewidth = wedge.get_linewidth()
            original_edgecolor = wedge.get_edgecolor()
            
            # Temporarily expand the wedge
            wedge.set_radius(original_radius + 0.05)
            wedge.set_linewidth(3)
            wedge.set_edgecolor('gold')
            self.canvas.draw_idle()
            
            # Reset after animation
            QTimer.singleShot(200, lambda: self.reset_wedge(wedge, original_radius, original_linewidth, original_edgecolor))
        except Exception as e:
            print(f"Error animating wedge: {e}")
    
    def reset_wedge(self, wedge, original_radius, original_linewidth, original_edgecolor):
        """Reset wedge to original state"""
        try:
            wedge.set_radius(original_radius)
            wedge.set_linewidth(original_linewidth)
            wedge.set_edgecolor(original_edgecolor)
            self.canvas.draw_idle()
        except Exception as e:
            print(f"Error resetting wedge: {e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DiscScope - Advanced Disk Analyzer")
        self.resize(1400, 800)
        
        # Set solid background for main window
        self.setStyleSheet("""
            QMainWindow {
                background-color: #181818;
            }
        """)
        
        # Create central widget with solid background
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        central_widget.setStyleSheet("""
            #CentralWidget {
                background-color: #181818;
            }
        """)
        self.setCentralWidget(central_widget)

        self.icon_provider = QFileIconProvider()
        self.controller = ScanController(self)

        self.last_progress = 0
        self.top_files_data = []
        self.details_tabs = {}  # Store details tabs to avoid duplicates
        self.path_map = {}  # Initialize path_map

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
        self.btn_select = None

        self._setup_ui()
        self._setup_animations()
        
        # Initialize interactive chart
        self.chart = None

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
            
        # Update button styles
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

    def create_details_tab(self, title, node_data):
        """Create a new tab with details about the clicked segment"""
        try:
            # Generate unique tab name
            tab_name = f"{title}_Details"
            if tab_name in self.details_tabs:
                # If tab already exists, just switch to it
                index = self.details_tabs[tab_name]
                self.tabs.setCurrentIndex(index)
                return
            
            # Create new tab widget
            details_tab = QWidget()
            details_tab.setStyleSheet("""
                QWidget {
                    background: rgba(31, 31, 35, 0.85);
                    border-radius: 8px;
                }
            """)
            
            layout = QVBoxLayout()
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)
            
            # Header with title and size
            header_frame = QFrame()
            header_frame.setStyleSheet("""
                QFrame {
                    background: rgba(0, 120, 215, 0.2);
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
            header_layout = QHBoxLayout()
            
            title_label = QLabel(f"<h2>{title}</h2>")
            title_label.setStyleSheet("color: #4caf50;")
            
            size_label = QLabel(f"<b>Total Size:</b> {self.format_size(node_data.get('size', 0))}")
            size_label.setStyleSheet("color: #2196f3; font-size: 14px;")
            
            header_layout.addWidget(title_label)
            header_layout.addStretch()
            header_layout.addWidget(size_label)
            header_frame.setLayout(header_layout)
            layout.addWidget(header_frame)
            
            # Table for showing contents
            table = QTableView()
            table.setStyleSheet("""
                QTableView {
                    background: rgba(31, 31, 35, 0.85);
                    border: 1px solid rgba(68, 68, 68, 0.3);
                    border-radius: 8px;
                    gridline-color: #333;
                }
                QTableView::item {
                    padding: 8px;
                }
                QTableView::item:hover {
                    background: rgba(0, 120, 215, 0.2);
                }
                QTableView::item:selected {
                    background: #0078d7;
                    color: white;
                }
            """)
            
            # Create model for the table
            model = QStandardItemModel()
            
            # Populate data based on node type
            if node_data.get("is_others") and node_data.get("children"):
                model.setHorizontalHeaderLabels(["Name", "Size", "Type", "Files", "Folders"])
                children = node_data.get("children", [])
                for child in sorted(children, key=lambda x: x.get("size", 0), reverse=True)[:100]:
                    is_folder = child.get("children") or child.get("dirs", 0) > 0
                    name_item = QStandardItem(child.get("name", "Unknown"))
                    icon = self.get_icon(child.get("path", ""), is_folder)
                    name_item.setIcon(icon)
                    size_item = QStandardItem(self.format_size(child.get("size", 0)))
                    type_item = QStandardItem("Folder" if is_folder else "File")
                    files_item = QStandardItem(str(child.get("files", 0) if is_folder else 1))
                    dirs_item = QStandardItem(str(child.get("dirs", 0) if is_folder else 0))
                    
                    model.appendRow([name_item, size_item, type_item, files_item, dirs_item])
            
            elif node_data.get("children"):
                model.setHorizontalHeaderLabels(["Name", "Size", "Type", "Files", "Folders"])
                children = node_data.get("children", [])
                for child in sorted(children, key=lambda x: x.get("size", 0), reverse=True)[:100]:
                    is_folder = child.get("children") or child.get("dirs", 0) > 0
                    name_item = QStandardItem(child.get("name", "Unknown"))
                    icon = self.get_icon(child.get("path", ""), is_folder)
                    name_item.setIcon(icon)
                    size_item = QStandardItem(self.format_size(child.get("size", 0)))
                    type_item = QStandardItem("Folder" if is_folder else "File")
                    files_item = QStandardItem(str(child.get("files", 0) if is_folder else 1))
                    dirs_item = QStandardItem(str(child.get("dirs", 0) if is_folder else 0))
                    
                    model.appendRow([name_item, size_item, type_item, files_item, dirs_item])
            else:
                model.setHorizontalHeaderLabels(["Name", "Size", "Type", "Modified", "Accessed"])
                path = node_data.get("path", "")
                modified, accessed = self.get_file_times(path)
                
                name_item = QStandardItem(node_data.get("name", "Unknown"))
                icon = self.get_icon(path, False)
                name_item.setIcon(icon)
                size_item = QStandardItem(self.format_size(node_data.get("size", 0)))
                type_item = QStandardItem("File")
                modified_item = QStandardItem(modified)
                accessed_item = QStandardItem(accessed)
                
                model.appendRow([name_item, size_item, type_item, modified_item, accessed_item])
            
            table.setModel(model)
            
            # Adjust column widths
            table.setColumnWidth(0, 300)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setStretchLastSection(True)
            
            # Add close button
            close_btn = QPushButton("Close Tab")
            close_btn.setStyleSheet("""
                QPushButton {
                    background: #d32f2f;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #b71c1c;
                }
            """)
            
            # Store tab info for closing
            close_btn.clicked.connect(lambda: self.close_details_tab(tab_name))
            
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            button_layout.addWidget(close_btn)
            
            layout.addWidget(table)
            layout.addLayout(button_layout)
            details_tab.setLayout(layout)
            
            # Add the tab
            index = self.tabs.addTab(details_tab, f"📊 {title}")
            self.tabs.setCurrentIndex(index)
            
            # Store reference
            self.details_tabs[tab_name] = index
            
        except Exception as e:
            print(f"Error creating details tab: {e}")
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"Could not create details tab: {str(e)}")
    
    def close_details_tab(self, tab_name):
        """Close a details tab"""
        try:
            if tab_name in self.details_tabs:
                index = self.details_tabs[tab_name]
                self.tabs.removeTab(index)
                del self.details_tabs[tab_name]
                
                # Update indices for remaining tabs
                new_dict = {}
                for name, idx in self.details_tabs.items():
                    if idx > index:
                        new_dict[name] = idx - 1
                    else:
                        new_dict[name] = idx
                self.details_tabs = new_dict
        except Exception as e:
            print(f"Error closing tab: {e}")

    def _setup_ui(self):
        central = self.centralWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Top bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(15)
        
        # Logo/Title
        title_label = QLabel("DISC SCOPE")
        title_font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("""
            color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4caf50, stop:0.5 #2196f3, stop:1 #9c27b0);
            padding: 5px;
        """)
        
        self.btn_select = AnimatedButton("SELECT FOLDER")
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
        self.stats = QLabel("Ready to analyze")
        self.stats.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 12px;
                padding: 5px 12px;
                background: #2d2d30;
                border-radius: 6px;
            }
        """)
        
        top_bar.addWidget(title_label)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_select)
        top_bar.addWidget(self.progress)
        top_bar.addWidget(self.stats)
        
        # Content area
        content = QHBoxLayout()
        content.setSpacing(15)
        
        # Tree view with solid background
        self.tree = QTreeView()
        self.tree.setStyleSheet("""
            QTreeView {
                background-color: #1f1f1f;
                border: 1px solid #333;
                border-radius: 8px;
                outline: none;
            }
            QTreeView::item {
                padding: 8px;
                border-radius: 4px;
            }
            QTreeView::item:hover {
                background-color: rgba(0, 120, 215, 0.2);
            }
            QTreeView::item:selected {
                background-color: #0078d7;
                color: white;
            }
        """)
        
        # Table view with solid background
        self.table = QTableView()
        self.table.setStyleSheet("""
            QTableView {
                background-color: #1f1f1f;
                border: 1px solid #333;
                border-radius: 8px;
                gridline-color: #333;
                outline: none;
            }
            QTableView::item {
                padding: 8px;
            }
            QTableView::item:hover {
                background-color: rgba(0, 120, 215, 0.2);
            }
            QTableView::item:selected {
                background-color: #0078d7;
                color: white;
            }
        """)
        
        # Models
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Name", "Size"])
        self.table_model = QStandardItemModel()
        self.table_model.setHorizontalHeaderLabels(
            ["Name", "Size", "Type", "Files", "Folders", "Modified", "Accessed"]
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
                background: #2d2d30;
                color: #aaa;
                padding: 10px 24px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #0078d7;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background: #3e3e42;
                color: white;
            }
        """)
        
        # Details tab with glass effect
        details_tab = QWidget()
        details_tab.setStyleSheet("""
            QWidget {
                background: rgba(31, 31, 35, 0.85);
                border-radius: 8px;
            }
        """)
        details_layout = QVBoxLayout()
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create glass container for table
        glass_container = QFrame()
        glass_container.setStyleSheet("""
            QFrame {
                background: rgba(31, 31, 35, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
            }
        """)
        glass_layout = QVBoxLayout()
        glass_layout.setContentsMargins(1, 1, 1, 1)
        glass_layout.addWidget(self.table)
        glass_container.setLayout(glass_layout)
        
        details_layout.addWidget(glass_container)
        details_tab.setLayout(details_layout)
        
        # Top Files tab with glass effect
        top_files_tab = QWidget()
        top_files_tab.setStyleSheet("""
            QWidget {
                background: rgba(31, 31, 35, 0.85);
                border-radius: 8px;
            }
        """)
        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add header for top files
        top_header = QLabel("LARGEST FILES")
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
                background: rgba(31, 31, 35, 0.85);
                border: 1px solid rgba(68, 68, 68, 0.3);
                border-radius: 8px;
            }
            QTableView::item {
                padding: 8px;
            }
            QTableView::item:hover {
                background: rgba(0, 120, 215, 0.2);
            }
            QTableView::item:selected {
                background: #0078d7;
                color: white;
            }
        """)
        
        self.top_files_model = QStandardItemModel()
        self.top_files_model.setHorizontalHeaderLabels(["Name", "Size", "Path"])
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
        
        # Create glass container for top files table
        glass_container2 = QFrame()
        glass_container2.setStyleSheet("""
            QFrame {
                background: rgba(31, 31, 35, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
            }
        """)
        glass_layout2 = QVBoxLayout()
        glass_layout2.setContentsMargins(1, 1, 1, 1)
        glass_layout2.addWidget(self.top_files_table)
        glass_container2.setLayout(glass_layout2)
        
        top_layout.addWidget(glass_container2)
        top_files_tab.setLayout(top_layout)
        
        # Chart tab with interactive chart
        chart_tab = QWidget()
        chart_tab.setStyleSheet("""
            QWidget {
                background: rgba(31, 31, 35, 0.85);
                border-radius: 8px;
            }
        """)
        chart_layout = QVBoxLayout()
        chart_layout.setContentsMargins(0, 0, 0, 0)
        
        chart_header = QLabel("STORAGE DISTRIBUTION - Click on any segment to see details")
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
        
        # Create glass container for chart
        glass_container3 = QFrame()
        glass_container3.setStyleSheet("""
            QFrame {
                background: rgba(31, 31, 35, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
            }
        """)
        glass_layout3 = QVBoxLayout()
        glass_layout3.setContentsMargins(1, 1, 1, 1)
        glass_layout3.addWidget(self.canvas)
        glass_container3.setLayout(glass_layout3)
        
        chart_layout.addWidget(chart_header)
        chart_layout.addWidget(glass_container3)
        chart_tab.setLayout(chart_layout)
        
        self.tabs.addTab(details_tab, "DETAILS")
        self.tabs.addTab(top_files_tab, "TOP FILES")
        self.tabs.addTab(chart_tab, "CHART")
        
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
                background: #2d2d30;
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
        try:
            self.top_files_model.removeRows(0, self.top_files_model.rowCount())
            
            sorted_files = sorted(
                self.top_files_data,
                key=lambda x: x.get("size", 0),
                reverse=True
            )[:50]
            
            for idx, f in enumerate(sorted_files):
                path = f.get("path", "")
                size = f.get("size", 0)
                name = os.path.basename(path) if path else "Unknown"
                
                # Add rank for top files
                rank = idx + 1
                rank_text = f"#{rank}" if rank <= 3 else f"{rank}."
                display_name = f"{rank_text} {name}"
                
                name_item = QStandardItem(display_name)
                size_item = QStandardItem(self.format_size(size))
                path_item = QStandardItem(path)
                
                size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                
                is_folder = os.path.isdir(path) if path else False
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
        except Exception as e:
            print(f"Error loading top files: {e}")
            traceback.print_exc()
        
    def format_size(self, size):
        try:
            for unit in ["B", "KB", "MB", "GB", "TB"]:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} PB"
        except:
            return "0 B"
    
    def load_chart(self, node):
        """Load interactive chart with clickable segments"""
        try:
            if not self.chart:
                self.chart = InteractiveChart(self.figure, self.canvas, self)
            self.chart.create_chart(node)
        except Exception as e:
            print(f"Error loading chart: {e}")
            traceback.print_exc()
    
    def get_icon(self, path, is_folder=True):
        try:
            if path and os.path.exists(path):
                info = QFileInfo(os.path.abspath(path))
                if info.exists():
                    return self.icon_provider.icon(info)
            return self.icon_provider.icon(
                QFileIconProvider.IconType.Folder if is_folder else QFileIconProvider.IconType.File
            )
        except:
            return self.icon_provider.icon(QFileIconProvider.IconType.File)
    
    def get_file_times(self, path):
        try:
            if path and os.path.exists(path):
                stat = os.stat(path)
                return (
                    datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    datetime.datetime.fromtimestamp(stat.st_atime).strftime("%Y-%m-%d %H:%M")
                )
            return "-", "-"
        except:
            return "-", "-"
    
    def update_progress(self, val):
        if val < self.last_progress:
            return
        self.last_progress = val
        self.progress.setValue(val)
        if val >= 100:
            self.stats.setText("Scan complete!")
    
    def update_status(self, text):
        self.stats.setText(f"Processing: {text}")
    
    def select_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path:
            print("[UI] Selected folder:", path)
            self.tree_model.removeRows(0, self.tree_model.rowCount())
            self.table_model.removeRows(0, self.table_model.rowCount())
            self.progress.setValue(0)
            self.last_progress = 0
            self.update_status("Scanning...")
            try:
                self.controller.start_scan(path)
            except Exception as e:
                print(f"Error starting scan: {e}")
                traceback.print_exc()
                self.update_status("Error starting scan")
    
    def build_path_map(self, node):
        try:
            if node and "path" in node:
                self.path_map[node["path"]] = node
                for child in node.get("children", []):
                    self.build_path_map(child)
        except Exception as e:
            print(f"Error building path map: {e}")
    
    def load_data(self, data):
        try:
            self.tree_model.removeRows(0, self.tree_model.rowCount())
            self.top_files_data = data.get("largest_files", [])
            root = data.get("tree", {})
            
            if not root:
                print("No tree data found")
                return
            
            self.full_data = root
            self.path_map = {}
            self.build_path_map(root)
            
            root_item = QStandardItem(root.get("name", "Root"))
            root_item.setData(root)
            root_item.setIcon(self.get_icon(root.get("path", ""), True))
            size_item = QStandardItem(self.format_size(root.get("size", 0)))
            self.tree_model.appendRow([root_item, size_item])
            
            if root.get("children"):
                dummy = QStandardItem("Loading...")
                root_item.appendRow([dummy, QStandardItem("")])
            
            info = data.get("scan_info", {})
            
            self.stats.setText(
                f"Size: {self.format_size(info.get('size',0))}   "
                f"Folders: {info.get('dirs',0)}   "
                f"Files: {info.get('files',0)}"
            )
            
            self.load_top_files()
            self.load_chart(root)
            print("[UI] load_data finished")
        except Exception as e:
            print(f"Error loading data: {e}")
            traceback.print_exc()
            self.update_status("Error loading data")
    
    def on_tree_expand(self, index):
        try:
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
        except Exception as e:
            print(f"Error on tree expand: {e}")
    
    def _batch_load_tree_children(self, parent_item, children):
        try:
            self._batch_parent = parent_item
            self._batch_children = children
            self._batch_index = 0
            if self._batch_timer:
                self._batch_timer.stop()
            self._batch_timer = QTimer()
            self._batch_timer.timeout.connect(self._process_next_tree_batch)
            self._batch_timer.start(10)
        except Exception as e:
            print(f"Error in batch load: {e}")
    
    def _process_next_tree_batch(self):
        try:
            start = self._batch_index
            end = min(start + self._batch_size, len(self._batch_children))
            for i in range(start, end):
                child = self._batch_children[i]
                name_item = QStandardItem(child.get("name", "Unknown"))
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
        except Exception as e:
            print(f"Error processing tree batch: {e}")
            if self._batch_timer:
                self._batch_timer.stop()
    
    def load_children(self, node):
        try:
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
        except Exception as e:
            print(f"Error loading children: {e}")
    
    def _batch_load_table_children(self, children):
        try:
            self._batch_table_children = children
            self._batch_table_index = 0
            if self._batch_table_timer:
                self._batch_table_timer.stop()
            self._batch_table_timer = QTimer()
            self._batch_table_timer.timeout.connect(self._process_next_table_batch)
            self._batch_table_timer.start(10)
        except Exception as e:
            print(f"Error in batch table load: {e}")
    
    def _process_next_table_batch(self):
        try:
            start = self._batch_table_index
            end = min(start + self._batch_size, len(self._batch_table_children))
            for i in range(start, end):
                child = self._batch_table_children[i]
                is_folder = child.get("dirs", 0) > 0 or child.get("children")
                
                name = QStandardItem(child.get("name", "Unknown"))
                name.setData(child)
                size = QStandardItem(self.format_size(child.get("size", 0)))
                type_item = QStandardItem("Folder" if is_folder else "File")
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
        except Exception as e:
            print(f"Error processing table batch: {e}")
            if self._batch_table_timer:
                self._batch_table_timer.stop()
    
    def on_tree_click(self, index):
        try:
            item = self.tree_model.itemFromIndex(index)
            node = item.data()
            if not node:
                return
            
            if node.get("dirs", 0) == 0 and node.get("files", 0) == 0:
                self.table_model.removeRows(0, self.table_model.rowCount())
                modified, accessed = self.get_file_times(node.get("path", ""))
                
                name = QStandardItem(node.get("name", "Unknown"))
                name.setData(node)
                name.setIcon(self.get_icon(node.get("path", ""), False))
                
                self.table_model.appendRow([
                    name,
                    QStandardItem(self.format_size(node.get("size", 0))),
                    QStandardItem("File"),
                    QStandardItem("1"),
                    QStandardItem("0"),
                    QStandardItem(modified),
                    QStandardItem(accessed)
                ])
                return
            
            QTimer.singleShot(0, lambda: self.load_children(node))
        except Exception as e:
            print(f"Error on tree click: {e}")
    
    def expand_tree_to_path(self, target_path):
        try:
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
        except Exception as e:
            print(f"Error expanding tree: {e}")
    
    def on_table_double_click(self, index):
        try:
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
                if path and os.path.exists(path):
                    os.startfile(path)
        except Exception as e:
            print(f"Error on table double click: {e}")