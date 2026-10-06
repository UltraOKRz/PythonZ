import tkinter as tk
from modules.common import StrokeLabel
from .base import BaseUIFrame

class MapBannerFrame(BaseUIFrame):
    """Widget 2: แถบ Map Banner (โปร่งใส + StrokeLabel คมชัด สไตล์ Game HUD)"""
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, bg=app.trans_key, bd=0, cursor="hand2", **kwargs)
        self.app = app
        self.var_main = tk.StringVar(value=self.app.selected_layer_name or "รอตรวจจับแมพ...")
        self.var_sub = tk.StringVar(value=f"📍 {self.app.detected_submap_name}" if getattr(self.app, 'detected_submap_name', '') else "📍 กด Scan Map หรือเลือกแมพ")
        self._build_ui()

    def _build_ui(self):
        self.bind("<Button-1>", lambda e: self.app.open_map_picker())

        self.lbl_arr = StrokeLabel(self, text="▾", font=("Segoe UI", 9, "bold"),
                                   fg="#38bdf8", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="e", cursor="hand2")
        self.lbl_arr.pack(side=tk.RIGHT, padx=4)
        self.lbl_arr.bind("<Button-1>", lambda e: self.app.open_map_picker())
        self.app.lbl_arr = self.lbl_arr

        self.lbl_map_icon = tk.Label(self, bg=self.app.trans_key, cursor="hand2")
        self.lbl_map_icon.pack(side=tk.LEFT, padx=(3, 4))
        self.lbl_map_icon.bind("<Button-1>", lambda e: self.app.open_map_picker())
        self.app.lbl_map_icon = self.lbl_map_icon

        f_map_txts = tk.Frame(self, bg=self.app.trans_key, cursor="hand2")
        f_map_txts.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=3)
        f_map_txts.bind("<Button-1>", lambda e: self.app.open_map_picker())

        self.lbl_map_main = StrokeLabel(f_map_txts, text=self.var_main.get(), font=("Segoe UI", 10, "bold"),
                                        fg="#e2e8f0", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="w", cursor="hand2", wraplength=120)
        self.lbl_map_main.pack(fill=tk.X)
        self.lbl_map_main.bind("<Button-1>", lambda e: self.app.open_map_picker())
        self.app.lbl_map_main = self.lbl_map_main
        self.app.btn_map = self.lbl_map_main

        self.lbl_map_sub = StrokeLabel(f_map_txts, text=self.var_sub.get(), font=("Segoe UI", 9),
                                       fg="#38bdf8", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="w", cursor="hand2", wraplength=120)
        self.lbl_map_sub.pack(fill=tk.X, pady=(1, 0))
        self.lbl_map_sub.bind("<Button-1>", lambda e: self.app.open_map_picker())
        self.app.lbl_map_sub = self.lbl_map_sub

    def update_map(self, main_name, sub_name):
        self.var_main.set(main_name or "รอตรวจจับแมพ...")
        self.var_sub.set(f"📍 {sub_name}" if sub_name else "📍 กด Scan Map หรือเลือกแมพ")
        if hasattr(self, 'lbl_map_main') and self.lbl_map_main.winfo_exists():
            self.lbl_map_main.config(text=self.var_main.get())
        if hasattr(self, 'lbl_map_sub') and self.lbl_map_sub.winfo_exists():
            self.lbl_map_sub.config(text=self.var_sub.get())
