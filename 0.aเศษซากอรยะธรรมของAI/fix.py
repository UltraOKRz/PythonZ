import sys

path = r'c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\1.Python Code\Cloack_Overlay\Cloack_Overlay.pyw'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('f"{self.wallet_neso_compact}\nNESO"', 'f"{self.wallet_neso_compact}\\nNESO"')
content = content.replace('"...\\nNESO"', '"...\\nNESO"')  # already fine
content = content.replace('"...\\nNESO"\nNESO"', '"...\\nNESO"')
content = content.replace('"...\\nNESO"\nNESO', '"...\\nNESO"')
content = content.replace('"...\\nNESO"', '"...\\nNESO"')
content = content.replace('"...\\nNESO"', '"...\\nNESO"')
# I will just write a regex
import re
content = re.sub(r'f"\{self\.wallet_neso_compact\}\nNESO"', r'f"{self.wallet_neso_compact}\\nNESO"', content)
content = re.sub(r'"\.\.\.\nNESO"', r'"...\\nNESO"', content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
