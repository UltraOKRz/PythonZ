import sys

path = r'c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\1.Python Code\Cloack_Overlay\Cloack_Overlay.pyw'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, l in enumerate(lines):
    if i == 523: # index 523 is line 524
        skip = True
    if skip and i == 534: # index 534 is line 535
        skip = False
        continue
    if not skip:
        new_lines.append(l)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
