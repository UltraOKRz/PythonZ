import tkinter as tk
from .base import BaseUIFrame

class StatusFooterFrame(BaseUIFrame):
    """Widget 10: แถบสถานะด้านล่างสุด (Real Time, NXPC Price, Ping)"""
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, bg="#08101a", bd=1, relief="solid",
                         highlightbackground="#1e293b", highlightthickness=1, **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        # เวลาปัจจุบัน
        self.lbl_real_time = tk.Label(self, text="00:00:00", font=("Consolas", 10, "bold"),
                                      fg="#38bdf8", bg="#08101a")
        self.lbl_real_time.pack(side=tk.LEFT, padx=(2, 1), pady=1)
        self.app.lbl_real_time = self.lbl_real_time

        # ราคา NXPC
        self.lbl_nxpc = tk.Label(self, text="NXPC: $--", font=("Consolas", 10, "bold"),
                                 fg="#f59e0b", bg="#08101a", cursor="hand2")
        self.lbl_nxpc.pack(side=tk.LEFT, padx=1, pady=1)
        self.lbl_nxpc.bind("<Button-1>", lambda e: self.app.toggle_nxpc_currency())
        self.app.lbl_nxpc = self.lbl_nxpc

        # ขีดคั่น
        tk.Label(self, text="|", font=("Consolas", 10), fg="#334155", bg="#08101a").pack(side=tk.LEFT, padx=0)

        # Server Ping
        self.lbl_ping = tk.Label(self, text="📶 --ms", font=("Consolas", 10, "bold"),
                                 fg="#94a3b8", bg="#08101a", cursor="hand2")
        self.lbl_ping.pack(side=tk.RIGHT, padx=(1, 2), pady=1)
        self.lbl_ping.bind("<Button-1>", lambda e: self.app.reset_api_counter())
        self.app.lbl_ping = self.lbl_ping

        # ขีดคั่น Ping กับ API Poll
        tk.Label(self, text="|", font=("Consolas", 10), fg="#334155", bg="#08101a").pack(side=tk.RIGHT, padx=0)

        # 🔄 API Polling Status (ย้ายมาจากแถบล่าง)
        self.lbl_poll_countdown = tk.Label(self, text="🔄 60s", font=("Consolas", 10, "bold"),
                                           fg="#94a3b8", bg="#08101a", cursor="hand2")
        self.lbl_poll_countdown.pack(side=tk.RIGHT, padx=(1, 2), pady=1)
        self.lbl_poll_countdown.bind("<Button-1>", lambda e: self.app.trigger_scan_and_refresh())
        self.app.lbl_poll_countdown = self.lbl_poll_countdown

    def update_clock(self, clock_str):
        if hasattr(self, 'lbl_real_time') and self.lbl_real_time.winfo_exists():
            self.lbl_real_time.config(text=clock_str)

    def update_nxpc(self, nxpc_str):
        if hasattr(self, 'lbl_nxpc') and self.lbl_nxpc.winfo_exists():
            self.lbl_nxpc.config(text=f"NXPC: {nxpc_str}")

    def update_ping(self, ping_str):
        if hasattr(self, 'lbl_ping') and self.lbl_ping.winfo_exists():
            self.lbl_ping.config(text=ping_str)
