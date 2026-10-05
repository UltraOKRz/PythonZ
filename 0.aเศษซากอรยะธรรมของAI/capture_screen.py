import subprocess
import time
import os
import sys
from PIL import ImageGrab

pyw_path = os.path.abspath(r"1.Python Code\Cloack_Overlay\Cloack_Overlay.pyw")
proc = subprocess.Popen([sys.executable, pyw_path])
time.sleep(3.5) # รอให้โหลดและดึง API

# จับภาพหน้าจอตำแหน่ง 100, 100
bbox = (95, 95, 360, 480)
im = ImageGrab.grab(bbox)
out_img = r"C:\Users\PythonX\.gemini\antigravity-ide\brain\dc3b2554-7403-4718-be5d-b5f2d78749b3\live_running_overlay.png"
im.save(out_img)
print("Captured live overlay to", out_img)

proc.terminate()
