import tkinter as tk
from modules.common import StrokeLabel
from .base import BaseUIFrame

class TimerFrame(BaseUIFrame):
    """Widget 3: นาฬิกา 20 นาที แบบ Circular Ring + ปุ่ม Scan Map / Char OCR"""
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, has_resize_grip=True, bg=app.trans_key, bd=0, **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        self.bind("<ButtonPress-1>", self.app.start_drag)
        self.bind("<B1-Motion>", self.app.do_drag)
        self.bind("<ButtonRelease-1>", self.app.end_drag)

        self.lbl_t_header = StrokeLabel(self, text="⏱️ 20m Cycle", font=("Segoe UI", 6, "bold"),
                                        fg="#94a3b8", bg=self.app.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
        self.lbl_t_header.pack(pady=(1, 0))
        self.lbl_t_header.bind("<ButtonPress-1>", self.app.start_drag)
        self.lbl_t_header.bind("<B1-Motion>", self.app.do_drag)
        self.lbl_t_header.bind("<ButtonRelease-1>", self.app.end_drag)

        # 🕒 หลอดแคปซูลเวลานับถอยหลัง สไตล์นีออน HUD (ฝังตัวเลขนับเวลาขนาด 15 bold ไว้ข้างใน)
        self.canvas_timer_capsule = tk.Canvas(self, bg=self.app.trans_key, height=28, highlightthickness=0)
        self.canvas_timer_capsule.pack(fill=tk.X, padx=3, pady=(1, 2))
        self.canvas_timer_capsule.bind("<ButtonPress-1>", self.app.start_drag)
        self.canvas_timer_capsule.bind("<B1-Motion>", self.app.do_drag)
        self.canvas_timer_capsule.bind("<ButtonRelease-1>", self.app.end_drag)
        self.app.canvas_timer_capsule = self.canvas_timer_capsule
        self.app.canvas_timer_ring = self.canvas_timer_capsule # เพื่อ backward compatibility

        # ปุ่ม Scan Map & Char OCR
        f_timer_btns = tk.Frame(self, bg=self.app.trans_key)
        f_timer_btns.pack(pady=(1, 2), padx=2, fill=tk.X)

        self.btn_timer_scan = tk.Label(f_timer_btns, text="🔍 Map", font=("Segoe UI", 8, "bold"),
                                       fg="#38bdf8", bg="#16202c", relief="solid", bd=1, cursor="hand2", padx=2, pady=1)
        self.btn_timer_scan.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        self.btn_timer_scan.bind("<Button-1>", lambda e: self.app.trigger_scan_and_refresh())
        self.app.btn_timer_scan = self.btn_timer_scan

        self.btn_char_ocr = tk.Label(f_timer_btns, text="👤 Char", font=("Segoe UI", 8, "bold"),
                                     fg="#a855f7", bg="#1e1b2e", relief="solid", bd=1, cursor="hand2", padx=2, pady=1)
        self.btn_char_ocr.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.btn_char_ocr.bind("<Button-1>", lambda e: self.app.open_char_crop_tool())
        self.app.btn_char_ocr = self.btn_char_ocr

    def update_char_name(self, c_name):
        if hasattr(self, 'btn_char_ocr') and self.btn_char_ocr.winfo_exists():
            if c_name:
                disp_c = c_name if len(c_name) <= 9 else c_name[:8] + ".."
                self.btn_char_ocr.config(text=f"👤 {disp_c}", fg="#c084fc", bg="#2e1065")
            else:
                self.btn_char_ocr.config(text="👤 Char", fg="#a855f7", bg="#1e1b2e")
