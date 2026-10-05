import re

file_path = r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\โพสิชั่น.pyw"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Pattern to replace
pattern = r"        elif entry_price > 0:\n            raw_y_entry = inner_h - \(\(entry_price - act_min\) / act_rng\) \* inner_h\n            y_entry = max\(10, min\(inner_h - 10, raw_y_entry\)\)\n            margin = self\.active_sim\[\"margin\"\]\n            qty = \(margin \* self\.active_sim\[\"leverage\"\]\) / entry_price\n            pnl = \(live_price - entry_price\) \* qty if self\.active_sim\['side'\] == \"Long\" else \(entry_price - live_price\) \* qty\n            roe = \(pnl / margin\) \* 100\n            entry_color = \"#00bfff\" if self\.active_sim\['side'\] == \"Long\" else \"#ff9800\"\n            sign = \"\+\" if pnl >= 0 else \"\"\n            if raw_y_entry < 0 or raw_y_entry > inner_h:\n                canvas\.create_line\(0, y_entry, inner_w, y_entry, fill=entry_color, width=1\.5, dash=\(4,4\)\)\n            else:\n                canvas\.create_line\(0, y_entry, inner_w, y_entry, fill=entry_color, width=1\.5\)\n            canvas\.create_rectangle\(inner_w, y_entry - 8, w, y_entry \+ 8, fill=entry_color, outline=\"\"\)\n            canvas\.create_text\(inner_w \+ 2, y_entry, text=f\" \{entry_price:,\.2f\}\", fill=\"#000\", anchor=tk\.W, font=\(\"Arial\", 8, \"bold\"\)\)\n            canvas\.create_text\(5, y_entry - 12 if y_entry > 20 else y_entry \+ 12, text=f\"Entry: PNL \{sign\}\$\{pnl:,\.2f\} \(\{sign\}\{roe:,\.2f\}%\)\", fill=entry_color, anchor=tk\.W, font=\(\"Arial\", 8, \"bold\"\)\)"

replacement = """        elif entry_price > 0:
            raw_y_entry = inner_h - ((entry_price - act_min) / act_rng) * inner_h
            y_entry = max(10, min(inner_h - 10, raw_y_entry))
            margin = self.active_sim["margin"]
            qty = (margin * self.active_sim["leverage"]) / entry_price
            pnl = (live_price - entry_price) * qty if self.active_sim['side'] == "Long" else (entry_price - live_price) * qty
            roe = (pnl / margin) * 100
            
            if pnl > 0.01: pnl_color = "#00e676"
            elif pnl < -0.01: pnl_color = "#ff3d57"
            else: pnl_color = "#ffffff"
            
            sign = "+" if pnl > 0 else ""
            
            # Draw line matching PNL color (thin, dashed)
            canvas.create_line(0, y_entry, inner_w, y_entry, fill=pnl_color, width=1, dash=(2,2))
            
            # Entry Price right-axis label
            canvas.create_rectangle(inner_w, y_entry - 8, w, y_entry + 8, fill=pnl_color, outline="")
            canvas.create_text(inner_w + 2, y_entry, text=f"{entry_price:,.2f}", fill="#000", anchor=tk.W, font=("Arial", 8, "bold"))
            
            # PNL text on the right side
            pnl_text = f" {self.active_sim['side']} {self.active_sim['leverage']}x | PNL {sign}${pnl:,.2f} ({sign}{roe:,.2f}%) "
            text_y = y_entry - 14 if y_entry > 20 else y_entry + 14
            t_id = canvas.create_text(inner_w - 5, text_y, text=pnl_text, fill="#121418", anchor=tk.E, font=("Arial", 8, "bold"))
            
            # Draw background box for PNL text
            bbox = canvas.bbox(t_id)
            if bbox:
                r_id = canvas.create_rectangle(bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2, fill=pnl_color, outline="")
                canvas.tag_lower(r_id, t_id)"""

new_content, count = re.subn(pattern, replacement, content)
if count > 0:
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("PNL line successfully updated!")
else:
    print("Pattern not found!")
