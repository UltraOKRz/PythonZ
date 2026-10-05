import runpy
import traceback
import sys

try:
    d = runpy.run_path(r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\โพสิชั่น.pyw", run_name="__main__")
except Exception as e:
    traceback.print_exc()
