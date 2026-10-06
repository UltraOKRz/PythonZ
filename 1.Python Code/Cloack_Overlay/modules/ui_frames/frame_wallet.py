import tkinter as tk
from .base import BaseUIFrame

class WalletFrame(BaseUIFrame):
    """Widget 4: กล่องแสดงยอดเงิน NESO & Nesolet ประจำกระเป๋า"""
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, bg="#08101a", **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        # กล่องกระเป๋า NESO
        f_wal_neso = tk.Frame(self, bg="#1a1c29", bd=1, relief="solid", cursor="hand2")
        f_wal_neso.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0, 1))
        f_wal_neso.bind("<Button-1>", lambda e: self.app.open_wallet_inapp_modal())

        self.lbl_wallet_neso_val = tk.Label(f_wal_neso, text=f"{self.app.wallet_neso_compact}\nNESO",
                                            font=("Consolas", 13, "bold"), fg="#c084fc", bg="#1a1c29", justify="center", padx=1, pady=1)
        self.lbl_wallet_neso_val.pack(anchor="center")
        self.lbl_wallet_neso_val.bind("<Button-1>", lambda e: self.app.open_wallet_inapp_modal())
        self.app.lbl_wallet_neso_val = self.lbl_wallet_neso_val

        # กล่อง Nesolet
        f_wal_nesolet = tk.Frame(self, bg="#231433", bd=1, relief="solid")
        f_wal_nesolet.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(1, 0))

        self.lbl_nesolet = tk.Label(f_wal_nesolet, text=f"{self.app.wallet_nesolet_compact}\nNesolet",
                                    font=("Consolas", 13, "bold"), fg="#d8b4fe", bg="#231433", justify="center", padx=1, pady=1)
        self.lbl_nesolet.pack(anchor="center")
        self.app.lbl_nesolet = self.lbl_nesolet

    def update_wallet_display(self, neso_compact, nesolet_compact):
        if hasattr(self, 'lbl_wallet_neso_val') and self.lbl_wallet_neso_val.winfo_exists():
            self.lbl_wallet_neso_val.config(text=f"{neso_compact}\nNESO")
        if hasattr(self, 'lbl_nesolet') and self.lbl_nesolet.winfo_exists():
            self.lbl_nesolet.config(text=f"{nesolet_compact}\nNesolet")
