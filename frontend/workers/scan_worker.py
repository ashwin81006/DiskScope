from PyQt6.QtCore import QObject, pyqtSignal
import subprocess
import json
import os
import time


class ScanWorker(QObject):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int)
    status = pyqtSignal(str)

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        try:
            base = os.path.dirname(__file__)

            exe = os.path.abspath(os.path.join(base, "..", "..", "scanner.exe"))
            output = os.path.abspath(os.path.join(base, "..", "..", "output", "scan_result.json"))

            if os.path.exists(output):
                os.remove(output)

            self.status.emit("🔍 Scanning...")

            process = subprocess.Popen(
                [exe, self.path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=os.path.abspath(os.path.join(base, "..", ".."))
            )

            # 🔥 READ PROGRESS LIVE
            while True:
                line = process.stdout.readline()

                if line:
                    line = line.strip()

                    if "PROGRESS:" in line:
                        try:
                            val = int(line.split(":")[1])
                            self.progress.emit(val)
                        except:
                            pass

                if process.poll() is not None:
                    break

            process.wait()

            # 🔥 WAIT FOR JSON
            while not os.path.exists(output):
                time.sleep(0.2)

            while True:
                try:
                    with open(output, "r") as f:
                        data = json.load(f)
                    break
                except:
                    time.sleep(0.2)

            self.progress.emit(100)
            self.status.emit("✅ Scan complete")
            self.finished.emit(data)

        except Exception as e:
            print("Worker Error:", e)
            self.finished.emit({})