# -*- coding: utf-8 -*-
"""
Mod: Farm Income Tracker & Daily 24h History
โฟลเดอร์: Mod/
หน้าต่างหลัก: 177 x 252 px (โหมดจับเวลาสด, ประวัติรอบฟาร์ม Manual & สถิติ 24 ชม.)
หน้าต่างประวัติย่อย: หน้าต่างแยก Scrollable พร้อมสรุปรายวัน ย้อนหลัง และคลิกดูรายละเอียดประวัติการ Mint แต่ละธุรกรรมได้
"""

import tkinter as tk
from tkinter import ttk
import os
import json
import time
from datetime import datetime, timezone
import urllib.request
import threading

MOD_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(MOD_DIR, "farm_history.json")

# สัญญาณ On-Chain สำหรับ MSU Henesys L1
# 100,000 NESO = 1 NXPC (อัตราคงที่ทางการของ MapleStory Universe)
NESO_PER_NXPC = 100000.0
# Smart Contract ของระบบ Mint เหรียญ NESO เข้ากระเป๋าผู้เล่น
MINTER_CONTRACT = "0x18dcf168258bd4794d99992581dd74677d4ff5bf"


class IncomeTrackerMod:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        
        # สถานะการจับเวลา Manual
        self.is_tracking = False
        self.start_ts = 0.0
        self.elapsed_sec = 0.0
        self.start_neso = 0.0
        self.last_known_wallet_neso = 0.0
        
        # 🪙 ระบบ Auto-Track NESOLET สดระดับตัวละคร (รองรับการสะสมยอด + ดักจับจังหวะ Mint ไม่ให้สปีดตก)
        self.session_farmed_nesolet = 0.0      # ยอดรวม NESOLET ที่ฟาร์มได้ในรอบนี้จริง
        self.last_char_nesolet = None          # ค่า NESOLET ล่าสุดที่อ่านได้จากตัวละคร
        self.session_mint_count = 0            # นับจำนวนครั้งที่มีการกด Mint ในรอบนี้
        
        # ข้อมูลตัดรอบประจำวัน (Server Reset 07:00 น. เวลาไทย = 00:00 UTC)
        self.history_data = self._load_history()
        self._check_daily_reset()
        
        # หน้าต่าง GUI
        self.win = None
        self.history_win = None
        self.is_usd_mode = False
        
        # State การกางดูรายละเอียดการ Mint ในหน้าประวัติ { "YYYY-MM-DD": True/False }
        self.expanded_days = {}
        self.current_history_tab = "daily" # 'daily' หรือ 'manual'
        
        # On-Chain Sync Controller
        self._last_onchain_sync = 0.0
        self._is_syncing_onchain = False
        
        # ดึงประวัติ On-chain ทันทีเมื่อเปิด
        self._fetch_onchain_mints_async()
        
        # เริ่มลูปอัปเดตเบื้องหลัง
        self._schedule_tick()

    def _load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "manual_sessions" not in data:
                        data["manual_sessions"] = []
                    return data
            except Exception as e:
                print("Load farm history error:", e)
        return {
            "last_reset_date": "",
            "start_day_neso": 0.0,
            "today_minted_neso": 0.0,
            "days": [],
            "manual_sessions": []
        }

    def _save_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Save farm history error:", e)

    def _get_current_server_date_str(self):
        """เวลาตัดรอบเซิร์ฟเวอร์: 07:00 น. เวลาไทย (UTC 00:00)"""
        now = datetime.now()
        if now.hour < 7:
            day_ts = time.time() - 86400
            return datetime.fromtimestamp(day_ts).strftime("%Y-%m-%d")
        else:
            return now.strftime("%Y-%m-%d")

    def _get_server_reset_timestamp(self):
        """คำนวณ Timestamp วินาทีของเวลา 07:00 น. (00:00 Server Time) ล่าสุด"""
        now = datetime.now()
        if now.hour < 7:
            yesterday = datetime.fromtimestamp(time.time() - 86400)
            reset_dt = datetime(yesterday.year, yesterday.month, yesterday.day, 7, 0, 0)
        else:
            reset_dt = datetime(now.year, now.month, now.day, 7, 0, 0)
        return int(reset_dt.timestamp())

    def _get_wallet_neso_float(self):
        """ดึงค่ายอดกระเป๋าจริง float จาก app"""
        w_val = getattr(self.app, 'wallet_neso_val', 0.0)
        if isinstance(w_val, (int, float)) and w_val > 0:
            return float(w_val)
        return 0.0

    def _get_character_nesolet_float(self):
        """ดึงค่ายอด NESOLET ในตัวละครปัจจุบัน float จาก app"""
        c_val = getattr(self.app, 'wallet_nesolet_val', None)
        if c_val is not None and isinstance(c_val, (int, float)):
            return float(c_val)
        # Fallback กรณีเก็บเป็น string เช่น "1,234.5"
        c_str = getattr(self.app, 'wallet_nesolet_str', '0')
        try:
            cleaned = str(c_str).replace(',', '').strip()
            if cleaned and cleaned != "...":
                return float(cleaned)
        except:
            pass
        return None

    def _fetch_onchain_mints_async(self):
        """ดึงประวัติการ Mint เหรียญ NESO จาก Henesys L1 Explorer แบบ Background Thread"""
        if self._is_syncing_onchain:
            return
        threading.Thread(target=self._fetch_onchain_mints_worker, daemon=True).start()

    def _fetch_onchain_mints_worker(self):
        self._is_syncing_onchain = True
        try:
            wallet = getattr(self.app, 'wallet_addr', '')
            if not wallet:
                try:
                    from modules.config import get_default_wallet
                    wallet = get_default_wallet()
                except Exception:
                    pass
            if not wallet:
                return

            curr_server_date = self._get_current_server_date_str()
            nxpc_u = getattr(self.app, 'nxpc_usd', 0.0)
            nxpc_b = getattr(self.app, 'nxpc_thb', 0.0)
            
            # ยิง Routescan EVM Explorer API สำหรับ Henesys L1 (Chain ID: 68414) ดึง 100 รายการล่าสุด
            url = (
                f"https://api.routescan.io/v2/network/mainnet/evm/68414/etherscan/api"
                f"?module=account&action=tokentx&address={wallet}&page=1&offset=100&sort=desc"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode("utf-8"))

            if res.get("status") == "1" and "result" in res:
                txs = res["result"]
                # จัดกลุ่มรายการ Mint ตามวันของ Server (ตัดรอบ 07:00 น. เวลาไทย = UTC 00:00:00)
                # แปลง timestamp เป็น UTC จะตรงกับวันของ Server เสมอ
                days_mints_map = {}
                for tx in txs:
                    if (tx.get("from", "").lower() == MINTER_CONTRACT.lower() and 
                        tx.get("to", "").lower() == wallet.lower()):
                        ts = int(tx.get("timeStamp", 0))
                        # Server Date ตามรอบ 07:00 น. TH คือ UTC วันเดียวกัน
                        dt_utc = datetime.fromtimestamp(ts, timezone.utc)
                        s_date = dt_utc.strftime("%Y-%m-%d")
                        val = int(tx.get("value", "0")) / (10**18)
                        t_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                        
                        if s_date not in days_mints_map:
                            days_mints_map[s_date] = []
                        days_mints_map[s_date].append({
                            "time": t_str,
                            "neso": round(val, 2),
                            "hash": tx.get("hash", "")
                        })

                # อัปเดตยอดของวันนี้สดๆ
                today_items = days_mints_map.get(curr_server_date, [])
                total_today = sum(i["neso"] for i in today_items)
                self.history_data["today_minted_neso"] = round(total_today, 2)
                self.history_data["last_reset_date"] = curr_server_date

                # สร้างรายการประวัติย้อนหลังทุกวัน (รวมวันนี้ด้วย)
                all_days_list = []
                # เรียงวันจากล่าสุดไปเก่าสุด
                sorted_dates = sorted(list(days_mints_map.keys()), reverse=True)
                for d in sorted_dates:
                    items = days_mints_map[d]
                    day_minted = sum(i["neso"] for i in items)
                    equiv_nxpc = day_minted / NESO_PER_NXPC
                    all_days_list.append({
                        "date": d,
                        "minted_neso": round(day_minted, 2),
                        "nxpc_usd": nxpc_u,
                        "nxpc_thb": nxpc_b,
                        "est_usd": round(equiv_nxpc * nxpc_u, 2),
                        "est_thb": round(equiv_nxpc * nxpc_b, 2),
                        "details": items
                    })

                self.history_data["days"] = all_days_list[:30]
                self._save_history()
                
                # หากหน้าต่างเปิดอยู่ ให้รีเฟรช UI ทั้งหน้าหลักและหน้าต่างประวัติ
                self.root.after(0, lambda: [
                    self._refresh_ui(self._get_wallet_neso_float()),
                    self._render_history_items()
                ])
        except Exception as e:
            print("Fetch onchain mints error:", e)
        finally:
            self._is_syncing_onchain = False
            self._last_onchain_sync = time.time()

    def _check_daily_reset(self):
        curr_server_date = self._get_current_server_date_str()
        last_date = self.history_data.get("last_reset_date", "")
        current_wallet = self._get_wallet_neso_float()

        if not last_date:
            self.history_data["last_reset_date"] = curr_server_date
            self.history_data["start_day_neso"] = current_wallet
            self._save_history()
        elif last_date != curr_server_date:
            self.history_data["last_reset_date"] = curr_server_date
            self.history_data["start_day_neso"] = current_wallet
            self.history_data["today_minted_neso"] = 0.0
            self._save_history()

    def _schedule_tick(self):
        self._update_logic()
        self.root.after(1000, self._schedule_tick)

    def _update_logic(self):
        self._check_daily_reset()
        current_wallet = self._get_wallet_neso_float()
        curr_nesolet = self._get_character_nesolet_float()
        
        # ดึงประวัติ Onchain ทุกๆ 30 วินาที เพื่ออัปเดตยอด Mint สดๆ
        if time.time() - self._last_onchain_sync > 30:
            self._fetch_onchain_mints_async()
        
        # คำนวณ Session Timer และสะสม NESOLET จากตัวละคร
        if self.is_tracking:
            self.elapsed_sec = time.time() - self.start_ts
            if self.start_neso == 0.0 and current_wallet > 0:
                self.start_neso = current_wallet
            
            # 🪙 ประมวลผล Delta ของ NESOLET ตัวละคร
            if curr_nesolet is not None:
                if self.last_char_nesolet is None:
                    self.last_char_nesolet = curr_nesolet
                else:
                    delta = curr_nesolet - self.last_char_nesolet
                    if delta > 0.0001:
                        # ฟาร์มได้เพิ่มขึ้นตามปกติ
                        self.session_farmed_nesolet += delta
                        self.last_char_nesolet = curr_nesolet
                    elif delta < -0.0001:
                        # 🚨 ยอดลดลง = มีการกด Mint NESOLET เป็น NESO!
                        # ป้องกันตัวเลขติดลบ: นำยอดเดิมที่หายไปมาบวกทบเข้ายอดสะสม
                        minted_part = max(0.0, self.last_char_nesolet - curr_nesolet)
                        self.session_farmed_nesolet += minted_part
                        self.session_mint_count += 1
                        self.last_char_nesolet = curr_nesolet
        else:
            # ถ้าไม่ได้กำลังฟาร์ม ให้ sync จุดอ้างอิงล่าสุดไว้ตลอด
            if curr_nesolet is not None:
                self.last_char_nesolet = curr_nesolet
        
        # อัปเดตหน้าต่างถ้าเปิดอยู่
        if self.win and self.win.winfo_exists():
            self._refresh_ui(current_wallet)

    def toggle_window(self):
        """เปิด/ปิด หน้าต่างหลักขนาด 177x252 px"""
        if self.win and self.win.winfo_exists():
            self.win.destroy()
            self.win = None
            return

        win = tk.Toplevel(self.root)
        win.title("Farm Tracker")
        win.geometry("177x252")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.overrideredirect(True) # ไร้ขอบหน้าต่างวินโดว์เพื่อความสวยงามสไตล์ HUD
        win.configure(bg="#08101a")
        self.win = win

        # กรอบนอกสุดสีทองเกมมิ่ง
        border_f = tk.Frame(win, bg="#08101a", bd=1, relief="solid",
                            highlightbackground="#eab308", highlightthickness=1)
        border_f.pack(fill=tk.BOTH, expand=True)

        # -------------------------------------------------------------
        # Header Bar (ลากหน้าต่างได้ + ปุ่มปิด)
        # -------------------------------------------------------------
        hdr = tk.Frame(border_f, bg="#0f172a", height=20)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        lbl_title = tk.Label(hdr, text=" 📊 Income Tracker", font=("Segoe UI", 7, "bold"), fg="#38bdf8", bg="#0f172a")
        lbl_title.pack(side=tk.LEFT, padx=2)

        btn_close = tk.Label(hdr, text="✕", font=("Segoe UI", 7, "bold"), fg="#ff4d4f", bg="#0f172a", cursor="hand2", padx=4)
        btn_close.pack(side=tk.RIGHT)
        btn_close.bind("<Button-1>", lambda e: self.win.destroy())

        # ลากหน้าต่าง
        def _start_drag(e):
            win._drag_x = e.x
            win._drag_y = e.y
        def _do_drag(e):
            x = win.winfo_x() + (e.x - getattr(win, '_drag_x', 0))
            y = win.winfo_y() + (e.y - getattr(win, '_drag_y', 0))
            win.geometry(f"+{x}+{y}")
        hdr.bind("<ButtonPress-1>", _start_drag)
        hdr.bind("<B1-Motion>", _do_drag)
        lbl_title.bind("<ButtonPress-1>", _start_drag)
        lbl_title.bind("<B1-Motion>", _do_drag)

        # -------------------------------------------------------------
        # 1. แถบสรุป 24 ชม. วันนี้ (Server Reset 07:00)
        # -------------------------------------------------------------
        f_24h = tk.Frame(border_f, bg="#0b1322", bd=1, relief="solid", highlightbackground="#1e293b", highlightthickness=1)
        f_24h.pack(fill=tk.X, padx=3, pady=(2, 1))

        lbl_24h_h = tk.Label(f_24h, text="☀️ วันนี้ (ตัดรอบ 07:00)", font=("Segoe UI", 6, "bold"), fg="#facc15", bg="#0b1322")
        lbl_24h_h.pack(anchor="w", padx=3, pady=(1, 0))

        self.lbl_24h_neso = tk.Label(f_24h, text="+0.00 NESO", font=("Consolas", 8, "bold"), fg="#4ade80", bg="#0b1322")
        self.lbl_24h_neso.pack(anchor="w", padx=3)

        self.lbl_24h_money = tk.Label(f_24h, text="~ ฿0.00 ($0.00)", font=("Consolas", 6), fg="#94a3b8", bg="#0b1322", cursor="hand2")
        self.lbl_24h_money.pack(anchor="w", padx=3, pady=(0, 2))
        self.lbl_24h_money.bind("<Button-1>", lambda e: self._toggle_currency())

        # -------------------------------------------------------------
        # 2. แถบรอบฟาร์มปัจจุบัน (Session Live Rate)
        # -------------------------------------------------------------
        f_live = tk.Frame(border_f, bg="#08101a", bd=1, relief="solid", highlightbackground="#1e293b", highlightthickness=1)
        f_live.pack(fill=tk.X, padx=3, pady=1)

        f_timer_row = tk.Frame(f_live, bg="#08101a")
        f_timer_row.pack(fill=tk.X, padx=3, pady=(1, 0))

        self.lbl_status_dot = tk.Label(f_timer_row, text="⏸ หยุด", font=("Segoe UI", 6, "bold"), fg="#f59e0b", bg="#08101a")
        self.lbl_status_dot.pack(side=tk.LEFT)

        self.lbl_timer = tk.Label(f_timer_row, text="00:00:00", font=("Consolas", 8, "bold"), fg="#38bdf8", bg="#08101a")
        self.lbl_timer.pack(side=tk.RIGHT)

        self.lbl_live_gained = tk.Label(f_live, text="🪙 รอบนี้: +0.00 NESO", font=("Segoe UI", 6), fg="#e2e8f0", bg="#08101a")
        self.lbl_live_gained.pack(anchor="w", padx=3, pady=(1, 0))

        self.lbl_live_speed = tk.Label(f_live, text="⚡ สปีด: -- NESO/ชม.", font=("Consolas", 7, "bold"), fg="#facc15", bg="#08101a")
        self.lbl_live_speed.pack(anchor="w", padx=3)

        self.lbl_live_income = tk.Label(f_live, text="💵 รายได้: ~฿0.00 / ชม.", font=("Consolas", 6), fg="#38ef7d", bg="#08101a")
        self.lbl_live_income.pack(anchor="w", padx=3, pady=(0, 2))

        # -------------------------------------------------------------
        # 3. ปุ่มควบคุมรอบฟาร์ม [Start/Pause] [Reset]
        # -------------------------------------------------------------
        f_ctrl = tk.Frame(border_f, bg="#08101a")
        f_ctrl.pack(fill=tk.X, padx=3, pady=1)

        self.btn_start = tk.Label(f_ctrl, text="▶ เริ่มฟาร์ม", font=("Segoe UI", 7, "bold"),
                                  fg="#000000", bg="#38ef7d", relief="solid", bd=1, cursor="hand2", padx=4, pady=1)
        self.btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        self.btn_start.bind("<Button-1>", lambda e: self._toggle_tracking())

        btn_rst = tk.Label(f_ctrl, text="🔄 รีเซ็ต", font=("Segoe UI", 7),
                           fg="#cbd5e1", bg="#1e293b", relief="solid", bd=1, cursor="hand2", padx=4, pady=1)
        btn_rst.pack(side=tk.RIGHT, padx=(2, 0))
        btn_rst.bind("<Button-1>", lambda e: self._reset_session())

        # -------------------------------------------------------------
        # 4. กล่องสรุปประวัติรอบฟาร์มแมนนวลล่าสุด (Manual Session Log)
        # -------------------------------------------------------------
        f_last_manual = tk.Frame(border_f, bg="#0b1322", bd=1, relief="solid", highlightbackground="#1e293b", highlightthickness=1)
        f_last_manual.pack(fill=tk.X, padx=3, pady=1)

        lbl_m_hdr = tk.Label(f_last_manual, text="⏱️ ประวัติรอบล่าสุด", font=("Segoe UI", 6, "bold"), fg="#a855f7", bg="#0b1322")
        lbl_m_hdr.pack(anchor="w", padx=3, pady=(1, 0))

        self.lbl_last_session_info = tk.Label(
            f_last_manual,
            text="ยังไม่มีรอบที่บันทึก",
            font=("Consolas", 6),
            fg="#94a3b8",
            bg="#0b1322",
            justify=tk.LEFT
        )
        self.lbl_last_session_info.pack(anchor="w", padx=3, pady=(0, 2))
        self._update_last_session_widget()

        # -------------------------------------------------------------
        # 5. ปุ่มเปิดหน้าต่างประวัติแยก [ 📜 เปิดดูประวัติรายวัน ]
        # -------------------------------------------------------------
        btn_history = tk.Label(border_f, text="📜 ดูประวัติรายวันย้อนหลัง ❯", font=("Segoe UI", 6, "bold"),
                               fg="#38bdf8", bg="#0f172a", relief="solid", bd=1,
                               highlightbackground="#1e293b", highlightthickness=1,
                               cursor="hand2", pady=2)
        btn_history.pack(fill=tk.X, padx=3, pady=(1, 2), side=tk.BOTTOM)
        btn_history.bind("<Button-1>", lambda e: self.open_history_window())

        # รีเฟรชข้อมูลครั้งแรก
        current_wallet = self._get_wallet_neso_float()
        self._refresh_ui(current_wallet)

    def _update_last_session_widget(self):
        """อัปเดตกล่องแสดงรอบฟาร์ม Manual ล่าสุด"""
        if not hasattr(self, 'lbl_last_session_info') or not self.lbl_last_session_info.winfo_exists():
            return
        sessions = self.history_data.get("manual_sessions", [])
        if not sessions:
            self.lbl_last_session_info.config(text="ยังไม่มีรอบที่บันทึก (กดรีเซ็ตเพื่อจบและบันทึกรอบ)", fg="#64748b")
            return
        last = sessions[-1]
        dur_str = last.get("duration", "00:00:00")
        neso_val = last.get("gained_neso", 0.0)
        speed_val = last.get("speed", 0.0)
        txt = f"+{neso_val:,.1f} NESO ({dur_str})\n⚡ {speed_val:,.1f} NESO/ชม."
        self.lbl_last_session_info.config(text=txt, fg="#38ef7d")

    def _toggle_tracking(self):
        current_wallet = self._get_wallet_neso_float()
        curr_nesolet = self._get_character_nesolet_float()
        
        if not self.is_tracking:
            self.is_tracking = True
            self.start_ts = time.time() - self.elapsed_sec
            if self.start_neso == 0.0:
                self.start_neso = current_wallet
            if curr_nesolet is not None:
                self.last_char_nesolet = curr_nesolet
            if hasattr(self, 'btn_start') and self.btn_start.winfo_exists():
                self.btn_start.config(text="⏸ หยุดพัก", bg="#f59e0b", fg="#000000")
            if hasattr(self, 'lbl_status_dot') and self.lbl_status_dot.winfo_exists():
                self.lbl_status_dot.config(text="🟢 กำลังฟาร์ม", fg="#4ade80")
        else:
            self.is_tracking = False
            self.elapsed_sec = time.time() - self.start_ts
            if hasattr(self, 'btn_start') and self.btn_start.winfo_exists():
                self.btn_start.config(text="▶ ต่อฟาร์ม", bg="#38ef7d", fg="#000000")
            if hasattr(self, 'lbl_status_dot') and self.lbl_status_dot.winfo_exists():
                self.lbl_status_dot.config(text="⏸ หยุดพัก", fg="#f59e0b")

    def _reset_session(self):
        """กดรีเซ็ต -> บันทึกสถิติรอบการฟาร์ม Manual ปัจจุบันลงประวัติก่อนเริ่มรอบใหม่"""
        current_wallet = self._get_wallet_neso_float()
        curr_nesolet = self._get_character_nesolet_float()
        
        # คำนวณยอดที่ได้: ให้สิทธิ์ NESOLET สะสมก่อน ถ้ามีค่า > 0, มิฉะนั้น fallback ใช้ wallet neso
        gained = self.session_farmed_nesolet
        if gained <= 0 and self.start_neso > 0 and current_wallet >= self.start_neso:
            gained = current_wallet - self.start_neso
        
        # ถ้ารันมากกว่า 10 วินาที ให้บันทึกลงประวัติรอบฟาร์ม
        if self.elapsed_sec >= 10:
            sec = int(self.elapsed_sec)
            dur_str = f"{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}"
            hours = self.elapsed_sec / 3600.0
            spd = (gained / hours) if hours > 0 else 0.0
            
            sess_entry = {
                "timestamp": int(time.time()),
                "date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "duration": dur_str,
                "gained_neso": round(gained, 2),
                "speed": round(spd, 1),
                "mint_count": self.session_mint_count
            }
            if "manual_sessions" not in self.history_data:
                self.history_data["manual_sessions"] = []
            self.history_data["manual_sessions"].append(sess_entry)
            self.history_data["manual_sessions"] = self.history_data["manual_sessions"][-30:] # เก็บ 30 รอบล่าสุด
            self._save_history()
            self._update_last_session_widget()

        self.is_tracking = False
        self.elapsed_sec = 0.0
        self.start_ts = time.time()
        self.start_neso = current_wallet
        self.session_farmed_nesolet = 0.0
        self.session_mint_count = 0
        if curr_nesolet is not None:
            self.last_char_nesolet = curr_nesolet
            
        if hasattr(self, 'btn_start') and self.btn_start.winfo_exists():
            self.btn_start.config(text="▶ เริ่มฟาร์ม", bg="#38ef7d", fg="#000000")
        if hasattr(self, 'lbl_status_dot') and self.lbl_status_dot.winfo_exists():
            self.lbl_status_dot.config(text="⏸ หยุด", fg="#f59e0b")
        if hasattr(self, 'lbl_timer') and self.lbl_timer.winfo_exists():
            self.lbl_timer.config(text="00:00:00")
        self._refresh_ui(current_wallet)

    def _toggle_currency(self):
        self.is_usd_mode = not self.is_usd_mode
        self._refresh_ui(self._get_wallet_neso_float())

    def _refresh_ui(self, current_wallet):
        if not self.win or not self.win.winfo_exists():
            return

        # 1. แสดงเวลา
        sec = int(self.elapsed_sec)
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        t_str = f"{h:02d}:{m:02d}:{s:02d}"
        if hasattr(self, 'lbl_timer') and self.lbl_timer.winfo_exists():
            self.lbl_timer.config(text=t_str)

        # 2. คำนวณ Session จาก Auto-NESOLET (หรือ fallback เป็นกระเป๋าถ้ายังไม่มี Nesolet)
        gained = self.session_farmed_nesolet
        unit_label = "NESOLET"
        if gained <= 0 and self.start_neso > 0 and current_wallet >= self.start_neso:
            gained = current_wallet - self.start_neso
            unit_label = "NESO"
            
        if hasattr(self, 'lbl_live_gained') and self.lbl_live_gained.winfo_exists():
            mint_suffix = f" (Mint x{self.session_mint_count})" if self.session_mint_count > 0 else ""
            self.lbl_live_gained.config(text=f"🪙 รอบนี้: +{gained:,.1f} {unit_label}{mint_suffix}")

        # สปีดความเร็ว NESOLET/ชม.
        hours = self.elapsed_sec / 3600.0
        speed = (gained / hours) if hours >= (10.0 / 3600.0) else 0.0 # รันเกิน 10 วินาทีก็เริ่มพล็อตสปีดได้ทันใจ
        if hasattr(self, 'lbl_live_speed') and self.lbl_live_speed.winfo_exists():
            spd_txt = f"{speed:,.1f} /ชม." if hours >= (10.0 / 3600.0) else "-- /ชม."
            self.lbl_live_speed.config(text=f"⚡ สปีด: {spd_txt}")

        # รายได้ต่อชั่วโมง (100,000 NESO = 1 NXPC)
        nxpc_u = getattr(self.app, 'nxpc_usd', 0.0)
        nxpc_b = getattr(self.app, 'nxpc_thb', 0.0)
        if hasattr(self, 'lbl_live_income') and self.lbl_live_income.winfo_exists():
            if hours >= (10.0 / 3600.0) and speed > 0:
                speed_nxpc = speed / NESO_PER_NXPC
                income_thb = speed_nxpc * nxpc_b
                income_usd = speed_nxpc * nxpc_u
                inc_txt = f"~${income_usd:.2f} / ชม." if self.is_usd_mode else f"~฿{income_thb:.2f} / ชม."
            else:
                inc_txt = "~฿0.00 / ชม."
            self.lbl_live_income.config(text=f"💵 รายได้: {inc_txt}")

        # 3. ยอด 24 ชม. วันนี้ (ดึงยอด Mint จาก On-chain Henesys L1 ตั้งแต่ 07:00 น.)
        today_neso = self.history_data.get("today_minted_neso", 0.0)
        if hasattr(self, 'lbl_24h_neso') and self.lbl_24h_neso.winfo_exists():
            self.lbl_24h_neso.config(text=f"+{today_neso:,.2f} NESO")

        today_nxpc = today_neso / NESO_PER_NXPC
        today_thb = today_nxpc * nxpc_b
        today_usd = today_nxpc * nxpc_u
        if hasattr(self, 'lbl_24h_money') and self.lbl_24h_money.winfo_exists():
            self.lbl_24h_money.config(text=f"~ ฿{today_thb:,.2f} (${today_usd:,.2f})")

    # -----------------------------------------------------------------
    # หน้าต่างประวัติรายวันแยกต่างหาก (Separate Scrollable History Window)
    # -----------------------------------------------------------------
    def open_history_window(self):
        if self.history_win and self.history_win.winfo_exists():
            self.history_win.lift()
            return

        h_win = tk.Toplevel(self.root)
        h_win.title("Farm History")
        h_win.geometry("260x330")
        h_win.attributes("-topmost", True)
        h_win.configure(bg="#08101a")
        self.history_win = h_win

        # หัวข้อบาร์
        hdr = tk.Frame(h_win, bg="#0f172a", height=24)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        tk.Label(hdr, text=" 📜 บันทึกประวัติฟาร์ม", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#0f172a").pack(side=tk.LEFT, padx=4)
        btn_x = tk.Label(hdr, text="✕", font=("Segoe UI", 8, "bold"), fg="#ff4d4f", bg="#0f172a", cursor="hand2", padx=6)
        btn_x.pack(side=tk.RIGHT)
        btn_x.bind("<Button-1>", lambda e: h_win.destroy())

        # 🗂️ แถบแท็บสลับโหมด: [ ☀️ รายวัน On-Chain ] | [ ⏱️ รอบฟาร์มแมนนวล ]
        f_tabs = tk.Frame(h_win, bg="#0f172a")
        f_tabs.pack(fill=tk.X, padx=4, pady=(2, 2))

        self.btn_tab_daily = tk.Label(
            f_tabs,
            text="☀️ รายวัน (On-Chain)",
            font=("Segoe UI", 7, "bold"),
            fg="#38ef7d" if self.current_history_tab == "daily" else "#64748b",
            bg="#1e293b" if self.current_history_tab == "daily" else "#0f172a",
            relief="solid", bd=1, cursor="hand2", padx=6, pady=2
        )
        self.btn_tab_daily.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        self.btn_tab_manual = tk.Label(
            f_tabs,
            text="⏱️ รอบฟาร์ม (Manual)",
            font=("Segoe UI", 7, "bold"),
            fg="#a855f7" if self.current_history_tab == "manual" else "#64748b",
            bg="#1e293b" if self.current_history_tab == "manual" else "#0f172a",
            relief="solid", bd=1, cursor="hand2", padx=6, pady=2
        )
        self.btn_tab_manual.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))

        def _switch_tab(tab_name):
            self.current_history_tab = tab_name
            self.btn_tab_daily.config(
                fg="#38ef7d" if tab_name == "daily" else "#64748b",
                bg="#1e293b" if tab_name == "daily" else "#0f172a"
            )
            self.btn_tab_manual.config(
                fg="#a855f7" if tab_name == "manual" else "#64748b",
                bg="#1e293b" if tab_name == "manual" else "#0f172a"
            )
            self._render_history_items()

        self.btn_tab_daily.bind("<Button-1>", lambda e: _switch_tab("daily"))
        self.btn_tab_manual.bind("<Button-1>", lambda e: _switch_tab("manual"))

        # ปุ่มควบคุมล่างสุด: [ 🔄 รีเฟรช ] [ 🗑️ ล้างประวัติ ]
        bot_bar = tk.Frame(h_win, bg="#0f172a")
        bot_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=4, pady=4)

        btn_rf = tk.Label(bot_bar, text="🔄 รีเฟรช", font=("Segoe UI", 7),
                          fg="#38bdf8", bg="#1e293b", relief="solid", bd=1, cursor="hand2", padx=6, pady=2)
        btn_rf.pack(side=tk.LEFT, padx=(0, 4))
        btn_rf.bind("<Button-1>", lambda e: self._fetch_onchain_mints_async())

        btn_clear = tk.Label(bot_bar, text="🗑️ ล้างประวัติ", font=("Segoe UI", 7),
                             fg="#ef4444", bg="#1e1b2e", relief="solid", bd=1, cursor="hand2", padx=6, pady=2)
        btn_clear.pack(side=tk.LEFT)
        btn_clear.bind("<Button-1>", lambda e: self._clear_all_history())

        lbl_hint = tk.Label(bot_bar, text="คลิกดูรายละเอียดย่อยได้", font=("Segoe UI", 6), fg="#64748b", bg="#0f172a")
        lbl_hint.pack(side=tk.RIGHT, padx=4)

        # รายการประวัติแบบ Scrollable
        container = tk.Frame(h_win, bg="#08101a")
        container.pack(fill=tk.BOTH, expand=True, padx=4, pady=(2, 4))

        canvas = tk.Canvas(container, bg="#08101a", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#08101a")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # ให้ความกว้างของ scrollable_frame ขยายเต็ม Canvas เสมอ
        def _on_canvas_configure(e):
            canvas.itemconfig(canvas_window, width=e.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.history_scrollable_frame = scrollable_frame
        self.history_canvas = canvas

        self._render_history_items()

    def _render_history_items(self):
        """เรนเดอร์รายการตามแท็บที่เลือก (daily หรือ manual)"""
        if not hasattr(self, 'history_scrollable_frame') or not self.history_scrollable_frame.winfo_exists():
            return

        for w in self.history_scrollable_frame.winfo_children():
            w.destroy()

        # =============================================================
        # 1. แท็บประวัติรอบฟาร์มแมนนวล (Manual Sessions Tab)
        # =============================================================
        if self.current_history_tab == "manual":
            sessions = self.history_data.get("manual_sessions", [])
            if not sessions:
                lbl_empty = tk.Label(
                    self.history_scrollable_frame,
                    text="ยังไม่มีประวัติรอบฟาร์มแมนนวล\n(กด '🔄 รีเซ็ต' ที่หน้าหลักเพื่อบันทึกรอบ)",
                    font=("Segoe UI", 8), fg="#64748b", bg="#08101a", pady=25
                )
                lbl_empty.pack(fill=tk.X)
                return

            # เรียงจากรอบล่าสุดไปเก่าสุด
            for idx, sess in enumerate(reversed(sessions), 1):
                dt_str = sess.get("date_time", "----")
                dur_str = sess.get("duration", "00:00:00")
                g_neso = sess.get("gained_neso", 0.0)
                spd = sess.get("speed", 0.0)

                card = tk.Frame(self.history_scrollable_frame, bg="#0e1322", bd=1, relief="solid",
                                highlightbackground="#2d1b4e", highlightthickness=1)
                card.pack(fill=tk.X, pady=2, padx=2)

                # แถวบน: วันที่/เวลา + เหรียญที่ได้
                r1 = tk.Frame(card, bg="#0e1322")
                r1.pack(fill=tk.X, padx=4, pady=(2, 0))
                mint_cnt = sess.get("mint_count", 0)
                tag_txt = f"⏱️ {dt_str[5:]}" + (f" (Mint x{mint_cnt})" if mint_cnt > 0 else "")
                tk.Label(r1, text=tag_txt, font=("Segoe UI", 7, "bold"), fg="#c084fc", bg="#0e1322").pack(side=tk.LEFT)
                tk.Label(r1, text=f"+{g_neso:,.1f} NESO", font=("Consolas", 7, "bold"), fg="#38ef7d", bg="#0e1322").pack(side=tk.RIGHT)

                # แถวล่าง: เวลาที่ใช้ + สปีดต่อชั่วโมง
                r2 = tk.Frame(card, bg="#0e1322")
                r2.pack(fill=tk.X, padx=4, pady=(1, 3))
                tk.Label(r2, text=f"⏳ {dur_str}", font=("Consolas", 6), fg="#94a3b8", bg="#0e1322").pack(side=tk.LEFT)
                tk.Label(r2, text=f"⚡ {spd:,.1f} /ชม.", font=("Consolas", 6), fg="#facc15", bg="#0e1322").pack(side=tk.RIGHT)
            return

        # =============================================================
        # 2. แท็บประวัติรายวัน On-Chain (Daily Mints Tab)
        # =============================================================
        days = self.history_data.get("days", [])
        if not days:
            lbl_empty = tk.Label(self.history_scrollable_frame, text="กำลังดึงข้อมูล On-chain...\n(หรือคลิกปุ่ม 🔄 รีเฟรช)",
                                 font=("Segoe UI", 8), fg="#64748b", bg="#08101a", pady=20)
            lbl_empty.pack(fill=tk.X)
            return

        curr_server_date = self._get_current_server_date_str()

        for item in days:
            d_str = item.get("date", "----")
            m_neso = item.get("minted_neso", 0.0)
            est_b = item.get("est_thb", 0.0)
            details = item.get("details", [])
            is_today = (d_str == curr_server_date)
            is_expanded = self.expanded_days.get(d_str, False)

            # กรอบแถวหลัก
            bg_color = "#0b1626" if is_today else "#0d1522"
            border_color = "#38bdf8" if is_today else "#1e293b"
            
            card = tk.Frame(self.history_scrollable_frame, bg=bg_color, bd=1, relief="solid",
                            highlightbackground=border_color, highlightthickness=1)
            card.pack(fill=tk.X, pady=2, padx=2)

            # 🌟 แถวสรุปเดี่ยวบรรทัดเดียว (One-Line Row)
            r_single = tk.Frame(card, bg=bg_color, cursor="hand2")
            r_single.pack(fill=tk.X, padx=4, pady=3)

            # ลูกศรหน้าวัน
            arrow_icon = "▼" if is_expanded else "▶"
            lbl_arrow = tk.Label(r_single, text=arrow_icon, font=("Segoe UI", 6), fg="#94a3b8", bg=bg_color)
            lbl_arrow.pack(side=tk.LEFT, padx=(0, 2))

            # วันที่ (เน้นสีพิเศษถ้าเป็นวันนี้)
            date_fg = "#38ef7d" if is_today else "#fde047"
            prefix = "🌟 " if is_today else "📅 "
            lbl_d = tk.Label(r_single, text=f"{prefix}{d_str[5:]}", font=("Segoe UI", 7, "bold"), fg=date_fg, bg=bg_color)
            lbl_d.pack(side=tk.LEFT)

            # ยอดเงินขวาสุด
            lbl_b = tk.Label(r_single, text=f"~฿{est_b:,.1f}", font=("Consolas", 7, "bold"), fg="#38ef7d", bg=bg_color)
            lbl_b.pack(side=tk.RIGHT)

            # ยอดเหรียญตรงกลาง
            lbl_n = tk.Label(r_single, text=f"+{m_neso:,.0f}", font=("Consolas", 7), fg="#38bdf8", bg=bg_color)
            lbl_n.pack(side=tk.RIGHT, padx=4)

            # Binding คลิกที่แถวเดี่ยวเพื่อกาง/หุบดูรายละเอียดย่อย
            def make_toggle(day_k):
                return lambda e: self._toggle_day_details(day_k)

            toggle_cb = make_toggle(d_str)
            for widget in [r_single, lbl_arrow, lbl_d, lbl_n, lbl_b]:
                widget.bind("<Button-1>", toggle_cb)

            # 📋 รายละเอียดย่อยแต่ละธุรกรรมการ Mint เมื่อคลิกกาง (Expandable Sub-list)
            if is_expanded and details:
                detail_box = tk.Frame(card, bg="#070c14", bd=1, relief="solid", highlightbackground="#1e293b", highlightthickness=1)
                detail_box.pack(fill=tk.X, padx=4, pady=(0, 3))

                for tx_info in details:
                    tx_row = tk.Frame(detail_box, bg="#070c14")
                    tx_row.pack(fill=tk.X, padx=3, pady=1)

                    t_txt = tx_info.get("time", "--:--:--")
                    val_txt = f"+{tx_info.get('neso', 0.0):,.2f} NESO"
                    tk.Label(tx_row, text=f"🕒 {t_txt}", font=("Consolas", 6), fg="#94a3b8", bg="#070c14").pack(side=tk.LEFT)
                    tk.Label(tx_row, text=val_txt, font=("Consolas", 6, "bold"), fg="#67e8f9", bg="#070c14").pack(side=tk.RIGHT)

    def _toggle_day_details(self, day_key):
        self.expanded_days[day_key] = not self.expanded_days.get(day_key, False)
        self._render_history_items()

    def _clear_all_history(self):
        """ล้างแคชประวัติย้อนหลังทั้งหมดและดึง On-chain ใหม่"""
        self.history_data["days"] = []
        self.history_data["manual_sessions"] = []
        self.history_data["today_minted_neso"] = 0.0
        self.history_data["start_day_neso"] = self._get_wallet_neso_float()
        self._save_history()
        self._render_history_items()
        self._update_last_session_widget()
        self._refresh_ui(self._get_wallet_neso_float())
        # ยิงดึงประวัติสดใหม่ทันที
        self._fetch_onchain_mints_async()
        if hasattr(self.app, 'log_cmd'):
            self.app.log_cmd("🗑️ ล้างประวัติ Farm Tracker และรีเฟรชข้อมูลใหม่แล้ว")
