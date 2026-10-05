import subprocess
import time
import os

proc = subprocess.Popen(["python", "1.Python Code\\Cloack_Overlay\\Cloack_Overlay.pyw"])
print("COS launched, PID:", proc.pid)
time.sleep(2)
poll = proc.poll()
if poll is None:
    print("SUCCESS: COS is running stably!")
    proc.terminate()
else:
    print("FAILED: COS terminated unexpectedly with code:", poll)
