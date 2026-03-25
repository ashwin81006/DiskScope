from PyQt6.QtCore import QThread
from workers.scan_worker import ScanWorker


class ScanController:
    def __init__(self, ui):
        self.ui = ui
        self.thread = None
        self.worker = None

    def start_scan(self, path):
        print("[Controller] Starting scan for", path)
        self.thread = QThread()
        self.worker = ScanWorker(path)

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.finished.connect(self.on_finished)
        self.worker.progress.connect(self.ui.update_progress)
        self.worker.status.connect(self.ui.update_status)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_finished(self, data):
        print("[Controller] finished signal received, data keys:", data.keys() if data else "None")
        self.ui.load_data(data)