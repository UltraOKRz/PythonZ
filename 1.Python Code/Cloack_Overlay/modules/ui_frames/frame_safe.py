import tkinter as tk
from .base import BaseUIFrame

class SafeZoneFrame(BaseUIFrame):
    """Widget 7: แผ่นป้าย Safe Zone แสดงแทนแผงตัวเลขดรอปเมื่ออยู่ในเมืองหรือแมพไม่มีดรอป"""
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, bg="#06090e", cursor="hand2", **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        self.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())

        # การ์ดป้ายสี่เหลี่ยมสีขาว Safe Zone เด่นตรงกลาง
        f_sz_card = tk.Frame(self, bg="#ffffff", bd=1, relief="solid",
                             highlightbackground="#94a3b8", highlightthickness=1)
        f_sz_card.pack(expand=True, padx=4, pady=(4, 2))
        f_sz_card.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())

        self.lbl_sz_title = tk.Label(f_sz_card, text="Safe Zone", font=("Segoe UI", 10, "bold"),
                                     fg="#0f172a", bg="#ffffff", padx=10, pady=3)
        self.lbl_sz_title.pack()
        self.lbl_sz_title.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_sz_title = self.lbl_sz_title

        self.lbl_sz_desc = tk.Label(self, text="[ จุดพักผ่อน • ปลอดภัยจากมอนสเตอร์ ]",
                                    font=("Segoe UI", 7), fg="#64748b", bg="#06090e")
        self.lbl_sz_desc.pack(pady=(0, 2))
        self.lbl_sz_desc.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_sz_desc = self.lbl_sz_desc

        self.lbl_sz_town = tk.Label(self, text="🏙️ จุดปลอดภัย",
                                    font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#06090e")
        self.lbl_sz_town.pack(pady=(0, 5))
        self.lbl_sz_town.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_sz_town = self.lbl_sz_town

    def update_town_display(self, town_name):
        if hasattr(self, 'lbl_sz_town') and self.lbl_sz_town.winfo_exists():
            self.lbl_sz_town.config(text=f"🏙️ {town_name}")
