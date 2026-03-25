from PyQt6.QtCore import QObject, pyqtSignal
import subprocess
import json
import os
import time


class ScanWorker(QObject):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, path):
        super().__init__()
        self.path = path
        self._process = None
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        if self._process:
            self._process.terminate()
            # Give it a moment, then force kill if needed
            time.sleep(0.5)
            if self._process.poll() is None:
                self._process.kill()

    def run(self):
        try:
            if self._is_cancelled:
                self.cancelled.emit()
                return

            base = os.path.dirname(__file__)

            exe = os.path.abspath(os.path.join(base, "..", "..", "scanner.exe"))
            output = os.path.abspath(os.path.join(base, "..", "..", "output", "scan_result.json"))

            if os.path.exists(output):
                os.remove(output)

            self.status.emit("🔍 Scanning...")

            self._process = subprocess.Popen(
                [exe, self.path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
                cwd=os.path.abspath(os.path.join(base, "..", ".."))
            )

            # Read progress live
            for line in self._process.stdout:
                if self._is_cancelled:
                    self._process.terminate()
                    self.cancelled.emit()
                    return
                
                line = line.strip()
                if "PROGRESS:" in line:
                    try:
                        val = int(line.split(":")[1])
                        self.progress.emit(min(val, 99))  # Cap at 99 until done
                    except:
                        pass

            self._process.wait()

            if self._is_cancelled:
                self.cancelled.emit()
                return

            # Wait for JSON with timeout
            timeout = 30  # seconds
            start = time.time()
            last_size = -1

            while time.time() - start < timeout:
                if os.path.exists(output):
                    size = os.path.getsize(output)
                    if size > 0 and size == last_size:
                        break
                    last_size = size
                time.sleep(0.2)

            if not os.path.exists(output) or os.path.getsize(output) == 0:
                self.status.emit("❌ Scan failed - no data")
                self.finished.emit({})
                return

            with open(output, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
            
            self.progress.emit(100)
            self.status.emit("✅ Scan complete")
            self.finished.emit(data)

        except Exception as e:
            print("Worker Error:", e)
            self.status.emit(f"❌ Error: {str(e)}")
            self.finished.emit({})