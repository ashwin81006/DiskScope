from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeView, QTableView, QProgressBar,
    QFileDialog, QFileIconProvider, QLabel, QHeaderView,
    QTabWidget, QSplitter, QApplication
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import QFileInfo, Qt, QTimer, QSize
from controllers.scan_controller import ScanController
import os
import datetime
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DiscScope")
        self.resize(1200, 700)

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

        self._setup_ui()

    # ================= UI ================= #

    def load_top_files(self):
        self.top_files_model.removeRows(0, self.top_files_model.rowCount())

        sorted_files = sorted(
            self.top_files_data,
            key=lambda x: x.get("size", 0),
            reverse=True
        )[:50]

        for f in sorted_files:
            path = f.get("path", "")
            size = f.get("size", 0)

            name = os.path.basename(path)

            name_item = QStandardItem(name)
            size_item = QStandardItem(self.format_size(size))
            path_item = QStandardItem(path)

            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)

            # 🔥 USE SAME ICON LOGIC AS TREE
            is_folder = os.path.isdir(path)
            icon = self.get_icon(path, is_folder)

            # 🔥 IMPORTANT (TableView fix)
            name_item.setData(icon, Qt.ItemDataRole.DecorationRole)

            self.top_files_model.appendRow([
                name_item,
                size_item,
                path_item
            ])

        # 🔥 FORCE REFRESH
        self.top_files_model.layoutChanged.emit()
        self.top_files_table.viewport().update()
        

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout()
        top_bar = QHBoxLayout()
        content = QHBoxLayout()

        self.btn_select = QPushButton("Select Folder")
        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setFormat("%p%")
        self.stats = QLabel("Ready")

        self.tree = QTreeView()
        self.table = QTableView()

        # Models
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Name", "Size"])
        self.table_model = QStandardItemModel()
        self.table_model.setHorizontalHeaderLabels(
            ["Name", "Size", "Type", "Files", "Folders", "Last Modified", "Last Accessed"]
        )

        self.tree.setModel(self.tree_model)
        self.table.setModel(self.table_model)

        # UX
        self.tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.table.setHorizontalScrollMode(QTableView.ScrollMode.ScrollPerPixel)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 350)
        self.tree.setIndentation(14)
        self.tree.setColumnWidth(0, 400)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.tree.setStyleSheet("QTreeView::item { height: 26px; }")
        self.table.setStyleSheet("QTableView::item { height: 26px; }")

        # Signals
        self.btn_select.clicked.connect(self.select_folder)
        self.tree.clicked.connect(self.on_tree_click)
        self.tree.expanded.connect(self.on_tree_expand)
        self.table.doubleClicked.connect(self.on_table_double_click)

        # Layout
        top_bar.addWidget(self.btn_select)
        top_bar.addWidget(self.progress)
        top_bar.addWidget(self.stats)

        self.tabs = QTabWidget()
        self.tabs.setContentsMargins(0, 0, 0, 0)
        self.tabs.setStyleSheet("""
        QTabBar::tab { padding: 6px 14px; background: #2b2b2b; border: 1px solid #444; }
        QTabBar::tab:selected { background: #3c3c3c; }
        """)

        # Details tab
        details_tab = QWidget()
        details_layout = QVBoxLayout()
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.addWidget(self.table)
        details_tab.setLayout(details_layout)

        # Top Files tab
        top_files_tab = QWidget()
        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_files_table = QTableView()
        self.top_files_table.verticalHeader().setDefaultSectionSize(26)
        self.top_files_model = QStandardItemModel()
        self.top_files_model.setHorizontalHeaderLabels(["Name", "Size", "Path"])
        self.top_files_table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.top_files_table.setStyleSheet("""
QTableView::item {
    padding-left: 6px;
}
""")
        self.top_files_table.setModel(self.top_files_model)
        header = self.top_files_table.horizontalHeader()
        self.top_files_table.setColumnWidth(0, 300)
        self.top_files_table.setIconSize(QSize(24, 24))
        self.top_files_model.layoutChanged.emit()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)      # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Size
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)      # Path
        self.top_files_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.top_files_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        top_layout.addWidget(self.top_files_table)
        top_files_tab.setLayout(top_layout)

        # Chart tab (placeholder)
        chart_tab = QWidget()
        chart_layout = QVBoxLayout()
        chart_layout.setContentsMargins(0, 0, 0, 0)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        chart_layout.addWidget(self.canvas)
        chart_tab.setLayout(chart_layout)

        self.tabs.addTab(details_tab, "Details")
        self.tabs.addTab(top_files_tab, "Top Files")
        self.tabs.addTab(chart_tab, "Chart")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.tree)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 5)
        splitter.setHandleWidth(3)
        splitter.setSizes([400, 800])

        content.addWidget(splitter)
        main_layout.addLayout(top_bar, 0)
        container = QWidget()
        container.setLayout(content)
        main_layout.addWidget(container, 1)
        central.setLayout(main_layout)

    # ================= HELPERS ================= #

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

        # Sort by size
        children = sorted(children, key=lambda x: x.get("size", 0), reverse=True)

        TOP_N = 6
        top = children[:TOP_N]
        rest = children[TOP_N:]

        labels, sizes = [], []

        for child in top:
            labels.append(child.get("name", ""))
            sizes.append(child.get("size", 0))

        # 🔥 ADD "OTHERS"
        if rest:
            labels.append("Others")
            sizes.append(sum(c.get("size", 0) for c in rest))

        colors = ["#4CAF50", "#2196F3", "#FFC107", "#E91E63", "#9C27B0", "#00BCD4", "#9E9E9E"]

        ax.pie(
            sizes,
            labels=labels,
            autopct='%1.1f%%',
            startangle=140,
            colors=colors[:len(sizes)],
            textprops={'color': 'white'}
        )

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
                datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
                datetime.datetime.fromtimestamp(stat.st_atime).strftime("%Y-%m-%d")
            )
        except:
            return "-", "-"

    # ================= ACTIONS ================= #

    def update_progress(self, val):
        if val < self.last_progress:
            return
        self.last_progress = val
        self.progress.setValue(val)

    def update_status(self, text):
        self.stats.setText(text)

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

        # 🔥 build path map
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
            f"Size: {self.format_size(info.get('size',0))}   "
            f"Folders: {info.get('dirs',0)}   "
            f"Files: {info.get('files',0)}"
        )

        # 🔥 IMPORTANT
        self.load_top_files()
        self.load_chart(root)
        print("[UI] load_data finished")

    # ================= TREE LAZY LOADING ================= #

    def on_tree_expand(self, index):
        item = self.tree_model.itemFromIndex(index)
        node = item.data()
        if not node:
            return

        # Check if already loaded (real children count > 0 or no dummy)
        if item.rowCount() > 0:
            first_child = item.child(0, 0)
            if first_child and first_child.text() == "Loading...":
                # Remove dummy child
                item.removeRows(0, item.rowCount())
            else:
                # Already loaded real children
                return

        real_node = self.path_map.get(node.get("path"))

        if not real_node:
            return

        children = real_node.get("children", [])
        if not children:
            return

        # Start batch loading
        self._batch_load_tree_children(item, children)

    def _batch_load_tree_children(self, parent_item, children):
        self._batch_parent = parent_item
        self._batch_children = children
        self._batch_index = 0
        self._batch_timer = QTimer()
        self._batch_timer.timeout.connect(self._process_next_tree_batch)
        if self._batch_timer:
            self._batch_timer.stop()
        self._batch_timer.start(10)  # as soon as possible

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

            # If this child has its own children, add a dummy child to show expand arrow
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

    # ================= TABLE LOADING ================= #

    def load_children(self, node):
        """Load children into the table (with batching)"""
        self.table_model.removeRows(0, self.table_model.rowCount())
        MAX_ITEMS = 500   # 🔥 IMPORTANT LIMIT

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
        self._batch_table_timer = QTimer()
        self._batch_table_timer.timeout.connect(self._process_next_table_batch)
        if self._batch_table_timer:
            self._batch_table_timer.stop()
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

    # ================= TREE CLICK ================= #

    def on_tree_click(self, index):
        item = self.tree_model.itemFromIndex(index)
        node = item.data()
        if not node:
            return

        # File click (leaf)
        if node.get("dirs", 0) == 0 and node.get("files", 0) == 0:
            self.table_model.removeRows(0, self.table_model.rowCount())
            modified, accessed = self.get_file_times(node.get("path", ""))

            name = QStandardItem(node.get("name", ""))
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

        # Folder click – load table children
        QTimer.singleShot(0, lambda: self.load_children(node))

    def expand_tree_to_path(self, target_path):
        """Expand tree to show the folder at target_path"""
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