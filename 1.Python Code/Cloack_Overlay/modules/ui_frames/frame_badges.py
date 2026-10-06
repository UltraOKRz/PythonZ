import tkinter as tk
from .base import BaseUIFrame

class BadgesFrame(BaseUIFrame):
    """Widget 5: กล่องแสดงยอดเหรียญ NESO ใน Pool ปัจจุบัน (Normal & Boost)"""
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, bg="#08101a", **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        self.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())

        coin_img = self.app.get_neso_coin_photo(size=37)

        # กล่อง 1: Normal Pool Badge
        c_norm_badge = tk.Frame(self, bg="#081d3d", bd=1, relief="solid",
                                highlightbackground="#0084ff", highlightthickness=1, cursor="hand2")
        c_norm_badge.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2), pady=2)
        c_norm_badge.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())

        if coin_img:
            lbl_cn_icon = tk.Label(c_norm_badge, image=coin_img, bg="#081d3d")
            lbl_cn_icon.image = coin_img
            lbl_cn_icon.pack(padx=2, pady=(2, 0))
            lbl_cn_icon.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        else:
            lbl_cn_icon = tk.Label(c_norm_badge, text="🪙", font=("Segoe UI", 12), bg="#081d3d")
            lbl_cn_icon.pack(padx=2, pady=(2, 0))
            lbl_cn_icon.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())

        _init_norm_stk = self.app.format_compact_number(getattr(self.app, 'neso_normal_stock_f', 0.0))
        self.lbl_neso_badge_norm_stock = tk.Label(c_norm_badge, text=f"{_init_norm_stk}", font=("Consolas", 17, "bold"), fg="#bbf246", bg="#081d3d")
        self.lbl_neso_badge_norm_stock.pack(padx=2, pady=(0, 3))
        self.lbl_neso_badge_norm_stock.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_neso_badge_norm_stock = self.lbl_neso_badge_norm_stock

        # กล่อง 2: Boost Pool Badge
        c_boost_badge = tk.Frame(self, bg="#081d3d", bd=1, relief="solid",
                                 highlightbackground="#0084ff", highlightthickness=1, cursor="hand2")
        c_boost_badge.pack(side=tk.LEFT, expand=True, fill=tk.X, pady=2)
        c_boost_badge.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())

        if coin_img:
            lbl_cb_icon = tk.Label(c_boost_badge, image=coin_img, bg="#081d3d")
            lbl_cb_icon.image = coin_img
            lbl_cb_icon.pack(padx=2, pady=(2, 0))
            lbl_cb_icon.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        else:
            lbl_cb_icon = tk.Label(c_boost_badge, text="🪙", font=("Segoe UI", 12), bg="#081d3d")
            lbl_cb_icon.pack(padx=2, pady=(2, 0))
            lbl_cb_icon.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())

        _init_boost_stk = getattr(self.app, 'neso_boost_stock', '--')
        self.lbl_neso_badge_stock = tk.Label(c_boost_badge, text=f"{_init_boost_stk}", font=("Consolas", 17, "bold"), fg="#bbf246", bg="#081d3d")
        self.lbl_neso_badge_stock.pack(padx=2, pady=(0, 3))
        self.lbl_neso_badge_stock.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_neso_badge_stock = self.lbl_neso_badge_stock

    def update_badge_stocks(self, norm_str, boost_str, is_safe=False):
        if hasattr(self, 'lbl_neso_badge_norm_stock') and self.lbl_neso_badge_norm_stock.winfo_exists():
            if is_safe:
                self.lbl_neso_badge_norm_stock.config(text="--", fg="#64748b")
            else:
                self.lbl_neso_badge_norm_stock.config(text=norm_str, fg="#bbf246")

        if hasattr(self, 'lbl_neso_badge_stock') and self.lbl_neso_badge_stock.winfo_exists():
            if is_safe:
                self.lbl_neso_badge_stock.config(text="--", fg="#64748b")
            else:
                self.lbl_neso_badge_stock.config(text=boost_str, fg="#bbf246")
