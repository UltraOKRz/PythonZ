# modules/ocr_engine.py
# OCR Engine Mixin: OCR สแกนชื่อตัวละคร, สแกนชื่อแมพ/แชนแนล, เครื่องมือ Crop กรอบ
import os
import sys
import json
import time
import math
import difflib
import asyncio
import threading
import urllib
import urllib.request
import urllib.parse
import re
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import mss
import win32gui
import winocr

from modules.common import StrokeLabel, format_compact_number

class OcrEngineMixin:
    def open_ocr_crop_tool(self):
        """(ระบบตั้งค่ากรอบ OCR แบบปรับเส้นอิสระ + ปุ่มบันทึก)"""
        self.play_alert(800, 100)
        self.crop_win = tk.Toplevel(self.root)
        self.crop_win.attributes("-fullscreen", True)
        self.crop_win.attributes("-alpha", 0.5)
        self.crop_win.config(bg="black")
        self.crop_win.attributes("-topmost", True)

        canvas = tk.Canvas(self.crop_win, bg="black", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        def cancel_crop(e=None):
            if getattr(self, 'crop_win', None) and self.crop_win.winfo_exists():
                self.crop_win.destroy()

        # 1. ค้นหาพิกัดหน้าต่างเกมเพื่ออ้างอิงตำแหน่ง
        game_rect = None
        hwnd = None
        def enum_cb(h, _):
            nonlocal hwnd
            if win32gui.IsWindowVisible(h) and not win32gui.IsIconic(h):
                title = win32gui.GetWindowText(h)
                t_lower = title.lower()
                if "maplestory" in t_lower and not any(x in t_lower for x in ["visual studio", ".pyw", ".py", ".md", "antigravity", "cursor", "cmd.exe", "powershell"]):
                    hwnd = h
        try:
            win32gui.EnumWindows(enum_cb, None)
            if hwnd:
                game_rect = win32gui.GetWindowRect(hwnd)
        except Exception:
            pass

        # 2. คำนวณพิกัดเริ่มต้นของกรอบ
        sw = self.crop_win.winfo_screenwidth()
        sh = self.crop_win.winfo_screenheight()

        # ค่าเริ่มต้นถ้าไม่มีข้อมูลเดิม
        if game_rect:
            def_x1 = game_rect[0] + 8
            def_y1 = game_rect[1] + 32
        else:
            def_x1 = 100
            def_y1 = 100
        def_w = 270
        def_h = 80

        reg = getattr(self, 'custom_ocr_region', None)
        if isinstance(reg, dict):
            if game_rect:
                box_x1 = game_rect[0] + reg.get('x', 8)
                box_y1 = game_rect[1] + reg.get('y', 32)
            else:
                abs_c = reg.get('abs', None)
                if abs_c and len(abs_c) == 4:
                    box_x1, box_y1 = abs_c[0], abs_c[1]
                else:
                    box_x1 = reg.get('x', def_x1)
                    box_y1 = reg.get('y', def_y1)
            box_w = reg.get('w', def_w)
            box_h = reg.get('h', def_h)
            box_x2 = box_x1 + box_w
            box_y2 = box_y1 + box_h
            
            # เส้นแบ่งไอคอนและเส้นแบ่งกลาง
            icon_w_saved = reg.get('icon_w', min(50, max(32, int(box_h * 0.5))))
            box_icon_x = box_x1 + icon_w_saved
            red_box = reg.get('red_box')
            if red_box and len(red_box) == 4:
                box_mid_y = box_y1 + red_box[3]
            else:
                box_mid_y = box_y1 + (box_h // 2)
        else:
            box_x1 = def_x1
            box_y1 = def_y1
            box_x2 = def_x1 + def_w
            box_y2 = def_y1 + def_h
            box_icon_x = box_x1 + 44
            box_mid_y = box_y1 + (def_h // 2)

        # ป้องกันค่าเพี้ยนออกนอกจอ
        box_x1 = max(0, min(box_x1, sw - 100))
        box_y1 = max(60, min(box_y1, sh - 60))
        box_x2 = max(box_x1 + 60, min(box_x2, sw - 10))
        box_y2 = max(box_y1 + 40, min(box_y2, sh - 10))
        box_icon_x = max(box_x1 + 20, min(box_icon_x, box_x2 - 30))
        box_mid_y = max(box_y1 + 15, min(box_mid_y, box_y2 - 15))

        active_drag = None
        drag_start_x = 0
        drag_start_y = 0
        orig_coords = {}

        # 3. ฟังก์ชันวาดเส้นไกด์ไลน์ (Interactive Guidelines)
        def redraw_guides():
            canvas.delete("guidelines")
            w = box_x2 - box_x1
            h = box_y2 - box_y1

            # 🟡 1. Master Header Frame (กรอบเหลือง)
            canvas.create_rectangle(box_x1, box_y1, box_x2, box_y2, outline="#facc15", width=2, tags="guidelines")
            # 🟢 หมุดตั้งต้นมุมบนซ้าย
            canvas.create_rectangle(box_x1 - 2, box_y1 - 2, box_x1 + 12, box_y1 + 12, fill="#22c55e", outline="#ffffff", width=1, tags="guidelines")

            # 🔘 2. กล่องไอคอนด้านซ้าย (Icon Box)
            canvas.create_rectangle(box_x1 + 2, box_y1 + 2, box_icon_x - 1, box_y2 - 2, outline="#eab308", width=1, dash=(3, 2), tags="guidelines")
            canvas.create_text(box_x1 + ((box_icon_x - box_x1) // 2), box_y1 + (h // 2), text="Icon", fill="#cbd5e1", font=("Segoe UI", 9, "bold"), tags="guidelines")

            # 🔴 3. กล่องสีแดง (Main Zone แถวบน เช่น Scrapyard)
            canvas.create_rectangle(box_icon_x + 2, box_y1 + 2, box_x2 - 2, box_mid_y - 1, outline="#ef4444", width=2, tags="guidelines")
            canvas.create_text(box_icon_x + 6, box_y1 + 3, text="🔴 Main Zone (โซนใหญ่)", fill="#ef4444", font=("Segoe UI", 8, "bold"), anchor="nw", tags="guidelines")

            # 🔵 4. กล่องสีฟ้า (Sub Map แถวล่าง เช่น Scrapyard Entrance)
            canvas.create_rectangle(box_icon_x + 2, box_mid_y + 1, box_x2 - 2, box_y2 - 2, outline="#38bdf8", width=2, tags="guidelines")
            canvas.create_text(box_icon_x + 6, box_mid_y + 3, text="🔵 Sub Map (จุดยืนจริง)", fill="#38bdf8", font=("Segoe UI", 8, "bold"), anchor="nw", tags="guidelines")

            # ↕️ 5. เส้นแบ่งกลาง (Mid Line Handle - ปรับระดับแบ่งแถว 1 กับ 2)
            canvas.create_line(box_icon_x, box_mid_y, box_x2, box_mid_y, fill="#ffffff", width=2, dash=(4, 2), tags="guidelines")
            canvas.create_oval(box_x2 - 12, box_mid_y - 4, box_x2 - 4, box_mid_y + 4, fill="#ffffff", outline="#0284c7", tags="guidelines")

            # ↔️ 6. เส้นแบ่งไอคอน (Icon Line Handle)
            canvas.create_line(box_icon_x, box_y1, box_icon_x, box_y2, fill="#eab308", width=2, dash=(4, 2), tags="guidelines")
            canvas.create_oval(box_icon_x - 4, box_y1 + 4, box_icon_x + 4, box_y1 + 12, fill="#eab308", outline="#ffffff", tags="guidelines")

            # 📏 ป้ายบอกขนาดและคำแนะนำ
            canvas.create_text(box_x1, max(50, box_y1 - 18), text=f"📍 Master Header: {w}x{h} px | ลากเส้นบน-ล่าง-กลาง เพื่อจัดระดับ", 
                               fill="#facc15", font=("Segoe UI", 10, "bold"), anchor="nw", tags="guidelines")

        # 4. ฟังก์ชันตรวจจับว่าเมาส์อยู่ใกล้เส้นไหน
        def get_hover_target(x, y):
            tol = 8 # ระยะความไวของเส้น
            # เส้นแบ่งกลาง
            if abs(y - box_mid_y) <= tol and (box_icon_x - 5 <= x <= box_x2 + 5):
                return 'mid'
            # ขอบบน
            if abs(y - box_y1) <= tol and (box_x1 - 5 <= x <= box_x2 + 5):
                return 'top'
            # ขอบล่าง
            if abs(y - box_y2) <= tol and (box_x1 - 5 <= x <= box_x2 + 5):
                return 'bottom'
            # เส้นแบ่งไอคอน
            if abs(x - box_icon_x) <= tol and (box_y1 - 5 <= y <= box_y2 + 5):
                return 'icon'
            # ขอบซ้าย
            if abs(x - box_x1) <= tol and (box_y1 - 5 <= y <= box_y2 + 5):
                return 'left'
            # ขอบขวา
            if abs(x - box_x2) <= tol and (box_y1 - 5 <= y <= box_y2 + 5):
                return 'right'
            # ในกรอบ (ย้ายตำแหน่งทั้งกรอบ)
            if (box_x1 < x < box_x2) and (box_y1 < y < box_y2):
                return 'move'
            return 'new'

        def on_mouse_motion(e):
            if active_drag:
                return
            tgt = get_hover_target(e.x, e.y)
            if tgt in ['top', 'bottom', 'mid']:
                canvas.config(cursor="size_ns")
            elif tgt in ['left', 'right', 'icon']:
                canvas.config(cursor="size_we")
            elif tgt == 'move':
                canvas.config(cursor="fleur")
            else:
                canvas.config(cursor="crosshair")

        def on_mouse_down(e):
            nonlocal active_drag, drag_start_x, drag_start_y, orig_coords
            drag_start_x = e.x
            drag_start_y = e.y
            active_drag = get_hover_target(e.x, e.y)
            orig_coords = {
                'x1': box_x1, 'y1': box_y1,
                'x2': box_x2, 'y2': box_y2,
                'icon_x': box_icon_x, 'mid_y': box_mid_y
            }

        def on_mouse_drag(e):
            nonlocal box_x1, box_y1, box_x2, box_y2, box_icon_x, box_mid_y
            if not active_drag:
                return

            dx = e.x - drag_start_x
            dy = e.y - drag_start_y

            if active_drag == 'top':
                # ลากเส้นขอบบน ขึ้น-ลง
                box_y1 = min(orig_coords['y1'] + dy, box_mid_y - 12)
            elif active_drag == 'bottom':
                # ลากเส้นขอบล่าง ขึ้น-ลง
                box_y2 = max(orig_coords['y2'] + dy, box_mid_y + 12)
            elif active_drag == 'mid':
                # ลากเส้นแบ่งกลาง ขึ้น-ลง (แบ่ง Main Zone กับ Sub Map)
                box_mid_y = max(box_y1 + 10, min(orig_coords['mid_y'] + dy, box_y2 - 10))
            elif active_drag == 'icon':
                # ลากเส้นแบ่งไอคอน ซ้าย-ขวา
                box_icon_x = max(box_x1 + 15, min(orig_coords['icon_x'] + dx, box_x2 - 30))
            elif active_drag == 'left':
                # ลากขอบซ้าย
                box_x1 = min(orig_coords['x1'] + dx, box_icon_x - 15)
            elif active_drag == 'right':
                # ลากขอบขวา
                box_x2 = max(orig_coords['x2'] + dx, box_icon_x + 30)
            elif active_drag == 'move':
                # ย้ายทั้งกรอบ
                box_x1 = orig_coords['x1'] + dx
                box_y1 = orig_coords['y1'] + dy
                box_x2 = orig_coords['x2'] + dx
                box_y2 = orig_coords['y2'] + dy
                box_icon_x = orig_coords['icon_x'] + dx
                box_mid_y = orig_coords['mid_y'] + dy
            elif active_drag == 'new':
                # วาดกรอบใหม่
                x1 = min(drag_start_x, e.x)
                y1 = min(drag_start_y, e.y)
                x2 = max(drag_start_x, e.x)
                y2 = max(drag_start_y, e.y)
                if (x2 - x1) >= 20 and (y2 - y1) >= 20:
                    box_x1, box_y1, box_x2, box_y2 = x1, y1, x2, y2
                    box_icon_x = box_x1 + min(50, max(30, int((y2 - y1) * 0.5)))
                    box_mid_y = box_y1 + ((y2 - y1) // 2)

            redraw_guides()

        def on_mouse_up(e):
            nonlocal active_drag
            active_drag = None
            on_mouse_motion(e)

        canvas.bind("<Motion>", on_mouse_motion)
        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)

        # 5. ฟังก์ชันบันทึกพิกัดเมื่อกดปุ่ม [ บันทึก ]
        def save_and_close():
            w = box_x2 - box_x1
            h = box_y2 - box_y1
            if w > 20 and h > 20:
                rel_x = (box_x1 - game_rect[0]) if game_rect else box_x1
                rel_y = (box_y1 - game_rect[1]) if game_rect else box_y1
                icon_w = max(10, box_icon_x - box_x1)
                
                # พิกัดกล่องสีแดงและกล่องสีฟ้าสัมพัทธ์กับกรอบนอก
                rx1 = icon_w + 2
                ry1 = 2
                rx2 = w - 2
                ry2 = max(ry1 + 5, (box_mid_y - box_y1) - 1)

                bx1 = icon_w + 2
                by1 = min(h - 5, (box_mid_y - box_y1) + 1)
                bx2 = w - 2
                by2 = h - 2

                self.custom_ocr_region = {
                    'x': rel_x,
                    'y': rel_y,
                    'w': w,
                    'h': h,
                    'abs': [box_x1, box_y1, box_x2, box_y2],
                    'icon_w': icon_w,
                    'red_box': [rx1, ry1, rx2, ry2],
                    'blue_box': [bx1, by1, bx2, by2]
                }
                self.save_config()
                self.play_alert(1000, 150)
                self.crop_win.destroy()
                # สแกนทันทีหลังบันทึก
                self.auto_detect_map_async()
            else:
                self.crop_win.destroy()

        def reset_to_game():
            nonlocal box_x1, box_y1, box_x2, box_y2, box_icon_x, box_mid_y
            if game_rect:
                box_x1 = game_rect[0] + 8
                box_y1 = game_rect[1] + 32
            else:
                box_x1 = 100
                box_y1 = 100
            box_x2 = box_x1 + 270
            box_y2 = box_y1 + 80
            box_icon_x = box_x1 + 44
            box_mid_y = box_y1 + 40
            redraw_guides()

        # 6. แถบควบคุมลอยด้านบนจอ (Floating Control Bar)
        ctrl_frame = tk.Frame(self.crop_win, bg="#0f172a", bd=1, relief="solid", highlightbackground="#38bdf8", highlightthickness=1)
        ctrl_frame.place(relx=0.5, y=28, anchor="n")

        lbl_tip = tk.Label(ctrl_frame, text="🖱️ ลากเส้น [ ขอบบน / ขอบล่าง / เส้นแบ่งกลาง / เส้นไอคอน ] ขึ้น-ลง หรือ ซ้าย-ขวา ปรับให้ตรงตามต้องการ", 
                           font=("Segoe UI", 11), fg="#94a3b8", bg="#0f172a", padx=10, pady=6)
        lbl_tip.pack(side=tk.LEFT)

        btn_save = tk.Button(ctrl_frame, text="💾 บันทึกกรอบ", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#10b981", 
                             activebackground="#059669", activeforeground="#ffffff", relief="flat", cursor="hand2", padx=12, pady=4,
                             command=save_and_close)
        btn_save.pack(side=tk.LEFT, padx=6, pady=4)

        btn_reset = tk.Button(ctrl_frame, text="🔄 รีเซ็ต", font=("Segoe UI", 11), fg="#e2e8f0", bg="#334155", 
                              activebackground="#475569", activeforeground="#ffffff", relief="flat", cursor="hand2", padx=8, pady=4,
                              command=reset_to_game)
        btn_reset.pack(side=tk.LEFT, padx=4, pady=4)

        btn_cancel = tk.Button(ctrl_frame, text="❌ ยกเลิก (ESC)", font=("Segoe UI", 11), fg="#f87171", bg="#1e293b", 
                               activebackground="#3d1b1b", activeforeground="#ffffff", relief="flat", cursor="hand2", padx=8, pady=4,
                               command=cancel_crop)
        btn_cancel.pack(side=tk.LEFT, padx=(4, 8), pady=4)

        # ผูกปุ่ม Esc และคลิกขวาเพื่อยกเลิก
        self.crop_win.bind("<Escape>", cancel_crop)
        canvas.bind("<Escape>", cancel_crop)
        canvas.bind("<ButtonPress-3>", cancel_crop)

        # วาดไกด์ไลน์ครั้งแรกทันที
        redraw_guides()
        self.crop_win.focus_force()
        canvas.focus_set()

    def open_char_crop_tool(self):
        """(ระบบตั้งค่ากรอบ OCR สำหรับสแกนชื่อตัวละคร)"""
        self.play_alert(800, 100)
        self.char_crop_win = tk.Toplevel(self.root)
        self.char_crop_win.attributes("-fullscreen", True)
        self.char_crop_win.attributes("-alpha", 0.5)
        self.char_crop_win.config(bg="black")
        self.char_crop_win.attributes("-topmost", True)

        canvas = tk.Canvas(self.char_crop_win, bg="black", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        def cancel_crop(e=None):
            if getattr(self, 'char_crop_win', None) and self.char_crop_win.winfo_exists():
                self.char_crop_win.destroy()

        # 1. ค้นหาพิกัดหน้าต่างเกมเพื่ออ้างอิงตำแหน่ง
        game_rect = None
        hwnd = None
        def enum_cb(h, _):
            nonlocal hwnd
            if win32gui.IsWindowVisible(h) and not win32gui.IsIconic(h):
                title = win32gui.GetWindowText(h)
                t_lower = title.lower()
                if "maplestory" in t_lower and not any(x in t_lower for x in ["visual studio", ".pyw", ".py", ".md", "antigravity", "cursor", "cmd.exe", "powershell"]):
                    hwnd = h
        try:
            win32gui.EnumWindows(enum_cb, None)
            if hwnd:
                game_rect = win32gui.GetWindowRect(hwnd)
        except Exception:
            pass

        sw = self.char_crop_win.winfo_screenwidth()
        sh = self.char_crop_win.winfo_screenheight()

        if game_rect:
            def_x1 = game_rect[0] + 70
            def_y1 = max(0, game_rect[3] - 70)
        else:
            def_x1 = 100
            def_y1 = sh - 150
        def_w = 140
        def_h = 32

        reg = getattr(self, 'custom_char_ocr_region', None)
        if isinstance(reg, dict):
            if game_rect:
                box_x1 = game_rect[0] + reg.get('x', 70)
                box_y1 = game_rect[1] + reg.get('y', game_rect[3] - game_rect[1] - 70)
            else:
                abs_c = reg.get('abs', None)
                if abs_c and len(abs_c) == 4:
                    box_x1, box_y1 = abs_c[0], abs_c[1]
                else:
                    box_x1 = reg.get('x', def_x1)
                    box_y1 = reg.get('y', def_y1)
            box_w = reg.get('w', def_w)
            box_h = reg.get('h', def_h)
            box_x2 = box_x1 + box_w
            box_y2 = box_y1 + box_h
        else:
            box_x1 = def_x1
            box_y1 = def_y1
            box_x2 = def_x1 + def_w
            box_y2 = def_y1 + def_h

        box_x1 = max(0, min(box_x1, sw - 80))
        box_y1 = max(0, min(box_y1, sh - 40))
        box_x2 = max(box_x1 + 40, min(box_x2, sw - 10))
        box_y2 = max(box_y1 + 15, min(box_y2, sh - 10))

        active_drag = None
        drag_start_x = 0
        drag_start_y = 0
        orig_coords = {}

        def redraw_guides():
            canvas.delete("char_guides")
            w = box_x2 - box_x1
            h = box_y2 - box_y1

            canvas.create_rectangle(box_x1, box_y1, box_x2, box_y2, outline="#ef4444", width=2, tags="char_guides")
            canvas.create_rectangle(box_x1 - 2, box_y1 - 2, box_x1 + 10, box_y1 + 10, fill="#ef4444", outline="#ffffff", width=1, tags="char_guides")
            canvas.create_rectangle(box_x2 - 10, box_y2 - 10, box_x2 + 2, box_y2 + 2, fill="#ef4444", outline="#ffffff", width=1, tags="char_guides")
            canvas.create_text(box_x1 + (w // 2), box_y1 + (h // 2), text="👤 ชื่อตัวละคร", fill="#fca5a5", font=("Segoe UI", 10, "bold"), tags="char_guides")
            canvas.create_text(box_x1, max(40, box_y1 - 18), text=f"👤 กรอบชื่อตัวละคร: {w}x{h} px (ครอบชื่อเหนือหลอดเลือด HP/MP)",
                               fill="#fca5a5", font=("Segoe UI", 10, "bold"), anchor="nw", tags="char_guides")

        def get_hover_target(x, y):
            tol = 8
            if abs(y - box_y1) <= tol and (box_x1 - 5 <= x <= box_x2 + 5):
                return 'top'
            if abs(y - box_y2) <= tol and (box_x1 - 5 <= x <= box_x2 + 5):
                return 'bottom'
            if abs(x - box_x1) <= tol and (box_y1 - 5 <= y <= box_y2 + 5):
                return 'left'
            if abs(x - box_x2) <= tol and (box_y1 - 5 <= y <= box_y2 + 5):
                return 'right'
            if (box_x1 < x < box_x2) and (box_y1 < y < box_y2):
                return 'move'
            return 'new'

        def on_mouse_motion(e):
            if active_drag:
                return
            tgt = get_hover_target(e.x, e.y)
            if tgt in ['top', 'bottom']:
                canvas.config(cursor="size_ns")
            elif tgt in ['left', 'right']:
                canvas.config(cursor="size_we")
            elif tgt == 'move':
                canvas.config(cursor="fleur")
            else:
                canvas.config(cursor="crosshair")

        def on_mouse_down(e):
            nonlocal active_drag, drag_start_x, drag_start_y, orig_coords
            drag_start_x = e.x
            drag_start_y = e.y
            active_drag = get_hover_target(e.x, e.y)
            orig_coords = {'x1': box_x1, 'y1': box_y1, 'x2': box_x2, 'y2': box_y2}

        def on_mouse_drag(e):
            nonlocal box_x1, box_y1, box_x2, box_y2
            if not active_drag:
                return
            dx = e.x - drag_start_x
            dy = e.y - drag_start_y

            if active_drag == 'top':
                box_y1 = min(orig_coords['y1'] + dy, box_y2 - 15)
            elif active_drag == 'bottom':
                box_y2 = max(orig_coords['y2'] + dy, box_y1 + 15)
            elif active_drag == 'left':
                box_x1 = min(orig_coords['x1'] + dx, box_x2 - 30)
            elif active_drag == 'right':
                box_x2 = max(orig_coords['x2'] + dx, box_x1 + 30)
            elif active_drag == 'move':
                box_x1 = orig_coords['x1'] + dx
                box_y1 = orig_coords['y1'] + dy
                box_x2 = orig_coords['x2'] + dx
                box_y2 = orig_coords['y2'] + dy
            elif active_drag == 'new':
                x1 = min(drag_start_x, e.x)
                y1 = min(drag_start_y, e.y)
                x2 = max(drag_start_x, e.x)
                y2 = max(drag_start_y, e.y)
                if (x2 - x1) >= 15 and (y2 - y1) >= 10:
                    box_x1, box_y1, box_x2, box_y2 = x1, y1, x2, y2

            redraw_guides()

        def on_mouse_up(e):
            nonlocal active_drag
            active_drag = None
            on_mouse_motion(e)

        canvas.bind("<Motion>", on_mouse_motion)
        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)

        def save_and_close():
            w = box_x2 - box_x1
            h = box_y2 - box_y1
            if w > 10 and h > 10:
                rel_x = (box_x1 - game_rect[0]) if game_rect else box_x1
                rel_y = (box_y1 - game_rect[1]) if game_rect else box_y1
                self.custom_char_ocr_region = {
                    'x': rel_x,
                    'y': rel_y,
                    'w': w,
                    'h': h,
                    'abs': [box_x1, box_y1, box_x2, box_y2]
                }
                self.save_config()
                self.play_alert(1000, 150)
                self.char_crop_win.destroy()
                self.log_cmd(f"บันทึกกรอบตัวละคร: {w}x{h} px")
                self.auto_detect_character_async(silent=False)
            else:
                self.char_crop_win.destroy()

        def reset_to_game():
            nonlocal box_x1, box_y1, box_x2, box_y2
            if game_rect:
                box_x1 = game_rect[0] + 70
                box_y1 = max(0, game_rect[3] - 70)
            else:
                box_x1 = 100
                box_y1 = sh - 150
            box_x2 = box_x1 + 140
            box_y2 = box_y1 + 32
            redraw_guides()

        # แถบควบคุมลอย
        ctrl_frame = tk.Frame(self.char_crop_win, bg="#0f172a", bd=1, relief="solid", highlightbackground="#ef4444", highlightthickness=1)
        ctrl_frame.place(relx=0.5, y=28, anchor="n")

        lbl_tip = tk.Label(ctrl_frame, text="🖱️ ลากกรอบสีแดงครอบ 'ชื่อตัวละคร' เหนือหลอดเลือด HP/MP",
                           font=("Segoe UI", 11), fg="#94a3b8", bg="#0f172a", padx=10, pady=6)
        lbl_tip.pack(side=tk.LEFT)

        btn_save = tk.Button(ctrl_frame, text="💾 บันทึกกรอบตัวละคร", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#10b981",
                             activebackground="#059669", activeforeground="#ffffff", relief="flat", cursor="hand2", padx=12, pady=4,
                             command=save_and_close)
        btn_save.pack(side=tk.LEFT, padx=6, pady=4)

        btn_reset = tk.Button(ctrl_frame, text="🔄 รีเซ็ต", font=("Segoe UI", 11), fg="#e2e8f0", bg="#334155",
                              activebackground="#475569", activeforeground="#ffffff", relief="flat", cursor="hand2", padx=8, pady=4,
                              command=reset_to_game)
        btn_reset.pack(side=tk.LEFT, padx=4, pady=4)

        btn_cancel = tk.Button(ctrl_frame, text="❌ ยกเลิก (ESC)", font=("Segoe UI", 11), fg="#f87171", bg="#1e293b",
                               activebackground="#3d1b1b", activeforeground="#ffffff", relief="flat", cursor="hand2", padx=8, pady=4,
                               command=cancel_crop)
        btn_cancel.pack(side=tk.LEFT, padx=(4, 8), pady=4)

        self.char_crop_win.bind("<Escape>", cancel_crop)
        canvas.bind("<Escape>", cancel_crop)
        canvas.bind("<ButtonPress-3>", cancel_crop)

        redraw_guides()
        self.char_crop_win.focus_force()
        canvas.focus_set()

    def auto_detect_character_async(self, silent=False):
        threading.Thread(target=self._run_auto_detect_character, args=(silent,), daemon=True).start()

    def _fetch_account_characters(self):
        try:
            if not self.wallet_addr:
                return []
            key = self.get_current_api_key()
            url = f"https://openapi.msu.io/v1rc1/accounts/{self.wallet_addr}/characters"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0", "x-nxopen-api-key": key},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                self.api_call_count += 1
                res = json.loads(resp.read().decode("utf-8"))
                if res.get("success"):
                    self.account_characters = res.get("data", {}).get("characters", [])
                    return self.account_characters
        except Exception as e:
            print("Fetch account characters error:", e)
        return []

    def _fetch_character_detail(self, asset_key, char_name, silent=False):
        try:
            key = self.get_current_api_key()
            url = f"https://openapi.msu.io/v1rc1/characters/{asset_key}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0", "x-nxopen-api-key": key},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                self.api_call_count += 1
                res = json.loads(resp.read().decode("utf-8"))
                if res.get("success"):
                    char = res.get("data", {}).get("character", {})
                    comm = char.get("common", {})
                    lvl = comm.get("level", 0)
                    job = comm.get("job", {}).get("jobName", "")
                    nesolet_raw = comm.get("nesolet", "0")
                    try:
                        nesolet_val = int(nesolet_raw) / (10**18)
                    except:
                        nesolet_val = 0.0

                    self.current_char_name = char_name
                    self.current_char_asset_key = asset_key
                    self.current_char_level = str(lvl)
                    self.current_char_job = job
                    self.current_char_nesolet_loaded = True
                    self.wallet_nesolet_str = f"{nesolet_val:,.1f}"
                    self.wallet_nesolet_compact = format_compact_number(nesolet_val)

                    if not silent:
                        self.log_cmd(f"✨ ตัวละคร: {char_name} (Lv.{lvl} {job})")
                        self.log_cmd(f"💰 Nesolet: {self.wallet_nesolet_str}")
                    self.save_config()
                    self.root.after(0, self.update_drop_ui)
        except Exception as e:
            if not silent:
                self.log_cmd(f"⚠️ รายละเอียดตัวละคร: {e}")

    def _auto_init_character(self):
        """กำหนดตัวละครอัตโนมัติจากกระเป๋า (เลือกตามชื่อที่จำไว้ หรือตัวละครเลเวลสูงสุด)"""
        try:
            chars = self._fetch_account_characters()
            if chars:
                target = None
                if getattr(self, 'current_char_name', ''):
                    target = next((c for c in chars if c.get('name', '').lower() == self.current_char_name.lower()), None)
                if not target:
                    target = max(chars, key=lambda c: c.get("data", {}).get("level", 0))
                if target:
                    a_key = target.get("assetKey")
                    c_name = target.get("name")
                    if a_key:
                        self.current_char_asset_key = a_key
                        self.current_char_name = c_name
                        self._fetch_character_detail(a_key, c_name, silent=True)
        except Exception as e:
            print("Auto init character error:", e)

    def _match_and_update_character(self, detected_name):
        if not getattr(self, 'account_characters', None):
            self._fetch_account_characters()

        chars = getattr(self, 'account_characters', [])
        if not chars:
            self.log_cmd("⚠️ ไม่พบรายชื่อตัวละครในกระเป๋า")
            return

        matched = None
        for c in chars:
            c_name = c.get('name', '')
            if c_name.lower() == detected_name.lower():
                matched = c
                break

        if not matched:
            for c in chars:
                c_name = c.get('name', '')
                if detected_name.lower() in c_name.lower() or c_name.lower() in detected_name.lower():
                    matched = c
                    break

        if not matched:
            names = [c.get('name', '') for c in chars]
            close = difflib.get_close_matches(detected_name, names, n=1, cutoff=0.5)
            if close:
                for c in chars:
                    if c.get('name') == close[0]:
                        matched = c
                        break

        if matched:
            asset_key = matched.get('assetKey')
            char_name = matched.get('name')
            self._fetch_character_detail(asset_key, char_name)
        else:
            self.log_cmd(f"⚠️ ไม่พบตัวละคร '{detected_name}' ในกระเป๋า")

    def _run_auto_detect_character(self, silent=False):
        if not hasattr(self, 'custom_char_ocr_region') or not self.custom_char_ocr_region:
            if not silent:
                self.log_cmd("⚠️ ยังไม่ได้ตั้งกรอบชื่อตัวละคร (กดปุ่ม 👤)")
            return

        hwnd = None
        def enum_cb(h, _):
            nonlocal hwnd
            if win32gui.IsWindowVisible(h) and not win32gui.IsIconic(h):
                title = win32gui.GetWindowText(h)
                t_lower = title.lower()
                if "maplestory" in t_lower and not any(x in t_lower for x in ["visual studio", ".pyw", ".py", ".md", "antigravity", "cursor", "cmd.exe", "powershell"]):
                    hwnd = h
        win32gui.EnumWindows(enum_cb, None)
        if not hwnd:
            if not silent:
                self.log_cmd("⚠️ ไม่พบหน้าต่างเกม")
            return

        try:
            rect = win32gui.GetWindowRect(hwnd)
            reg = self.custom_char_ocr_region
            if isinstance(reg, dict):
                crop_x = rect[0] + reg.get('x', 0)
                crop_y = rect[1] + reg.get('y', 0)
                crop_w = reg.get('w', 140)
                crop_h = reg.get('h', 32)
            elif isinstance(reg, (list, tuple)) and len(reg) == 4:
                crop_x, crop_y = reg[0], reg[1]
                crop_w, crop_h = reg[2] - reg[0], reg[3] - reg[1]
            else:
                return

            with mss.mss() as sct:
                monitor = {"top": crop_y, "left": crop_x, "width": crop_w, "height": crop_h}
                sct_img = sct.grab(monitor)
                pil_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

                up_w = pil_img.width * 2
                up_h = pil_img.height * 2
                up_img = pil_img.resize((up_w, up_h), Image.Resampling.BILINEAR)

                res = winocr.recognize_pil_sync(up_img, 'en')
                raw_text = res.get('text', '').strip() if res else ""
                clean_name = re.sub(r'[^a-zA-Z0-9]', '', raw_text)

                if not clean_name:
                    res_g = winocr.recognize_pil_sync(up_img.convert("L"), 'en')
                    raw_text = res_g.get('text', '').strip() if res_g else ""
                    clean_name = re.sub(r'[^a-zA-Z0-9]', '', raw_text)

                self.log_cmd(f"สแกนชื่อตัวละคร: '{clean_name or raw_text}'")
                if clean_name:
                    self._match_and_update_character(clean_name)
                else:
                    if not silent:
                        self.log_cmd("❌ ไม่พบชื่อในกรอบตัวละคร")
        except Exception as e:
            print("Char OCR error:", e)
            self.log_cmd(f"⚠️ สแกนตัวละครผิดพลาด: {e}")

    def auto_detect_map_async(self, silent=False):
        """กดปุ่ม 🔍 หรือรันอัตโนมัติเพื่อตรวจจับชื่อแมพแบบ Real-time"""
        threading.Thread(target=self._run_auto_detect_map, args=(silent,), daemon=True).start()

    def _run_auto_detect_map(self, silent=False):
        def set_btn_state(text, bg="#16202c", fg="#38bdf8"):
            if not silent and hasattr(self, 'btn_ocr') and self.btn_ocr and self.btn_ocr.winfo_exists():
                self.btn_ocr.config(text=text, bg=bg, fg=fg)
        
        if not silent:
            self.root.after(0, lambda: set_btn_state("⏳ Scan", bg="#0e2a38", fg="#38bdf8"))
            self.log_cmd("🔍 เริ่มตรวจจับแผนที่ในเกม...")
        
        # 1. ค้นหาหน้าต่างเกม MapleStory N (กรองไม่ให้จับ VS Code, IDE หรือ Terminal)
        hwnd = None
        def enum_cb(h, _):
            nonlocal hwnd
            if win32gui.IsWindowVisible(h) and not win32gui.IsIconic(h):
                title = win32gui.GetWindowText(h)
                t_lower = title.lower()
                if "maplestory" in t_lower and not any(x in t_lower for x in ["visual studio", ".pyw", ".py", ".md", "antigravity", "cursor", "cmd.exe", "powershell"]):
                    hwnd = h
        win32gui.EnumWindows(enum_cb, None)
        
        if not hwnd:
            if not silent:
                self.log_cmd("⚠️ ไม่พบหน้าต่างเกม MapleStory N")
                self.root.after(0, lambda: set_btn_state("❓ No Game", bg="#3d1b1b", fg="#f87171"))
                self.root.after(1600, lambda: set_btn_state("🔍 Scan", bg="#16202c", fg="#38bdf8"))
            return

        # 2. จับภาพเฉพาะบริเวณชื่อแมพมุมซ้ายบน
        try:
            rect = win32gui.GetWindowRect(hwnd)
            win_w = rect[2] - rect[0]
            win_h = rect[3] - rect[1]
            
            if hasattr(self, 'custom_ocr_region') and self.custom_ocr_region:
                reg = self.custom_ocr_region
                if isinstance(reg, dict):
                    crop_x = rect[0] + reg.get('x', 0)
                    crop_y = rect[1] + reg.get('y', 0)
                    crop_w = reg.get('w', 300)
                    crop_h = reg.get('h', 85)
                elif isinstance(reg, (list, tuple)) and len(reg) == 4:
                    crop_x = reg[0]
                    crop_y = reg[1]
                    crop_w = reg[2] - reg[0]
                    crop_h = reg[3] - reg[1]
                else:
                    crop_x = rect[0] + 8
                    crop_y = rect[1] + 32
                    crop_w = min(420, max(300, win_w // 3))
                    crop_h = 85
            else:
                crop_x = rect[0] + 8
                crop_y = rect[1] + 32
                crop_w = min(420, max(300, win_w // 3))
                crop_h = 85
            
            with mss.mss() as sct:
                monitor = {"top": crop_y, "left": crop_x, "width": crop_w, "height": crop_h}
                sct_img = sct.grab(monitor)
                pil_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                
                # -----------------------------------------------------
                # 🔍 Smart Icon Bypass OCR:
                # Mini Map ใน MapleStory N จะมีไอคอนโซนอยู่ด้านซ้ายสุด (~38-42px)
                # ด้านขวาของไอคอนจะเป็นข้อความ 2 บรรทัด:
                # - แถวที่ 1 (Main Zone): ชื่อโซนใหญ่ (ตรงกับ layerName ใน API)
                # - แถวที่ 2 (Sub Map): ชื่อสถานที่ย่อยที่กำลังยืนอยู่จริง
                # -----------------------------------------------------
                # -----------------------------------------------------
                # 🔍 Dual-Band Isolated OCR:
                # แยกอ่านอิสระ 2 กรอบตามคำสั่งผู้ใช้:
                # 🔴 ครึ่งบน (Top Frame): ชื่อโซนหลัก (Main Zone)
                # 🔵 ครึ่งล่าง (Bottom Frame): ชื่อแมพย่อย/จุดยืน (Sub Map)
                # -----------------------------------------------------
                reg_info = getattr(self, 'custom_ocr_region', None)
                red_box = reg_info.get('red_box') if isinstance(reg_info, dict) else None
                blue_box = reg_info.get('blue_box') if isinstance(reg_info, dict) else None

                raw_title = ""
                raw_sub = ""

                def clean_ocr_line(s):
                    # 1. ตัดอักขระพิเศษและอักขระเดี่ยวประเภทขอบเส้น (เช่น I, |, l, 1, !) ที่หัว-ท้าย
                    s = re.sub(r'^[Il|1!\s\-_~•\.:\(\)\[\]/\\;]+', '', s)
                    s = re.sub(r'[\s\-_\|~•\.:\(\)\[\]/\\;]+$', '', s)
                    # 2. ตัดคำซ้ำที่ติดกัน เช่น "Scrapyard Scrapyard Lot Scrapya" -> "Scrapyard Lot"
                    words = s.split()
                    dedup_words = []
                    for w in words:
                        clean_w = re.sub(r'[^a-zA-Z0-9]', '', w)
                        if not dedup_words or clean_w.lower() != re.sub(r'[^a-zA-Z0-9]', '', dedup_words[-1]).lower():
                            # ป้องกันเศษคำตัดท้ายที่ไม่สมบูรณ์ เช่น "Scrapya" ต่อท้าย "Scrapyard"
                            if dedup_words and len(clean_w) >= 3 and len(clean_w) < len(dedup_words[-1]) and dedup_words[-1].lower().startswith(clean_w.lower()):
                                continue
                            dedup_words.append(w)
                    return " ".join(dedup_words).strip()

                if red_box and blue_box and len(red_box) == 4 and len(blue_box) == 4:
                    rx1, ry1, rx2, ry2 = red_box
                    bx1, by1, bx2, by2 = blue_box
                    # ป้องกันไม่ให้พิกัดล้นขนาดรูปภาพ
                    rx1 = max(0, min(rx1, pil_img.width - 5))
                    rx2 = max(rx1 + 5, min(rx2, pil_img.width))
                    ry1 = max(0, min(ry1, pil_img.height - 5))
                    ry2 = max(ry1 + 5, min(ry2, pil_img.height))

                    bx1 = max(0, min(bx1, pil_img.width - 5))
                    bx2 = max(bx1 + 5, min(bx2, pil_img.width))
                    by1 = max(0, min(by1, pil_img.height - 5))
                    by2 = max(by1 + 5, min(by2, pil_img.height))

                    top_img = pil_img.crop((rx1, ry1, rx2, ry2))
                    bot_img = pil_img.crop((bx1, by1, bx2, by2))
                    ICON_OFFSET_X = rx1
                else:
                    # Fallback สัดส่วน Master Header
                    if pil_img.height >= 48:
                        top_bar_h = min(32, max(16, int(pil_img.height * 0.28)))
                        cy1 = top_bar_h
                        ch = pil_img.height - cy1
                    else:
                        top_bar_h = 0
                        cy1 = 0
                        ch = pil_img.height

                    ICON_OFFSET_X = min(50, max(32, int(ch * 0.82)))
                    mid_h = cy1 + (ch // 2)

                    top_img = pil_img.crop((ICON_OFFSET_X, cy1, pil_img.width, mid_h))
                    bot_img = pil_img.crop((ICON_OFFSET_X, mid_h, pil_img.width, pil_img.height))

                def recognize_with_upscale(img):
                    if not img or img.width < 5 or img.height < 5:
                        return "", []
                    # ขยายขนาด 2x เพื่อให้อ่านตัวอักษรขนาดเล็กได้คมชัด
                    up_w = img.width * 2
                    up_h = img.height * 2
                    up_img = img.resize((up_w, up_h), Image.Resampling.BILINEAR)
                    res = winocr.recognize_pil_sync(up_img, 'en')
                    lines = [clean_ocr_line(l.get('text', '')) for l in res.get('lines', []) if clean_ocr_line(l.get('text', ''))]
                    txt = clean_ocr_line(res.get('text', ''))
                    if not lines:
                        # ลองแบบ grayscale
                        res_g = winocr.recognize_pil_sync(up_img.convert("L"), 'en')
                        lines = [clean_ocr_line(l.get('text', '')) for l in res_g.get('lines', []) if clean_ocr_line(l.get('text', ''))]
                        txt = clean_ocr_line(res_g.get('text', ''))
                    return txt, lines

                # 1. ลองอ่านแยก 2 บรรทัดจากกล่องข้อความเต็ม (text_box_img) ด้วย line-aware OCR
                text_box_img = pil_img.crop((ICON_OFFSET_X, 0, pil_img.width, pil_img.height))
                full_txt, full_lines = recognize_with_upscale(text_box_img)

                if len(full_lines) >= 2:
                    raw_title = full_lines[0]
                    raw_sub = full_lines[1]
                else:
                    # 2. ถ้าได้บรรทัดเดียว ลองอ่านแยกจากกรอบ top_img และ bot_img
                    if top_img and bot_img and top_img.width > 10 and bot_img.width > 10:
                        _, top_lines = recognize_with_upscale(top_img)
                        _, bot_lines = recognize_with_upscale(bot_img)
                        if top_lines:
                            raw_title = top_lines[0]
                        if bot_lines:
                            raw_sub = bot_lines[0]

                    # 3. ถ้ายังได้บรรทัดเดียวหรือว่างเปล่า ให้ใช้ Smart Word Splitter แยก 2 บรรทัดอัตโนมัติ
                    base_str = raw_title if raw_title else full_txt
                    if base_str and not raw_sub:
                        # 3.1 ตรวจจับคีย์เวิร์ดเมือง/จุดยืนที่อยู่ท้ายข้อความ
                        for tw_kw in ["haven", "village", "town", "entrance", "shelter", "campsite", "square", "maze", "junction", "lot", "street"]:
                            match = re.search(r'\b(' + re.escape(tw_kw) + r'.*)$', base_str, re.IGNORECASE)
                            if match:
                                raw_title = base_str[:match.start()].strip()
                                raw_sub = match.group(1).strip()
                                break
                        
                        # 3.2 ตรวจจับคำซ้ำ เช่น "Black Heaven Black Heaven Maze 3"
                        if not raw_sub:
                            words = base_str.split()
                            if len(words) >= 4 and words[0].lower() == words[2].lower() and words[1].lower() == words[3].lower():
                                raw_title = f"{words[0]} {words[1]}"
                                raw_sub = " ".join(words[2:])
                            elif len(words) >= 2 and words[0].lower() == words[1].lower():
                                raw_title = words[0]
                                raw_sub = " ".join(words[1:])
                            else:
                                raw_title = base_str

                raw_text = f"{raw_title}\n{raw_sub}".strip()
                title_line = raw_title.lower()
                sub_line = raw_sub.lower()
                combined_text = (title_line + " " + sub_line).strip()
                print(f"[OCR-DualBand] Top (Main Zone)={repr(raw_title)} | Bot (Sub Map)={repr(raw_sub)}")
                if raw_title or raw_sub:
                    t_show = (raw_title[:15] + "..") if len(raw_title) > 15 else (raw_title if raw_title else "-")
                    s_show = (raw_sub[:15] + "..") if len(raw_sub) > 15 else (raw_sub if raw_sub else "-")
                    self.log_cmd(f"📷 OCR: [{t_show}] / [{s_show}]")
                else:
                    self.log_cmd("❌ OCR: ไม่พบข้อความในกรอบ")

                if not raw_title and not raw_sub:
                    if not silent:
                        self.root.after(0, lambda: set_btn_state("❌ No Match", bg="#3d1b1b", fg="#f87171"))
                        self.root.after(1600, lambda: set_btn_state("🔍 Scan", bg="#16202c", fg="#38bdf8"))
                    return

                # =====================================================
                # 🏙️ Phase 0: Interception Check - ตรวจสอบ Town & Safe Zone ก่อนเสมอ!
                # ตรวจสอบทั้งบรรทัดย่อย (sub_line) และข้อความรวม (combined_text)
                # =====================================================
                TOWN_OCR_KEYWORDS = [
                    # คีย์เวิร์ดทั่วไปของเซฟโซน/เมือง (ดักจับทุกแมพในเกม)
                    "town", "village", "haven", "shelter", "campsite", "entrance", "safe zone",
                    "safe", "square", "lobby", "waiting room", "party room", "market", "station",
                    # Arcane River Towns & Camps
                    "nameless", "chu chu", "chew chew", "chewchew", "chu village", "chew village", "slurpy house",
                    "lachelein", "hotel lachelein", "main street", "arcana", "harp village",
                    "spirit tree", "morass", "trueffet", "esfera", "base camp",
                    "cernium", "burnium", "hotel arcus", "karrote", "odium",
                    # Victoria Island & Ossyria
                    "henesys", "ellinia", "perion", "kerning", "lith harbor", "nautilus",
                    "sleepywood", "orbis", "el nath", "aqua road", "aquarium", "ludibrium",
                    "leafre", "ariant", "magatia", "herb town", "mu lung", "korean folk",
                    "ereve", "elluel", "pantheon", "fox village", "savage terminal", "ristonia"
                ]

                detected_town = False
                detected_town_name = "ในเมือง"
                
                # ตรวจจากคีย์เวิร์ดเมือง: ดูจากทั้ง sub_line, title_line และ combined_text
                for town_kw in TOWN_OCR_KEYWORDS:
                    if town_kw in sub_line or town_kw in combined_text or town_kw in title_line:
                        detected_town = True
                        if "haven" in town_kw:
                            detected_town_name = "Haven"
                        elif "chu" in town_kw or "chew" in town_kw:
                            detected_town_name = "Chu Chu Village"
                        elif "entrance" in town_kw:
                            detected_town_name = "ทางเข้า / เซฟโซน"
                        else:
                            detected_town_name = town_kw.title()
                        print(f"[OCR-Town] Detected safe town: {detected_town_name} (from keyword '{town_kw}')")
                        break

                if detected_town:
                    is_same_town = silent and self.is_in_town and (self.last_ocr_map_str == f"town:{detected_town_name}")
                    def apply_town(t_name=detected_town_name, s_name=raw_sub, same=is_same_town):
                        self.is_in_town = True
                        self.has_no_drop = True
                        self.current_town_name = t_name
                        self.detected_submap_name = s_name if s_name else t_name
                        self.selected_layer_name = f"🏙️ {t_name}" if t_name != "ในเมือง" else "🏙️ ในเมือง"
                        self.last_ocr_map_str = f"town:{t_name}"
                        if not same:
                            self.log_cmd(f"🏙️ เข้าเมือง: {t_name}")
                        else:
                            self.log_cmd(f"🏙️ ปลอดภัย: {t_name}")
                        if same:
                            self.update_drop_ui()
                        else:
                            self.setup_ui_elements()
                        if not silent:
                            btn_txt = f"🏙️ {t_name[:6]}" if t_name != "ในเมือง" else "🏙️ Town"
                            set_btn_state(btn_txt, bg="#1e293b", fg="#94a3b8")
                            self.root.after(1600, lambda: set_btn_state("🔍 Scan", bg="#16202c", fg="#38bdf8"))
                    self.root.after(0, apply_town)
                    return

                matched_item = None

                clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title_line).strip()
                clean_sub = re.sub(r'[^a-zA-Z0-9\s]', '', sub_line).strip()

                # =====================================================
                # 🗺️ Master Table: Global Sub-Map & Zone Alias ทั้งหมดใน MapleStory N
                # อ้างอิง layerId จริงจาก layers_cache.json ครอบคลุมทั้งโซนหลักและแมพย่อย
                # =====================================================
                GLOBAL_MAP_ALIASES = [
                    # --- Road of Vanishing / Arcane River (Arc. 30~100) ---
                    # 130002: "Extinction Zone"
                    (130002, ["weathered land of fire", "hidden fire zone", "extinction zone", "foot of the volcano",
                              "flame cliff", "fire river", "soul zone", "fire zone", "rocky area", "vanishing journey",
                              "extinction 1", "extinction 2", "extinction 3", "extinction"]),
                    # 130001: "Lake of Oblivion"
                    (130001, ["weathered land of happiness", "weathered land of rage", "weathered land of sadness",
                              "weathered land of joy", "cliff of rest", "lake of oblivion", "oblivion lake",
                              "restful rock", "vanishing lake", "oblivion"]),
                    # 130003: "Cave of Repose"
                    (130003, ["cave of repose", "below the cave", "hidden cave", "cave depths", "armas hideout",
                              "arma's hideout", "upper cave", "lower cave", "repose"]),
                    # 130004: "Underground" (Reverse City)
                    (130004, ["reverse city underground", "subway line 1", "subway line 2", "subway line 3",
                              "underground train", "tboys research lab", "t-boy's research lab", "subway track",
                              "underground", "subway", "train line", "t-boy"]),
                    # 130005: "Surface" (Reverse City)
                    (130005, ["reverse city surface", "surface 1", "surface 2", "surface 3", "hidden station",
                              "rooftop", "surface", "overpass"]),

                    # --- Chew Chew Island (Arc. 100~190) ---
                    # 131005: "Illiard Fungos"
                    (131005, ["slurpy forest depths", "slurpy forest", "illiard plains", "illiard fungos",
                              "one-a-bobber", "one a bobber", "bitty-bobber", "bitty bobber", "bobber 1", "bobber 2",
                              "slurpy", "fungos", "illiard"]),
                    # 131001: "Five-Color Hill"
                    (131001, ["five-color hill", "five color hill", "mottled forest 1", "mottled forest 2",
                              "mottled forest 3", "mottled forest", "colour hill", "hill path", "five-color", "five color", "mottled"]),
                    # 131002: "Eree Valley"
                    (131002, ["dealie-bobber forest", "dealie bobber forest", "eree valley 1", "eree valley 2",
                              "eree valley", "dealie-bobber", "dealie bobber", "dealie", "eree"]),
                    # 131003: "Skywhale Mountain"
                    (131003, ["skywhale mountain", "colossal root", "whale mountain", "skywhale peak",
                              "skywhale 1", "skywhale 2", "skywhale", "sky whale"]),
                    # 131004: "Mushbud Forest"
                    (131004, ["torrent zone 1", "torrent zone 2", "torrent zone 3", "torrent zone",
                              "mushbud forest", "mushbud 1", "mushbud 2", "mushbud"]),

                    # --- Lachelein (Arc. 190~240) ---
                    # 132001: "Lachelein Alley"
                    (132001, ["lachelein alleyway", "lachelein alley", "lachelein hideout", "backalley 1",
                              "backalley 2", "backalley 3", "backalley", "alley 1", "alley 2", "alley 3", "alleyway", "alley"]),
                    # 132002: "Lachelein Street"
                    (132002, ["occupied dance floor", "occupied dance", "theatre street", "victory plate",
                              "main street 1", "main street 2", "main street", "ballroom 1", "ballroom 2",
                              "ballroom 3", "ballroom", "lachelein street"]),
                    # 132003: "Lachelein Clocktower"
                    (132003, ["nightmare clocktower 1f", "nightmare clocktower 2f", "nightmare clocktower 3f",
                              "nightmare clocktower 4f", "nightmare clocktower 5f", "nightmare clocktower",
                              "lachelein clocktower", "clocktower 1f", "clocktower 2f", "clocktower 3f",
                              "clocktower 4f", "clocktower 5f", "clocktower 1", "clocktower 2", "clocktower 3",
                              "clocktower 4", "clocktower 5", "clocktower"]),

                    # --- Arcana (Arc. 280~360) ---
                    # 133001: "Near the Floral Flute"
                    (133001, ["between frost and lightning", "where fireflies dance", "forest of sunlight",
                              "forest of lightning", "forest of water", "forest of earth", "forest of frost",
                              "near the floral flute", "sun-drenched", "spirit tree", "spirit grove",
                              "floral flute", "fireflies", "flute"]),
                    # 133002: "Heart of the Forest"
                    (133002, ["grove of whispering", "tree of beginnings", "deep in the forest",
                              "heart of the forest", "heart of forest", "forest heart"]),
                    # 133003: "Cavernous Cavern"
                    (133003, ["deep in the cavern - lower path", "deep in the cavern - upper path",
                              "four-branch cave", "four branch cave", "cavern lower path", "cavern upper path",
                              "cavernous cavern", "deep cavern", "cavern lower", "cavern upper", "lower path", "upper path", "cavernous"]),

                    # --- Morass (Arc. 400~520) ---
                    # 134001: "Path to the Coral Forest"
                    (134001, ["path to the coral forest 1", "path to the coral forest 2", "path to the coral forest 3",
                              "path to the coral forest 4", "path to the coral forest 5", "path to the coral forest",
                              "path to the coral", "coral forest 1", "coral forest 2", "coral forest 3",
                              "coral forest 4", "coral forest 5", "coral forest", "coral path", "abandoned area"]),
                    # 134002: "Trueffet Street"
                    (134002, ["shadows of the swamp", "swamp of memory", "trueffet street", "bully boulevard",
                              "bully blvd 1", "bully blvd 2", "bully blvd 3", "bully blvd", "street 1", "street 2", "arpien"]),
                    # 134003: "Research Lab"
                    (134003, ["research laboratory", "research lab", "closed area", "laboratory 1", "laboratory 2", "laboratory", "lab"]),
                    # 134004: "That Day in Trueffet"
                    (134004, ["that day in trueffet 1", "that day in trueffet 2", "that day in trueffet 3",
                              "that day in trueffet 4", "that day in trueffet", "trueffet rampart", "that day 1",
                              "that day 2", "that day 3", "that day 4", "that day", "rampart", "castle wall"]),

                    # --- Esfera (Arc. 560~670) ---
                    # 135003: "Radiant Temple"
                    (135003, ["mirror light 1", "mirror light 2", "mirror light 3", "mirror light 4", "mirror light",
                              "living spring 1", "living spring 2", "living spring 3", "living spring",
                              "radiant temple", "temple of light", "mirror temple", "esfera temple"]),
                    # 136003: "Star-Swallowing Sea"
                    (136003, ["star-swallowing sea 1", "star-swallowing sea 2", "star-swallowing sea 3",
                              "star-swallowing sea", "deep mirror sea", "star-swallowing", "star swallowing",
                              "sea of tears", "esfera sea"]),

                    # --- Scrapyard & Black Heaven (Lv. 200~219) ---
                    # 122007: "Scrapyard, Black Heaven Inside 3"
                    (122007, ["black heaven junction 3", "black heaven inside 3", "black heaven inside 03", "scrapyard, black heaven inside 3",
                              "black heaven maze 7", "black heaven maze 6", "black heaven maze 5",
                              "maze 7", "maze 6", "maze 5", "junction 3", "inside 3", "inside 03", "deck 3", "bh inside 3", "bhi3"]),
                    # 122006: "Scrapyard, Black Heaven Inside 2"
                    (122006, ["black heaven junction 2", "black heaven inside 2", "black heaven inside 02", "scrapyard, black heaven inside 2",
                              "black heaven maze 4", "black heaven maze 3", "black heaven maze 2",
                              "maze 4", "maze 3", "maze 2", "junction 2", "inside 2", "inside 02", "deck 2", "bh inside 2", "bhi2"]),
                    # 122005: "Scrapyard, Black Heaven Inside 1"
                    (122005, ["black heaven junction 1", "black heaven inside 1", "black heaven inside 01", "scrapyard, black heaven inside 1",
                              "black heaven maze 1", "maze 1", "junction 1", "inside 1", "inside 01", "deck 1", "bh inside 1", "bhi1"]),
                    # 121002: "Scrapyard Skyline"
                    (121002, ["scrapyard skyline", "upper skyline", "skyline edge", "skyline 1", "skyline 2", "skyline"]),
                    # 121001: "Scrapyard"
                    (121001, ["scrapyard entrance", "scrapyard hill", "scrapyard lot", "scrapyard deck",
                              "scrapyard upper", "hillside 1", "hillside 2", "hillside", "scrapyard"]),

                    # --- Dark World Tree (Lv. 210~219) ---
                    # 122004: "Dark World Tree Top"
                    (122004, ["dark world tree top", "world tree top", "top branch", "upper stem", "dwt top", "tree top", "world tree 4"]),
                    # 122003: "Dark World Tree Mid Top"
                    (122003, ["dark world tree mid top", "world tree mid top", "upper left stem", "upper right stem",
                              "upper left", "upper right", "dwt mid top", "mid top", "world tree 3"]),
                    # 122002: "Dark World Tree Mid Bottom"
                    (122002, ["dark world tree mid bottom", "world tree mid bottom", "lower left stem", "lower right stem",
                              "lower left", "lower right", "dwt mid bottom", "mid bottom", "world tree 2"]),
                    # 122001: "Dark World Tree Bottom"
                    (122001, ["dark world tree bottom", "world tree bottom", "lower stem 1", "lower stem 2",
                              "lower stem 3", "lower stem", "tree bottom", "dwt bottom", "world tree 1"]),

                    # --- Twilight Perion / Fox Valley (Lv. 190~199) ---
                    # 120002: "Twilight Perion Excavation Area"
                    (120002, ["twilight perion excavation", "rough wilderness", "excavation area", "excavation site",
                              "wild cargo area", "wild cargo", "excavation 1", "excavation 2"]),
                    # 120001: "Twilight Perion"
                    (120001, ["deserted southern ridge", "twilight perion", "desolate hills", "perion ruins"]),
                    # 120003: "Fox Valley"
                    (120003, ["fox valley", "fox ridge", "fox tree", "fox forest"]),

                    # --- Kritias / Gate to the Future / Omega (Lv. 160~189) ---
                    # 118001: "Kritias"
                    (118001, ["ranheim", "kritias territory", "kritias northern", "kritias southern", "kritias"]),
                    # 117001: "Gate to the Future"
                    (117001, ["gate to the future", "henesys ruins", "dark ereve", "future henesys", "future perion", "future kerning"]),
                    # 117002: "Omega Sector"
                    (117002, ["omega sector", "boswell field", "command center", "robot zone", "hangar", "silo", "omega"]),

                    # --- Temple of Time / Kerning Tower (Lv. 140~169) ---
                    # 115001: "Temple of Time"
                    (115001, ["road of memory", "road of regret", "road of oblivion", "temple of time", "time temple"]),
                    # 115002: "Kerning Tower"
                    (115002, ["kerning square tower", "kerning tower floor", "kerning tower 2f", "kerning tower 3f",
                              "kerning tower 4f", "kerning tower 5f", "kerning tower 6f", "kerning tower",
                              "2f cafe", "2f café", "toy factory", "tower floor"]),

                    # --- Stone Colossus (Lv. 150~169) ---
                    # 116001: "Stone Colossus"
                    (116001, ["stone colossus", "stone golem", "colossus"]),

                    # --- Mu Lung / Korean Folk / Partem / Crimsonheart (Lv. 130~149) ---
                    # 114001: "Mu Lung Garden"
                    (114001, ["mu lung garden", "peach garden", "mu lung dojo", "snake area", "herb town", "mu lung"]),
                    # 114002: "Korean Folk Town"
                    (114002, ["korean folk town", "haunted house", "black mountain", "tiger forest", "korean folk", "folk town"]),
                    # 114003: "Dead Mine"
                    (114003, ["mine passage", "dead mine 1", "dead mine 2", "dead mine 3", "dead mine 4", "dead mine"]),
                    # 114004: "Golden Temple"
                    (114004, ["golden temple", "gold temple", "buddha"]),
                    # 114005: "Crimsonheart Castle"
                    (114005, ["crimsonheart castle", "crimsonheart", "crimson heart"]),
                    # 114006: "Partem"
                    (114006, ["partem ruins", "partem crater", "partem forest", "partem"]),

                    # --- Minar Forest / Dragon Forest (Lv. 120~159) ---
                    # 113001: "Minar Forest Dragon Forest"
                    (113001, ["minar forest dragon forest", "nest of dead dragon", "peak of the big horn", "peak of dragon",
                              "wyvern canyon", "wyvern valley", "dragon forest", "wyvern", "manon", "griffey"]),
                    # 113002: "Fantasy Theme World"
                    (113002, ["fantasy theme world", "fantasy theme park", "theme park", "fantasy world"]),

                    # --- Clocktower Bottom / Lion King (Lv. 110~139) ---
                    # 112001: "Clocktower Bottom Floor"
                    (112001, ["clocktower bottom floor", "warpped path of time", "forgotten path of time",
                              "path of time", "clocktower bottom", "clock tower bottom", "ludibrium clocktower"]),
                    # 112002: "Lion King's Castle"
                    (112002, ["lion king's castle", "lion king castle", "lionheart castle", "first tower",
                              "second tower", "third tower", "fourth tower", "fifth tower", "von leon", "lion king"]),

                    # --- Magatia / Heliseum / Ludibrium (Lv. 90~119) ---
                    # 110001: "Magatia"
                    (110001, ["alcadno research", "zenumist research", "magatia", "alcadno", "zenumist", "alchemy", "zern"]),
                    # 110002: "Ludibrium"
                    (110002, ["ludibrium", "toy world", "toy room", "eos tower", "helios tower", "ludi"]),
                    # 110003: "Ellin Forest"
                    (110003, ["deep fairy forest", "ancient forest", "ellin forest", "ellin"]),
                    # 110004: "Heliseum"
                    (110004, ["downtown black market", "heliseum", "beldar"]),

                    # --- Minar Forest / Aqua Road Deep / Tyrant (Lv. 100~119) ---
                    # 111001: "Minar Forest"
                    (111001, ["entrance to dragon forest", "dragon nest", "minar forest", "leafre", "beetle", "centipede"]),
                    # 111002: "Aqua Road Deep Sea"
                    (111002, ["mushroom coral hill", "aqua road deep sea", "deep sea gorge", "deep underwater",
                              "aqua dungeon", "deep sea", "submerged"]),
                    # 111003: "Heliseum Tyrant's Territory"
                    (111003, ["heliseum tyrant's territory", "tyrant's territory", "tyrant territory",
                              "tyrant's castle", "tyrant castle", "commander"]),

                    # --- Aqua Road / Sky Road / El Nath (Lv. 70~89) ---
                    # 108001: "Aqua Road"
                    (108001, ["crystal dunes", "aqua road", "aquarium", "seaweed"]),
                    # 108002: "Sky Road"
                    (108002, ["cloud park", "orbis tower", "sky road", "orbis"]),
                    # 108003: "El Nath Mountains"
                    (108003, ["el nath mountains", "sharp cliff", "snowfield", "cold field", "el nath"]),

                    # --- Nihal Desert / Verne Mine (Lv. 80~99) ---
                    # 109001: "Nihal Desert"
                    (109001, ["burning sands", "nihal desert", "ariant", "desert"]),
                    # 109002: "Verne Mine"
                    (109002, ["edelstein mine", "verne mine", "mine"]),

                    # --- Beginner Zones ---
                    # 107001: "Mushroom Castle"
                    (107001, ["mushroom castle", "mushroom shrine", "mushroom forest"]),
                    # 107002: "Sleepywood"
                    (107002, ["evil eye cave", "drakes chasm", "ant tunnel", "zombie dungeon", "sleepy wood", "sleepywood"]),
                    # 106001: "Perion"
                    (106001, ["warrior grounds", "rocky mountain", "wild boar land", "perion"]),
                    # 105001: "Kerning City"
                    (105001, ["kerning square", "sunset sky", "kerning subway", "kerning city", "kerning"]),
                    # 104001: "Gold Beach"
                    (104001, ["gold beach resort", "holiday resort", "gold beach", "beach"]),
                    # 104002: "Riena Strait"
                    (104002, ["riena strait", "riena", "ship"]),
                    # 104003: "Edelstein"
                    (104003, ["resistance hq", "edelstein"]),
                    # 104004: "Elodin"
                    (104004, ["elodin"]),
                    # 104005: "Ellinel"
                    (104005, ["ellinel fairy academy", "ellinel"]),
                    # 103001: "The Adventure Begins"
                    (103001, ["southperry beach", "the adventure begins", "adventure begins", "southperry", "amherst"]),
                    # 102001: "Prepare for Adventure"
                    (102001, ["prepare for adventure", "nautilus port"]),
                ]

                # =====================================================
                # 🎯 Phase 1: Sub-Map First Matching ผ่าน Global Aliases (ลำดับสำคัญสูงสุด!)
                # แถวล่าง (Sub Map) คือชื่อห้อง/สถานที่จริงที่เฉพาะเจาะจงที่สุด
                # =====================================================
                if clean_sub:
                    for target_lid, kw_list in GLOBAL_MAP_ALIASES:
                        # เรียงคีย์เวิร์ดจากยาวไปสั้น เพื่อให้ได้คำที่เฉพาะเจาะจงที่สุดก่อน
                        for kw in sorted(kw_list, key=len, reverse=True):
                            if kw in sub_line:
                                matched_item = next((item for item in self.layers_list if item["layerId"] == target_lid), None)
                                if matched_item:
                                    print(f"[OCR-SubMap] Sub-map direct match: {matched_item['layerName']} (ID: {matched_item['layerId']}) via '{kw}'")
                                    break
                        if matched_item:
                            break

                # =====================================================
                # 🎯 Phase 2: Combined Text Matching ผ่าน Global Aliases
                # (กรณีที่ Sub-Map สั้น หรือคำระบุแมพกระจายอยู่ทั้งสองบรรทัด)
                # =====================================================
                if not matched_item:
                    for target_lid, kw_list in GLOBAL_MAP_ALIASES:
                        for kw in sorted(kw_list, key=len, reverse=True):
                            if kw in combined_text:
                                matched_item = next((item for item in self.layers_list if item["layerId"] == target_lid), None)
                                if matched_item:
                                    print(f"[OCR-Alias] Combined match: {matched_item['layerName']} (ID: {matched_item['layerId']}) via '{kw}'")
                                    break
                        if matched_item:
                            break

                # =====================================================
                # 🎯 Phase 3: Exact Match 100% (คำตรงกันเป๊ะ ทั้ง Sub หรือ Combined)
                # ห้ามทำ clean_title in clean_lname เด็ดขาดเพื่อป้องกันชื่อสั้นชนชื่อยาว!
                # =====================================================
                if not matched_item:
                    for item in self.layers_list:
                        clean_lname = re.sub(r'[^a-zA-Z0-9\s]', '', item["layerName"].lower()).strip()
                        if clean_sub and clean_sub == clean_lname:
                            matched_item = item
                            print(f"[OCR-Exact] Sub-map exact match: {item['layerName']} (ID: {item['layerId']})")
                            break
                        if combined_text == clean_lname:
                            matched_item = item
                            print(f"[OCR-Exact] Combined exact match: {item['layerName']} (ID: {item['layerId']})")
                            break
                        if clean_title == clean_lname and not clean_sub:
                            matched_item = item
                            print(f"[OCR-Exact] Title exact match (solo): {item['layerName']} (ID: {item['layerId']})")
                            break

                # =====================================================
                # 🎯 Phase 4: Smart Zone Disambiguation (ป้องกันแมพที่มีหลาย Sub-Layer ซ้ำชื่อกัน)
                # =====================================================
                if not matched_item:
                    # 4.1 Black Heaven (Inside 1, 2, 3)
                    if "black heaven" in combined_text or "scrapyard" in combined_text:
                        if any(x in combined_text for x in ["inside 3", "junction 3", "maze 7", "maze 6", "maze 5", "deck 3"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 122007), None)
                        elif any(x in combined_text for x in ["inside 2", "junction 2", "maze 4", "maze 3", "maze 2", "deck 2"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 122006), None)
                        elif any(x in combined_text for x in ["inside 1", "junction 1", "maze 1", "deck 1"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 122005), None)
                        elif "skyline" in combined_text:
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 121002), None)
                        elif "scrapyard" in combined_text and not any(x in combined_text for x in ["inside", "junction", "maze", "deck"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 121001), None)
                        if matched_item:
                            print(f"[OCR-Disambig] Black Heaven/Scrapyard resolved: {matched_item['layerName']} (ID: {matched_item['layerId']})")

                    # 4.2 Dark World Tree (Bottom, Mid Bottom, Mid Top, Top)
                    elif "dark world tree" in combined_text or "world tree" in combined_text or "dwt" in combined_text:
                        if any(x in combined_text for x in ["mid top", "upper left", "upper right", "upper stem", "mid-top"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 122003), None)
                        elif any(x in combined_text for x in ["mid bottom", "lower left", "lower right", "mid-bottom", "mid bot"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 122002), None)
                        elif any(x in combined_text for x in ["top branch", "tree top", "dwt top"]) or (clean_sub and "top" in clean_sub):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 122004), None)
                        elif any(x in combined_text for x in ["bottom", "lower stem", "tree bottom", "dwt bottom"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 122001), None)
                        if matched_item:
                            print(f"[OCR-Disambig] Dark World Tree resolved: {matched_item['layerName']} (ID: {matched_item['layerId']})")

                    # 4.3 Lachelein (Alley, Street, Clocktower)
                    elif "lachelein" in combined_text:
                        if any(x in combined_text for x in ["clocktower", "nightmare", "tower"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 132003), None)
                        elif any(x in combined_text for x in ["street", "ballroom", "dance", "theatre", "plate"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 132002), None)
                        elif any(x in combined_text for x in ["alley", "hideout", "alleyway", "backalley"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 132001), None)
                        if matched_item:
                            print(f"[OCR-Disambig] Lachelein resolved: {matched_item['layerName']} (ID: {matched_item['layerId']})")

                    # 4.4 Twilight Perion (Main vs Excavation Area)
                    elif "twilight perion" in combined_text:
                        if any(x in combined_text for x in ["excavation", "wild cargo", "cargo", "wilderness"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 120002), None)
                        else:
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 120001), None)
                        if matched_item:
                            print(f"[OCR-Disambig] Twilight Perion resolved: {matched_item['layerName']} (ID: {matched_item['layerId']})")

                    # 4.5 Minar Forest (Main vs Dragon Forest)
                    elif "minar forest" in combined_text or "leafre" in combined_text:
                        if any(x in combined_text for x in ["dragon", "wyvern", "nest", "peak", "manon", "griffey"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 113001), None)
                        else:
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 111001), None)
                        if matched_item:
                            print(f"[OCR-Disambig] Minar Forest resolved: {matched_item['layerName']} (ID: {matched_item['layerId']})")

                    # 4.6 Aqua Road (Main vs Deep Sea)
                    elif "aqua road" in combined_text or "aquarium" in combined_text:
                        if any(x in combined_text for x in ["deep", "gorge", "underwater", "coral hill"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 111002), None)
                        else:
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 108001), None)
                        if matched_item:
                            print(f"[OCR-Disambig] Aqua Road resolved: {matched_item['layerName']} (ID: {matched_item['layerId']})")

                    # 4.7 Heliseum (Downtown vs Tyrant's Territory)
                    elif "heliseum" in combined_text:
                        if any(x in combined_text for x in ["tyrant", "castle", "commander"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 111003), None)
                        else:
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 110004), None)
                        if matched_item:
                            print(f"[OCR-Disambig] Heliseum resolved: {matched_item['layerName']} (ID: {matched_item['layerId']})")

                # =====================================================
                # 🎯 Phase 5: Direct LayerName Substring (ทิศทางเดียว: clean_lname in OCR text)
                # ชื่อ Layer ใน API ต้องปรากฏอยู่ในข้อความที่ OCR อ่านได้ และเลือกชื่อที่ยาวที่สุด
                # =====================================================
                if not matched_item:
                    best_sub_item = None
                    max_sub_len = 0
                    for item in self.layers_list:
                        clean_lname = re.sub(r'[^a-zA-Z0-9\s]', '', item["layerName"].lower()).strip()
                        if len(clean_lname) >= 6 and (clean_lname in clean_sub or clean_lname in combined_text):
                            if len(clean_lname) > max_sub_len:
                                max_sub_len = len(clean_lname)
                                best_sub_item = item
                    if best_sub_item:
                        matched_item = best_sub_item
                        print(f"[OCR-Substring] LayerName found in OCR text: {matched_item['layerName']} (ID: {matched_item['layerId']})")

                # =====================================================
                # 🎯 Phase 6: Multi-Tier Distinctive Word Scoring (Fallback สุดท้าย)
                # =====================================================
                if not matched_item:
                    GENERIC_TERMS = {
                        "forest", "valley", "mountain", "mountains", "hill", "hills", "path", "road", "street",
                        "alley", "cave", "entrance", "outskirts", "area", "zone", "sea", "lake", "river",
                        "deep", "depths", "top", "bottom", "mid", "middle", "floor", "inside", "cliff",
                        "peak", "station", "closed", "hideout", "castle", "tower", "garden", "town", "ruins", "field"
                    }
                    raw_words = re.findall(r'[a-zA-Z0-9]+', combined_text)
                    distinctive_words = [w for w in raw_words if len(w) >= 3 and w not in GENERIC_TERMS]

                    best_score = 0
                    best_item = None
                    for item in self.layers_list:
                        lname = item["layerName"].lower()
                        gname = item.get("groupName", "").lower()
                        score = 0
                        for w in distinctive_words:
                            if w in lname:
                                score += len(w) * 3
                            elif w in gname:
                                score += len(w) * 1.5
                        
                        if score > 0:
                            sim = difflib.SequenceMatcher(None, title_line if title_line else combined_text, lname).ratio()
                            score += sim * 4.0

                        if score > best_score:
                            best_score = score
                            best_item = item

                    if best_score >= 8.0:
                        matched_item = best_item
                        print(f"[OCR-Scoring] Distinctive word match: {matched_item['layerName']} (ID: {matched_item['layerId']}) (Score: {best_score:.1f})")
                            
                # ถ้าเจอ Field แน่นอน ให้ใช้ Field ทันที!
                if matched_item:
                    target_item = matched_item
                    is_layer_changed = (self.selected_layer_id != target_item["layerId"]) or self.is_in_town
                    is_sub_changed = bool(raw_sub and raw_sub.strip() != getattr(self, 'detected_submap_name', '').strip())
                    
                    if not is_layer_changed and not is_sub_changed and silent:
                        # 🛡️ แมพและห้องเดิมเป๊ะ: ไม่แตะต้องชื่อแมพ ไม่เปลี่ยนค่าใดๆ ทั้งสิ้น แต่ยิงแค่ API ดรอปเรทอย่างเดียว!
                        sub_info = f" ({self.detected_submap_name})" if getattr(self, 'detected_submap_name', '') else ""
                        self.log_cmd(f"📍 แมพเดิม: {target_item['layerName']}{sub_info}")
                        self.fetch_drop_data_async()
                        return
                    elif not is_layer_changed and is_sub_changed and silent:
                        # 🚪 อยู่ในโซนเดิมแต่เปลี่ยนห้องย่อย! อัปเดตชื่อห้องทันที
                        def update_submap_only(s_name=raw_sub):
                            self.detected_submap_name = s_name.strip() if s_name else ""
                            self.save_config()
                            self.update_drop_ui()
                            self.log_cmd(f"🚪 เปลี่ยนห้อง: {self.detected_submap_name}")
                        self.root.after(0, update_submap_only)
                        self.fetch_drop_data_async()
                        return

                    # กรณีเปลี่ยนแมพจริง หรือผู้ใช้กดปุ่ม Scan เอง:
                    def apply_match(s_name=raw_sub):
                        self.is_in_town = False  # ออกจากเมืองแล้ว - เคลียร์ flag
                        self.current_town_name = ""
                        self.detected_submap_name = s_name.strip() if s_name else ""
                        self.selected_layer_id = target_item["layerId"]
                        self.selected_layer_name = target_item["layerName"]
                        self.selected_group_name = target_item["groupName"]
                        self.last_ocr_map_str = f"field:{target_item['layerId']}"
                        sub_info = f" ({self.detected_submap_name})" if self.detected_submap_name else ""
                        self.log_cmd(f"🎯 แมตช์แมพ: {target_item['layerName']}{sub_info}")
                        self.save_config()
                        self.fetch_drop_data_async()
                        self.setup_ui_elements()
                        if not silent:
                            set_btn_state("✅ Matched", bg="#103823", fg="#4ade80")
                            self.root.after(1600, lambda: set_btn_state("🔍 Scan", bg="#16202c", fg="#38bdf8"))
                    
                    self.root.after(0, apply_match)
                    return



                # ลำดับที่ 3: ไม่ตรงทั้ง Field และ Town
                # 🛡️ หัวใจสำคัญ: ถ้าเป็นการ Auto-scan เบื้องหลัง (silent=True) ห้ามลบหรือเปลี่ยนแมพเดิมเด็ดขาด!
                if silent:
                    return

                # ผู้ใช้กดปุ่ม Scan Map เอง
                if raw_text and len(raw_text.strip()) >= 4:
                    def apply_fallback_town(s_name=raw_sub, t_text=raw_text.split('\n')[0].strip()):
                        self.is_in_town = True
                        self.has_no_drop = True
                        self.current_town_name = t_text if t_text else "ในเมือง"
                        self.detected_submap_name = s_name if s_name else t_text
                        self.selected_layer_name = f"🏙️ {self.current_town_name}"
                        self.setup_ui_elements()
                        set_btn_state("🏙️ Town", bg="#1e293b", fg="#94a3b8")
                        self.root.after(1600, lambda: set_btn_state("🔍 Scan", bg="#16202c", fg="#38bdf8"))
                    self.root.after(0, apply_fallback_town)
                else:
                    self.root.after(0, lambda: set_btn_state("❌ No Match", bg="#3d1b1b", fg="#f87171"))
                    self.root.after(1600, lambda: set_btn_state("🔍 Scan", bg="#16202c", fg="#38bdf8"))
                
        except Exception as e:
            print("OCR Error:", e)
            if not silent:
                self.root.after(0, lambda: set_btn_state("⚠️ Error", bg="#3d1b1b", fg="#f87171"))
                self.root.after(1600, lambda: set_btn_state("🔍 Scan", bg="#16202c", fg="#38bdf8"))
        finally:
            # เคลียร์ตัวแปรและคืนหน่วยความจำทันที ไม่ค้างในแรม
            if 'sct' in locals():
                try:
                    sct.close()
                except Exception:
                    pass

