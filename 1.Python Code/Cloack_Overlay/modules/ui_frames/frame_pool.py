import tkinter as tk
from modules.common import StrokeLabel
from .base import BaseUIFrame

class PoolInfoFrame(BaseUIFrame):
    """Widget 8: กล่องข้อมูลคำนวณการดรอป 4 แถว (Drop+BOOTs, พื้นฐาน, อัตราดรอป, Stock/Charge)"""
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, bg=app.trans_key, bd=1,
                         highlightbackground="#22c55e", highlightthickness=1, **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        self.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())

        # แถว 1: ⚡Drop+BOOTs
        f_row_exp = tk.Frame(self, bg=self.app.trans_key)
        f_row_exp.pack(fill=tk.X, padx=3, pady=(1, 1), anchor="center")
        f_row_exp.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.f_row_exp = f_row_exp

        self.lbl_exp_t = StrokeLabel(f_row_exp, text="⚡Drop+BOOTs", font=("Segoe UI", 6, "bold"),
                                     fg="#fbbf24", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
        self.lbl_exp_t.pack(side=tk.TOP, anchor="center")
        self.lbl_exp_t.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_exp_t = self.lbl_exp_t

        self.lbl_boost_expected = StrokeLabel(f_row_exp, text=" --", font=("Consolas", 9, "bold"),
                                              fg="#facc15", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
        self.lbl_boost_expected.pack(side=tk.TOP, anchor="center", padx=(0, 0))
        self.lbl_boost_expected.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_boost_expected = self.lbl_boost_expected

        # แถว 2: ดรอปพื้นฐาน และ +1
        f_row_sure = tk.Frame(self, bg=self.app.trans_key)
        f_row_sure.pack(fill=tk.X, padx=3, pady=1, anchor="center")
        f_row_sure.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.f_row_sure = f_row_sure

        f_sure_part1 = tk.Frame(f_row_sure, bg=self.app.trans_key)
        f_sure_part1.pack(side=tk.TOP, anchor="center")
        f_sure_part1.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.f_sure_part1 = f_sure_part1

        coin_mini = self.app.get_neso_coin_photo(size=13)
        if coin_mini:
            lbl_sure_ico = tk.Label(f_sure_part1, image=coin_mini, bg=self.app.trans_key)
            lbl_sure_ico.image = coin_mini
            lbl_sure_ico.pack(side=tk.LEFT, padx=(0, 2))
            lbl_sure_ico.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
            self.lbl_sure_ico = lbl_sure_ico

        self.lbl_sure_t = StrokeLabel(f_sure_part1, text="[พื้นฐาน] ", font=("Segoe UI", 6, "bold"),
                                     fg="#38bdf8", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
        self.lbl_sure_t.pack(side=tk.LEFT)
        self.lbl_sure_t.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_sure_t = self.lbl_sure_t

        self.lbl_boost_sure_val = StrokeLabel(f_sure_part1, text="--", font=("Consolas", 9, "bold"),
                                              fg="#ffffff", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
        self.lbl_boost_sure_val.pack(side=tk.LEFT)
        self.lbl_boost_sure_val.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_boost_sure_val = self.lbl_boost_sure_val

        f_sure_part2 = tk.Frame(f_row_sure, bg=self.app.trans_key)
        f_sure_part2.pack(side=tk.TOP, anchor="center", pady=(1, 0))
        f_sure_part2.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.f_sure_part2 = f_sure_part2

        self.lbl_sure_p = StrokeLabel(f_sure_part2, text="+ ", font=("Segoe UI", 6, "bold"),
                                     fg="#94a3b8", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
        self.lbl_sure_p.pack(side=tk.LEFT)
        self.lbl_sure_p.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_sure_p = self.lbl_sure_p

        self.lbl_extra_t = StrokeLabel(f_sure_part2, text="[+1] ", font=("Segoe UI", 6, "bold"),
                                      fg="#4ade80", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
        self.lbl_extra_t.pack(side=tk.LEFT)
        self.lbl_extra_t.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_extra_t = self.lbl_extra_t

        self.lbl_boost_sure_rate = StrokeLabel(f_sure_part2, text="--", font=("Consolas", 9, "bold"),
                                               fg="#4ade80", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
        self.lbl_boost_sure_rate.pack(side=tk.LEFT)
        self.lbl_boost_sure_rate.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_boost_sure_rate = self.lbl_boost_sure_rate

        # แถว 3: 📊 อัตราดรอป
        f_row_rate = tk.Frame(self, bg=self.app.trans_key)
        f_row_rate.pack(fill=tk.X, padx=3, pady=1, anchor="center")
        f_row_rate.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.f_row_rate = f_row_rate

        f_rate_part1 = tk.Frame(f_row_rate, bg=self.app.trans_key)
        f_rate_part1.pack(side=tk.TOP, anchor="center")
        self.f_rate_part1 = f_rate_part1

        self.lbl_rate_t = StrokeLabel(f_rate_part1, text="📊 ", font=("Segoe UI", 6),
                                     fg="#94a3b8", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
        self.lbl_rate_t.pack(side=tk.LEFT)
        self.lbl_rate_t.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_rate_t = self.lbl_rate_t

        self.lbl_boost_rate_total = StrokeLabel(f_rate_part1, text=" --%", font=("Consolas", 6, "bold"),
                                                fg="#38bdf8", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
        self.lbl_boost_rate_total.pack(side=tk.LEFT)
        self.lbl_boost_rate_total.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_boost_rate_total = self.lbl_boost_rate_total

        f_rate_part2 = tk.Frame(f_row_rate, bg=self.app.trans_key)
        f_rate_part2.pack(side=tk.TOP, anchor="center", padx=(0, 0))
        self.f_rate_part2 = f_rate_part2

        self.lbl_boost_rate_breakdown = StrokeLabel(f_rate_part2, text=" (--% + --%)", font=("Consolas", 6),
                                                    fg="#fb923c", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
        self.lbl_boost_rate_breakdown.pack(side=tk.LEFT)
        self.lbl_boost_rate_breakdown.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_boost_rate_breakdown = self.lbl_boost_rate_breakdown

        # แถว 4: 📦 Stock & Per/Round
        f_row_stk = tk.Frame(self, bg=self.app.trans_key)
        f_row_stk.pack(fill=tk.X, padx=3, pady=1, anchor="center")
        f_row_stk.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.f_row_stk = f_row_stk

        f_stk_part1 = tk.Frame(f_row_stk, bg=self.app.trans_key)
        f_stk_part1.pack(side=tk.TOP, anchor="center")
        self.f_stk_part1 = f_stk_part1

        self.lbl_stk_t = StrokeLabel(f_stk_part1, text="📦 ", font=("Segoe UI", 6),
                                    fg="#94a3b8", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
        self.lbl_stk_t.pack(side=tk.LEFT)
        self.lbl_stk_t.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_stk_t = self.lbl_stk_t

        self.lbl_neso_boost_stock = StrokeLabel(f_stk_part1, text=" --- NESO", font=("Consolas", 6, "bold"),
                                                fg="#38ef7d", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
        self.lbl_neso_boost_stock.pack(side=tk.LEFT)
        self.lbl_neso_boost_stock.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_neso_boost_stock = self.lbl_neso_boost_stock

        f_stk_part2 = tk.Frame(f_row_stk, bg=self.app.trans_key)
        f_stk_part2.pack(side=tk.TOP, anchor="center", padx=(0, 0))
        self.f_stk_part2 = f_stk_part2

        self.lbl_chg_t = StrokeLabel(f_stk_part2, text="Per/Round =", font=("Segoe UI", 4),
                                    fg="#64748b", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
        self.lbl_chg_t.pack(side=tk.LEFT)
        self.lbl_chg_t.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_chg_t = self.lbl_chg_t

        self.lbl_neso_boost_charge = StrokeLabel(f_stk_part2, text="---", font=("Consolas", 6, "bold"),
                                                 fg="#38bdf8", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
        self.lbl_neso_boost_charge.pack(side=tk.LEFT)
        self.lbl_neso_boost_charge.bind("<Button-1>", lambda e: self.app.fetch_drop_data_async())
        self.app.lbl_neso_boost_charge = self.lbl_neso_boost_charge
