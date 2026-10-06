import tkinter as tk
from modules.common import StrokeLabel
from .base import BaseUIFrame

class HotFarmFrame(BaseUIFrame):
    """Widget 9: แถบแนะนำแมพในโซนที่ % สูงสุด (Hot Farm Recommender)"""
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, bg=app.trans_key, bd=1,
                         highlightbackground="#eab308", highlightthickness=1, **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        self.lbl_hot_map = StrokeLabel(self, text="🔥 แนะนำ...", font=("Segoe UI", 6, "bold"),
                                       fg="#fde047", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="w")
        self.lbl_hot_map.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 1), pady=1)
        self.app.lbl_hot_map = self.lbl_hot_map

        self.lbl_hot_rate = StrokeLabel(self, text="--%", font=("Consolas", 7, "bold"),
                                        fg="#4ade80", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="e")
        self.lbl_hot_rate.pack(side=tk.RIGHT, padx=(1, 2), pady=1)
        self.app.lbl_hot_rate = self.lbl_hot_rate

        self.lbl_hot_qty = StrokeLabel(self, text="-- N", font=("Consolas", 7, "bold"),
                                       fg="#facc15", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
        self.lbl_hot_qty.pack(side=tk.RIGHT, padx=(1, 3), pady=1)
        self.app.lbl_hot_qty = self.lbl_hot_qty

    def update_hot_recommendation(self, map_name, qty_str, rate_str):
        if hasattr(self, 'lbl_hot_map') and self.lbl_hot_map.winfo_exists():
            self.lbl_hot_map.config(text=map_name)
        if hasattr(self, 'lbl_hot_qty') and self.lbl_hot_qty.winfo_exists():
            self.lbl_hot_qty.config(text=qty_str)
        if hasattr(self, 'lbl_hot_rate') and self.lbl_hot_rate.winfo_exists():
            self.lbl_hot_rate.config(text=rate_str)
