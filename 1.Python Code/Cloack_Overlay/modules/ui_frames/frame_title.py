import tkinter as tk
from .base import BaseUIFrame

class TitleFrame(BaseUIFrame):
    """Widget 1: แถบ Title Bar ด้านบนสุด"""
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, bg="#121824", height=24, **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        # ลากหน้าต่าง
        self.bind("<ButtonPress-1>", self.app.start_drag)
        self.bind("<B1-Motion>", self.app.do_drag)
        self.bind("<ButtonRelease-1>", self.app.end_drag)

        # ปุ่มชิดขวา
        self.btn_close = tk.Label(self, text="✕", font=("Segoe UI", 9, "bold"), fg="#ff4d4f", bg="#121824", cursor="hand2", width=1)
        self.btn_close.pack(side=tk.RIGHT, padx=0)
        self.btn_close.bind("<Button-1>", lambda e: self.app.close_app())

        self.btn_mini = tk.Label(self, text="—", font=("Segoe UI", 9, "bold"), fg="#00f2fe", bg="#121824", cursor="hand2", width=1)
        self.btn_mini.pack(side=tk.RIGHT, padx=0)
        self.btn_mini.bind("<Button-1>", lambda e: self.app.toggle_compact_fold())

        self.btn_cfg = tk.Label(self, text="⚙", font=("Segoe UI", 9), fg="#94a3b8", bg="#121824", cursor="hand2", width=1)
        self.btn_cfg.pack(side=tk.RIGHT, padx=0)
        self.btn_cfg.bind("<Button-1>", lambda e: self.app.open_settings())

        self.btn_alpha = tk.Label(self, text="🌓", font=("Segoe UI", 9), fg="#38bdf8", bg="#121824", cursor="hand2", width=1)
        self.btn_alpha.pack(side=tk.RIGHT, padx=0)
        self.btn_alpha.bind("<Button-1>", lambda e: self.app.cycle_opacity())
        self.btn_alpha.bind("<Enter>", lambda e: self.btn_alpha.config(fg="#ffffff"))
        self.btn_alpha.bind("<Leave>", lambda e: self.btn_alpha.config(fg="#38bdf8"))

        # ฝั่งซ้าย: โลโก้/ป้าย COS สไตล์ Sidebar
        self.lbl_title = tk.Label(self, text="COS", font=("Segoe UI", 7, "bold"),
                                  fg="#00f2fe", bg="#16202c", relief="solid", bd=1,
                                  highlightbackground="#0284c7", highlightthickness=1,
                                  padx=4, pady=1)
        self.lbl_title.pack(side=tk.LEFT, padx=(3, 2))
        self.app.lbl_title = self.lbl_title

        srv_text = f"[{self.app.server_name[:1]}▾]"
        self.btn_srv = tk.Label(self, text=srv_text, font=("Consolas", 8, "bold"), fg="#f59e0b", bg="#121824", cursor="hand2")
        self.btn_srv.pack(side=tk.LEFT, padx=1)
        self.btn_srv.bind("<Button-1>", lambda e: self.app.show_server_dropdown(self.btn_srv))

        mode_tag = "ST" if self.app.mode == "ServerTime" else "MN"
        self.lbl_mode = tk.Label(self, text=f"[{mode_tag}▾]", font=("Consolas", 8, "bold"), 
                                 fg="#38ef7d" if self.app.mode == "ServerTime" else "#f59e0b", bg="#121824", cursor="hand2")
        self.lbl_mode.pack(side=tk.LEFT, padx=1)
        self.lbl_mode.bind("<Button-1>", lambda e: self.app.show_mode_dropdown(self.lbl_mode))

    def update_server_display(self, name):
        if hasattr(self, 'btn_srv') and self.btn_srv.winfo_exists():
            self.btn_srv.config(text=f"[{name[:1]}▾]")

    def update_mode_display(self, mode):
        if hasattr(self, 'lbl_mode') and self.lbl_mode.winfo_exists():
            mode_tag = "ST" if mode == "ServerTime" else "MN"
            self.lbl_mode.config(text=f"[{mode_tag}▾]", fg="#38ef7d" if mode == "ServerTime" else "#f59e0b")
