import subprocess
import time
import os
import sys

pyw_path = os.path.abspath(r"1.Python Code\Cloack_Overlay\Cloack_Overlay.pyw")
print("Starting Cloack_Overlay.pyw for validation...")
proc = subprocess.Popen([sys.executable, pyw_path])
time.sleep(3)

# เช็คว่า process ยังรันอยู่ดี
if proc.poll() is None:
    print("SUCCESS: Process is running properly without crash!")
    proc.terminate()
else:
    print("FAILED: Process exited with code:", proc.returncode)
