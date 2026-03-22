from PyQt6.QtCore import QThread
from workers.scan_worker import ScanWorker


class ScanController:
    def __init__(self, ui):
        self.ui = ui

    def start_scan(self, path):
        self.thread = QThread()
        self.worker = ScanWorker(path)

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.finished.connect(self.ui.load_data)
        self.worker.progress.connect(self.ui.update_progress)
        self.worker.status.connect(self.ui.update_status)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()