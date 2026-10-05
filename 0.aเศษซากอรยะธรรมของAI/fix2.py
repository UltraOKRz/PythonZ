import sys

path = r'c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\1.Python Code\Cloack_Overlay\Cloack_Overlay.pyw'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Clock Ring with horizontal timer
old_timer = """            # Center: Clock Ring (Fixed Anchor)
            f_ring_center = tk.Frame(f_pool_zone, bg=self.trans_key)
            f_ring_center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            f_ring_center.bind("<ButtonPress-1>", self.start_drag)
            f_ring_center.bind("<B1-Motion>", self.do_drag)
            f_ring_center.bind("<ButtonRelease-1>", self.end_drag)

            self.canvas_full = tk.Canvas(f_ring_center, bg=self.trans_key, highlightthickness=0)
            self.canvas_full.pack(fill=tk.BOTH, expand=True)
            self.canvas_full.bind("<ButtonPress-1>", self.start_drag)
            self.canvas_full.bind("<B1-Motion>", self.do_drag)
            self.canvas_full.bind("<ButtonRelease-1>", self.end_drag)
            self.canvas_full.bind("<Configure>", lambda e: self.redraw_full_canvas())"""

new_timer = """            # Center: Timer (Fixed Anchor)
            f_ring_center = tk.Frame(f_pool_zone, bg=self.trans_key)
            f_ring_center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            f_ring_center.bind("<ButtonPress-1>", self.start_drag)
            f_ring_center.bind("<B1-Motion>", self.do_drag)
            f_ring_center.bind("<ButtonRelease-1>", self.end_drag)

            self.lbl_timer_text = tk.Label(f_ring_center, text="00:00", font=("Consolas", 16, "bold"), fg="#38bdf8", bg=self.trans_key)
            self.lbl_timer_text.pack(expand=True)
            self.lbl_timer_text.bind("<ButtonPress-1>", self.start_drag)
            self.lbl_timer_text.bind("<B1-Motion>", self.do_drag)
            self.lbl_timer_text.bind("<ButtonRelease-1>", self.end_drag)
            
            self.canvas_timer_bar = tk.Canvas(f_ring_center, bg="#0f172a", height=12, highlightthickness=0)
            self.canvas_timer_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=4, pady=(0,4))
            self.canvas_timer_bar.bind("<ButtonPress-1>", self.start_drag)
            self.canvas_timer_bar.bind("<B1-Motion>", self.do_drag)
            self.canvas_timer_bar.bind("<ButtonRelease-1>", self.end_drag)"""

content = content.replace(old_timer, new_timer)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
