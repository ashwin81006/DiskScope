from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeView, QTableView, QProgressBar,
    QFileDialog, QFileIconProvider, QLabel, QHeaderView
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor
from PyQt6.QtCore import QFileInfo, Qt

from controllers.scan_controller import ScanController
import os
import datetime


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DiscScope")
        self.resize(1200, 700)

        self.icon_provider = QFileIconProvider()
        self.controller = ScanController(self)

        self.last_progress = 0

        self._setup_ui()

    # ================= UI ================= #
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

        # MODELS
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

        # Allow horizontal scroll instead of cutting text
        self.table.setHorizontalScrollMode(QTableView.ScrollMode.ScrollPerPixel)

        # Make Name column wider
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 350)

        self.tree.setIndentation(14)
        self.tree.setColumnWidth(0, 400)

        self.table.horizontalHeader().setStretchLastSection(True)

        self.tree.setStyleSheet("QTreeView::item { height: 26px; }")
        self.table.setStyleSheet("QTableView::item { height: 26px; }")

        # SIGNALS
        self.btn_select.clicked.connect(self.select_folder)
        self.tree.clicked.connect(self.on_tree_click)
        self.table.doubleClicked.connect(self.on_table_double_click)

        # LAYOUT
        top_bar.addWidget(self.btn_select)
        top_bar.addWidget(self.progress)
        top_bar.addWidget(self.stats)

        content.addWidget(self.tree, 2)
        content.addWidget(self.table, 3)

        main_layout.addLayout(top_bar)
        main_layout.addLayout(content)

        central.setLayout(main_layout)

    # ================= HELPERS ================= #
    def format_size(self, size):
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024

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
            self.tree_model.removeRows(0, self.tree_model.rowCount())
            self.table_model.removeRows(0, self.table_model.rowCount())

            self.progress.setValue(0)
            self.last_progress = 0

            self.update_status("Scanning...")
            self.controller.start_scan(path)

    def load_data(self, data):
        self.tree_model.removeRows(0, self.tree_model.rowCount())

        root = data.get("tree", {})
        self.tree_model.appendRow(self._build_tree(root))

        info = data.get("scan_info", {})

        self.stats.setText(
            f"Size: {self.format_size(info.get('size',0))}   "
            f"Folders: {info.get('dirs',0)}   "
            f"Files: {info.get('files',0)}"
        )

    # ================= TREE ================= #
    def _build_tree(self, node):
        name = QStandardItem(node.get("name", ""))
        size = QStandardItem(self.format_size(node.get("size", 0)))

        name.setData(node)
        name.setIcon(self.get_icon(node.get("path", ""), True))

        for child in node.get("children", []):
            name.appendRow(self._build_tree(child))

        return [name, size]

    # ================= TABLE ================= #
    def load_children(self, node):
        self.table_model.removeRows(0, self.table_model.rowCount())

        for child in node.get("children", []):
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
                name,
                size,
                type_item,
                files,
                dirs,
                QStandardItem(modified),
                QStandardItem(accessed)
            ])

    def on_tree_click(self, index):
        item = self.tree_model.itemFromIndex(index)
        node = item.data()

        if not node:
            return

        # FILE CLICK
        # FILE CLICK
        if node.get("dirs", 0) == 0 and node.get("files", 0) == 0:
            self.table_model.removeRows(0, self.table_model.rowCount())

            modified, accessed = self.get_file_times(node.get("path", ""))

            name = QStandardItem(node.get("name", ""))
            name.setData(node)

            # 🔥 FIX: ADD ICON
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

        self.load_children(node)

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

                # 🔥 expand parents
                parent = index
                while parent.isValid():
                    self.tree.expand(parent)
                    parent = parent.parent()

                self.tree.setCurrentIndex(index)
                self.tree.scrollTo(index)
                break
    # ================= DOUBLE CLICK ================= #
    def on_table_double_click(self, index):
        item = self.table_model.itemFromIndex(index)
        node = item.data()

        if not node:
            return

        path = node.get("path", "")
        is_folder = node.get("dirs", 0) > 0 or node.get("children")

        if is_folder:
            self.load_children(node)

            # 🔥 NEW: sync left tree
            self.expand_tree_to_path(path)

        else:
            os.startfile(path)