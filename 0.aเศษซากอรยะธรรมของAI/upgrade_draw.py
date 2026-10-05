import re

file_path = r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\โพสิชั่น.pyw"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update UI in open_full_chart
header_ui_pattern = r"        self\.btn_draw = tk\.Button\(header, text=\"✏️ ตีเส้น\", command=self\.toggle_draw_mode, bg=\"#2b313a\", fg=\"#fff\", bd=0, font=\(\"Arial\", 9\), cursor=\"hand2\"\)\n        self\.btn_draw\.pack\(side=tk\.LEFT, padx=6\)"
header_ui_replace = """        self.draw_type_var = tk.StringVar(value="trend")
        self.btn_draw = tk.Menubutton(header, text="✏️ Trend Line ▼", bg="#2b313a", fg="#fff", bd=0, font=("Arial", 9), cursor="hand2", relief=tk.FLAT)
        self.btn_draw.pack(side=tk.LEFT, padx=6)
        
        self.draw_menu = tk.Menu(self.btn_draw, tearoff=0, bg="#2b313a", fg="#fff", font=("Arial", 9))
        self.btn_draw.config(menu=self.draw_menu)
        
        self.draw_menu.add_command(label="✏️ Trend Line", command=lambda: self.set_draw_mode("trend", "✏️ Trend Line ▼"))
        self.draw_menu.add_command(label="➡️ Ray", command=lambda: self.set_draw_mode("ray", "➡️ Ray ▼"))
        self.draw_menu.add_command(label="↔️ Extended", command=lambda: self.set_draw_mode("extended", "↔️ Extended ▼"))
        self.draw_menu.add_command(label="➖ Horizontal", command=lambda: self.set_draw_mode("horizontal", "➖ Horizontal ▼"))
        self.draw_menu.add_separator()
        self.draw_menu.add_command(label="❌ Cancel Draw", command=self.cancel_draw_mode)"""
content = re.sub(header_ui_pattern, header_ui_replace, content)

# 2. Add set_draw_mode and cancel_draw_mode methods
draw_methods_pattern = r"    def toggle_draw_mode\(self\):\n        self\.is_drawing_mode = not self\.is_drawing_mode\n        self\.draw_start_point = None\n        self\.selected_line_idx = None\n        self\.btn_draw\.config\(bg=\"#f0b90b\", fg=\"#000\"\) if self\.is_drawing_mode else self\.btn_draw\.config\(bg=\"#2b313a\", fg=\"#fff\"\)\n        self\.canvas\.config\(cursor=\"crosshair\" if self\.is_drawing_mode else \"arrow\"\)\n        self\.request_chart_redraw\(\"full\"\)"
draw_methods_replace = """    def set_draw_mode(self, mode, text):
        self.draw_type_var.set(mode)
        self.is_drawing_mode = True
        self.draw_start_point = None
        self.selected_line_idx = None
        self.btn_draw.config(text=text, bg="#f0b90b", fg="#000")
        self.canvas.config(cursor="crosshair")
        self.request_chart_redraw("full")

    def cancel_draw_mode(self):
        self.is_drawing_mode = False
        self.draw_start_point = None
        self.btn_draw.config(bg="#2b313a", fg="#fff")
        self.canvas.config(cursor="arrow")
        self.request_chart_redraw("full")

    def toggle_draw_mode(self):
        if self.is_drawing_mode: self.cancel_draw_mode()
        else: self.set_draw_mode(self.draw_type_var.get(), self.btn_draw.cget("text"))"""
content = re.sub(draw_methods_pattern, draw_methods_replace, content)

# 3. Update line rendering in render_candlesticks
# We remove the `if not is_hover:` block and allow drawing on both
draw_render_pattern = r"        # วาดเส้นเทรนด์ไลน์ที่ตีไว้ \(เฉพาะตัวเต็ม\)\n        if not is_hover:\n            sym_tf = f\"{self\.active_sim\['symbol'\]}\"\n            for idx, line in enumerate\(self\.cfg_data\.get\(\"saved_lines\", \{\}\)\.get\(sym_tf, \[\]\)\):\n                x1, y1 = self\.time_price_to_xy\(line\[0\], line\[1\]\)\n                x2, y2 = self\.time_price_to_xy\(line\[2\], line\[3\]\)\n                color = \"#ffffff\" if self\.selected_line_idx == idx else \"#f0b90b\"\n                canvas\.create_line\(x1, y1, x2, y2, fill=color, width=2\)\n                if self\.selected_line_idx == idx:\n                    canvas\.create_oval\(x1-4, y1-4, x1\+4, y1\+4, fill=\"#00e676\", outline=\"\"\)\n                    canvas\.create_oval\(x2-4, y2-4, x2\+4, y2\+4, fill=\"#00e676\", outline=\"\"\)\n\n            if self\.is_drawing_mode and self\.draw_start_point and self\.temp_mouse_pos:\n                x1, y1 = self\.time_price_to_xy\(self\.draw_start_point\[0\], self\.draw_start_point\[1\]\)\n                canvas\.create_line\(x1, y1, self\.temp_mouse_pos\[0\], self\.temp_mouse_pos\[1\], fill=\"#fff\", width=1, dash=\(4,2\)\)"
draw_render_replace = """        # วาดเส้นเทรนด์ไลน์ที่ตีไว้
        sym_tf = f"{self.active_sim['symbol']}"
        for idx, line in enumerate(self.cfg_data.get("saved_lines", {}).get(sym_tf, [])):
            x1, y1 = self.time_price_to_xy(line[0], line[1])
            x2, y2 = self.time_price_to_xy(line[2], line[3])
            l_type = line[4] if len(line) > 4 else "trend"
            
            if l_type == "horizontal": y2 = y1 # Force horizontal
            
            dx, dy = x2 - x1, y2 - y1
            if dx == 0 and dy == 0: dx = 1
            
            rx1, ry1, rx2, ry2 = x1, y1, x2, y2
            if l_type == "ray":
                rx2, ry2 = x1 + dx * 10000, y1 + dy * 10000
            elif l_type == "extended":
                rx1, ry1 = x1 - dx * 10000, y1 - dy * 10000
                rx2, ry2 = x1 + dx * 10000, y1 + dy * 10000
            elif l_type == "horizontal":
                rx1, ry1 = -10000, y1
                rx2, ry2 = 10000, y1
                
            color = "#ffffff" if (self.selected_line_idx == idx and not is_hover) else "#f0b90b"
            canvas.create_line(rx1, ry1, rx2, ry2, fill=color, width=2)
            
            if self.selected_line_idx == idx and not is_hover:
                canvas.create_oval(x1-4, y1-4, x1+4, y1+4, fill="#00e676", outline="")
                canvas.create_oval(x2-4, y2-4, x2+4, y2+4, fill="#00e676", outline="")

        if not is_hover and getattr(self, 'is_drawing_mode', False) and getattr(self, 'draw_start_point', None) and getattr(self, 'temp_mouse_pos', None):
            x1, y1 = self.time_price_to_xy(self.draw_start_point[0], self.draw_start_point[1])
            x2, y2 = self.temp_mouse_pos[0], self.temp_mouse_pos[1]
            l_type = self.draw_type_var.get()
            if l_type == "horizontal": y2 = y1
            dx, dy = x2 - x1, y2 - y1
            if dx == 0 and dy == 0: dx = 1
            
            rx1, ry1, rx2, ry2 = x1, y1, x2, y2
            if l_type == "ray":
                rx2, ry2 = x1 + dx * 10000, y1 + dy * 10000
            elif l_type == "extended":
                rx1, ry1 = x1 - dx * 10000, y1 - dy * 10000
                rx2, ry2 = x1 + dx * 10000, y1 + dy * 10000
            elif l_type == "horizontal":
                rx1, ry1 = -10000, y1
                rx2, ry2 = 10000, y1
                
            canvas.create_line(rx1, ry1, rx2, ry2, fill="#fff", width=1, dash=(4,2))"""
content = re.sub(draw_render_pattern, draw_render_replace, content)


# 4. Save the line type in on_canvas_press
save_line_pattern = r"                self\.cfg_data\[\"saved_lines\"\]\[sym_tf\]\.append\(\[self\.draw_start_point\[0\], self\.draw_start_point\[1\], t, p\]\)"
save_line_replace = """                self.cfg_data["saved_lines"][sym_tf].append([self.draw_start_point[0], self.draw_start_point[1], t, p, self.draw_type_var.get()])"""
content = re.sub(save_line_pattern, save_line_replace, content)

# 5. Cancel drawing mode after finishing one draw
finish_draw_pattern = r"                self\.save_config\(\)\n                self\.draw_start_point = None\n            self\.request_chart_redraw\(\"full\"\)"
finish_draw_replace = """                self.save_config()
                self.draw_start_point = None
                self.cancel_draw_mode()
            self.request_chart_redraw("full")"""
content = re.sub(finish_draw_pattern, finish_draw_replace, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Upgrade Draw applied.")
