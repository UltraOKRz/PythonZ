import sys

path = r'c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\1.Python Code\Cloack_Overlay\Cloack_Overlay.pyw'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Fix hasattr(self, 'x') and self.x.winfo_exists() to checking if self.x is not None
# Let's just do a blanket replacement for all such patterns using regex
content = re.sub(
    r"hasattr\(self, '([^']+)'\) and self\.\1\.winfo_exists\(\)",
    r"getattr(self, '\1', None) is not None and self.\1.winfo_exists()",
    content
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
