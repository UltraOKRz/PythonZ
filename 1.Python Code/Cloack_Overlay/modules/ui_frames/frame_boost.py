import tkinter as tk
from .base import BaseUIFrame

class BoostTopFrame(BaseUIFrame):
    """Widget 6: แถบสีเขียวแสดงอัตรา BOOST DROP รวมตรงกลาง"""
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, bg="#14532d", bd=1, relief="solid", 
                         highlightbackground="#22c55e", highlightthickness=1, cursor="hand2", **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        self.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())

        self.lbl_flame = tk.Label(self, text="💧 BOOST", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#14532d")
        self.lbl_flame.pack(side=tk.LEFT, padx=4, pady=5)
        self.lbl_flame.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_flame = self.lbl_flame

        self.lbl_boost_hdr_mult = tk.Label(self, text="", font=("Consolas", 17, "bold"), fg="#86efac", bg="#14532d")
        self.lbl_boost_hdr_mult.pack(side=tk.RIGHT, padx=4, pady=5)
        self.lbl_boost_hdr_mult.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_boost_hdr_mult = self.lbl_boost_hdr_mult

        self.lbl_neso_boost_val = tk.Label(self, text="รอข้อมูล", font=("Consolas", 17, "bold"), fg="#4ade80", bg="#14532d")
        self.lbl_neso_boost_val.place(relx=0.5, rely=0.5, anchor="center")
        self.lbl_neso_boost_val.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_neso_boost_val = self.lbl_neso_boost_val

    def update_boost_header(self, text_rate, mult_text="", is_safe=False):
        if hasattr(self, 'lbl_flame') and self.lbl_flame.winfo_exists():
            if is_safe:
                self.lbl_flame.config(text="🌿 SAFE ZONE", fg="#4ade80")
            else:
                self.lbl_flame.config(text="💧 BOOST", fg="#38bdf8")

        if hasattr(self, 'lbl_neso_boost_val') and self.lbl_neso_boost_val.winfo_exists():
            if is_safe:
                self.lbl_neso_boost_val.config(text="🛡️ ปลอดภัย", fg="#94a3b8")
            else:
                self.lbl_neso_boost_val.config(text=text_rate, fg="#4ade80")

        if hasattr(self, 'lbl_boost_hdr_mult') and self.lbl_boost_hdr_mult.winfo_exists():
            self.lbl_boost_hdr_mult.config(text="" if is_safe else mult_text)
