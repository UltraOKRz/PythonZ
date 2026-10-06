# modules/api_client.py
# API Client Mixin: ดึงข้อมูลดรอป, NXPC, ข้อมูลกระเป๋า, Layer list, ไอคอน
import os
import sys
import json
import time
import threading
import urllib
import urllib.request
import urllib.parse
import math
import re
from datetime import datetime
from PIL import Image, ImageTk
from modules.common import (
    CONFIG_FILE, LAYERS_CACHE_FILE, ICONS_CACHE_DIR, DEFAULT_WALLET,
    ZONE_ICONS_MAP, get_default_wallet, get_api_keys,
    format_compact_number, format_compact_stock
)

class ApiClientMixin:
    def get_current_api_key(self):
        if not self.api_keys:
            return ""
        return self.api_keys[self.current_key_idx % len(self.api_keys)]

    def rotate_api_key(self):
        if self.api_keys:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)


    def fetch_drop_data_async(self):
        """ส่งคำขอไปยัง Official MSU OpenAPI เพื่อดึง % ดรอปและยอดกระเป๋าแบบ Background Thread"""
        if self.is_fetching:
            return
        self.is_fetching = True
        threading.Thread(target=self._fetch_drop_data_worker, daemon=True).start()

    def _fetch_nxpc_price_sync(self):
        try:
            now = time.time()
            if now - self.nxpc_last_fetch > 300: # 5 mins
                url = "https://api.coingecko.com/api/v3/simple/price?ids=nexpace&vs_currencies=usd,thb"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    self.nxpc_usd = data.get("nexpace", {}).get("usd", 0.0)
                    self.nxpc_thb = data.get("nexpace", {}).get("thb", 0.0)
                self.nxpc_last_fetch = now
        except Exception as e:
            print("Fetch NXPC price error:", e)

    def _fetch_wallet_neso_sync(self):
        """ดึงยอดเหรียญ NESO ในกระเป๋าผ่าน Official MSU OpenAPI"""
        self._fetch_nxpc_price_sync()
        
        # ⚡ จำกัดการยิง API Onchain Neso แค่ทุกๆ 60 วินาที เพื่อประหยัดโควต้า
        now = time.time()
        if not hasattr(self, 'wallet_last_fetch_ts'):
            self.wallet_last_fetch_ts = 0
        if now - self.wallet_last_fetch_ts < 60:
            return
            
        try:
            if not self.wallet_addr:
                return
            key = self.get_current_api_key()
            url = f"https://openapi.msu.io/v1rc1/accounts/{self.wallet_addr}/neso"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Content-Type": "application/json",
                    "x-nxopen-api-key": key
                },
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                self.api_call_count += 1
                res = json.loads(resp.read().decode("utf-8"))
            if res.get("success"):
                onchain_raw = res.get("data", {}).get("onchainNeso", "0")
                onchain_val = int(onchain_raw) / (10**18)
                self.wallet_neso_val = float(onchain_val)
                self.wallet_neso_str = f"{onchain_val:,.1f}"
                self.wallet_neso_compact = format_compact_number(onchain_val)
                
                if not getattr(self, 'current_char_nesolet_loaded', False):
                    offchain_raw = res.get("data", {}).get("offchainNeso", "0")
                    offchain_val = int(offchain_raw) / (10**18)
                    self.wallet_nesolet_str = f"{offchain_val:,.1f}"
                    self.wallet_nesolet_compact = format_compact_number(offchain_val)
                    
            self.wallet_last_fetch_ts = now

        except Exception as e:
            print("Fetch wallet neso error:", e)

    def _fetch_drop_data_worker(self):
        try:
            # 🛡️ ถ้าอยู่ในเมือง: ข้าม Reward API ทั้งหมด แค่ดึงยอดกระเป๋าและอัปเดต UI
            if self.is_in_town:
                self.has_no_drop = True
                self.last_update_str = datetime.now().strftime("%H:%M:%S")
                self._fetch_wallet_neso_sync()
                self.root.after(0, self.update_drop_ui)
                return

            if not self.selected_layer_id:
                # ยังไม่มีการเลือกแมพ หรือกำลังรอตรวจจับในเกม
                self.neso_normal_rate = "รอแมพ"
                self.neso_normal_stock = "---"
                self.neso_boost_rate = "รอแมพ"
                self.neso_boost_mult = ""
                self.neso_boost_stock = "---"
                self.last_update_str = datetime.now().strftime("%H:%M:%S")
                self._fetch_wallet_neso_sync()
                self.root.after(0, self.update_drop_ui)
                return

            # Map server name to worldId: Fang=0, Ain=1, Errai=2
            w_id = getattr(self, 'world_id', 0)
            url = f"https://openapi.msu.io/v1rc1/msn/rewards/{w_id}"

            # รวบรวม Layers สำหรับคำนวณและหาแมพแนะนำ
            curr_item = next((it for it in self.layers_list if it.get("layerId") == self.selected_layer_id), None)
            if curr_item and curr_item.get("groupName"):
                self.selected_group_name = curr_item.get("groupName")

            all_query_layers = []
            if self.selected_layer_id:
                all_query_layers.append(int(self.selected_layer_id))

            # 🎯 ดึงเลเวลตัวละครมาคำนวณช่วงเลเวลแนะนำ (+20 เวล, -20 เวล ปัดเลขกลมๆ ลงท้ายด้วย 0)
            char_lv = 0
            try:
                char_lv = int(getattr(self, 'current_char_level', 0) or 0)
            except:
                char_lv = 0

            target_level_layers = []
            if char_lv > 0:
                # ตัวอย่าง: Lv. 222 -> min = (222 - 20) // 10 * 10 = 200, max = (222 + 20) // 10 * 10 = 240
                min_target_lv = max(10, ((char_lv - 20) // 10) * 10)
                max_target_lv = ((char_lv + 20) // 10) * 10

                for it in self.layers_list:
                    l_min = it.get("minLevel", 0)
                    l_max = it.get("maxLevel", 0)
                    # ตรวจสอบว่าช่วงเลเวลของ Layer ทับซ้อนกับช่วงแนะนำหรือไม่
                    if l_max >= min_target_lv and l_min <= max_target_lv:
                        lid = int(it["layerId"])
                        if lid not in target_level_layers:
                            target_level_layers.append(lid)

            self.target_recommend_level_layers = target_level_layers

            # เพิ่ม Layers จากช่วงเลเวล หรือ fallback ไปโซนเดียวกันถ้าไม่มีข้อมูลเลเวล
            if target_level_layers:
                for lid in target_level_layers:
                    if lid not in all_query_layers:
                        all_query_layers.append(lid)
            elif self.selected_group_name:
                zone_layers = [it for it in self.layers_list if it.get("groupName") == self.selected_group_name]
                for zl in zone_layers:
                    lid = int(zl["layerId"])
                    if lid not in all_query_layers:
                        all_query_layers.append(lid)

            # ให้แมพปัจจุบันอยู่ต้นๆ เสมอ และจำกัดจำนวน query เพื่อประสิทธิภาพ
            all_query_layers = all_query_layers[:25]

            payload = {
                "layerDescs": [{"layerId": lid} for lid in all_query_layers]
            }

            res = None
            # วนลูปสลับคีย์ถ้าติด Error หรือ Rate limit
            for attempt in range(len(self.api_keys)):
                key = self.get_current_api_key()
                req = urllib.request.Request(
                    url, 
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Content-Type": "application/json",
                        "x-nxopen-api-key": key
                    },
                    method="POST"
                )
                try:
                    start_ping = time.time()
                    with urllib.request.urlopen(req, timeout=6) as resp:
                        self.server_ping_ms = int((time.time() - start_ping) * 1000)
                        self.api_call_count += 1
                        res = json.loads(resp.read().decode("utf-8"))
                        if res.get("success"):
                            self.rotate_api_key() # หมุนเวียนคีย์เพื่อเฉลี่ยโหลด
                            break
                        else:
                            self.rotate_api_key()
                except Exception as ex:
                    print(f"Key attempt {attempt+1} failed: {ex}")
                    self.rotate_api_key()
                    if attempt == len(self.api_keys) - 1:
                        raise ex
            
            def _to_f(val):
                try:
                    return float(val)
                except:
                    return 0.0

            if res and res.get("success"):
                reward_infos = res.get("data", {}).get("rewardInformations", {}).get("rewardInformations", [])
                has_neso_item = False
                
                # ค้นหาข้อมูลของแมพปัจจุบันที่เลือกอยู่จริง ๆ (ตรงตาม layerId)
                target_reward_info = None
                for r_info in reward_infos:
                    f_info = r_info.get("fieldInformation", {})
                    if f_info.get("layerId") == int(self.selected_layer_id):
                        target_reward_info = f_info
                        break
                
                # ถ้าไม่เจอให้ fallback ไปตัวแรกถ้ามี
                if not target_reward_info and reward_infos:
                    target_reward_info = reward_infos[0].get("fieldInformation", {})

                if target_reward_info:
                    items = target_reward_info.get("items", [])
                    
                    # แยก NESO Normal และ NESO Boost
                    for itm in items:
                        if itm.get("key", {}).get("itemId") == 1:
                            has_neso_item = True
                            is_boost = itm.get("enableBoostOption", False)
                            drop_val = _to_f(itm.get("dropProb", {}).get("value", 0))
                            base_val = _to_f(itm.get("baseProb", {}).get("value", 0))
                            stock_val = _to_f(itm.get("currentStock", {}).get("value", 0))
                            min_qty = _to_f(itm.get("dropQuantityMin", {}).get("value", 0))
                            max_qty = _to_f(itm.get("dropQuantityMax", {}).get("value", 0))
                            chg_val = _to_f(itm.get("stockPerCharge", {}).get("value", 0))
                            
                            if is_boost:
                                mult = (drop_val / base_val) if base_val > 0 else 1.0
                                self.neso_boost_rate_f = drop_val
                                self.neso_boost_stock_f = stock_val
                                self.neso_boost_base_f = base_val
                                self.neso_boost_charge_f = chg_val
                                self.neso_boost_min_f = min_qty
                                self.neso_boost_max_f = max_qty
                                self.neso_boost_rate = f"{drop_val:.2f}%"
                                self.neso_boost_mult = f"x{mult:.1f}"
                                
                                sure_drop = int(drop_val // 100)
                                chance_drop = drop_val % 100
                                extra_rate = max(0.0, drop_val - base_val)
                                
                                # คำนวณช่วงตัวเลข NESO ที่แน่นอน (Per Drop & Expected Total)
                                self.neso_boost_sure_min = sure_drop * min_qty
                                self.neso_boost_sure_max = sure_drop * max_qty
                                self.neso_boost_extra_min = (chance_drop / 100.0) * min_qty
                                self.neso_boost_extra_max = (chance_drop / 100.0) * max_qty
                                self.neso_boost_total_min = (drop_val / 100.0) * min_qty
                                self.neso_boost_total_max = (drop_val / 100.0) * max_qty
                                
                                if sure_drop > 0:
                                    self.neso_boost_sure_txt = f"{self.neso_boost_sure_min:.2f} ~ {self.neso_boost_sure_max:.2f} NESO"
                                else:
                                    self.neso_boost_sure_txt = "0 NESO"
                                
                                self.neso_boost_extra_txt = f"{self.neso_boost_extra_min:.2f} ~ {self.neso_boost_extra_max:.2f} ({chance_drop:.2f}%)"
                                self.neso_boost_total_txt = f"{self.neso_boost_total_min:.2f} ~ {self.neso_boost_total_max:.2f} NESO"
                                self.neso_boost_breakdown_txt = f"{drop_val:.2f}% ({base_val:.0f}% + {extra_rate:.2f}%)"
                                self.neso_boost_stock = format_compact_number(stock_val)
                                self.neso_boost_charge = format_compact_number(chg_val)
                                self.neso_boost_detail = f"การันตี {sure_drop} + {chance_drop:.1f}%"
                            else:
                                self.neso_normal_rate_f = drop_val
                                self.neso_normal_stock_f = stock_val
                                self.neso_normal_rate = f"{drop_val:.1f}%"
                                self.neso_normal_stock = format_compact_number(stock_val)
                                self.neso_normal_drop_qty = format_compact_number((drop_val / 100.0) * stock_val)

                    if has_neso_item and (getattr(self, 'neso_normal_rate_f', 0) > 0 or getattr(self, 'neso_boost_rate_f', 0) > 0 or getattr(self, 'neso_boost_stock_f', 0) > 0):
                        self.has_no_drop = False
                    else:
                        self.has_no_drop = True
                        self.neso_normal_rate = "--"
                        self.neso_normal_stock = "0"
                        self.neso_normal_rate_f = 0.0
                        self.neso_normal_stock_f = 0.0
                        self.neso_boost_rate = "--"
                        self.neso_boost_rate_f = 0.0
                        self.neso_boost_stock_f = 0.0
                        self.neso_boost_stock = "0"
                        self.neso_boost_mult = ""
                        self.neso_boost_min_f = 0.0
                        self.neso_boost_max_f = 0.0
                        self.neso_boost_sure_min = 0.0
                        self.neso_boost_sure_max = 0.0
                        self.neso_boost_extra_min = 0.0
                        self.neso_boost_extra_max = 0.0
                        self.neso_boost_total_min = 0.0
                        self.neso_boost_total_max = 0.0
                        self.neso_boost_sure_txt = "--"
                        self.neso_boost_extra_txt = "--"
                        self.neso_boost_total_txt = "--"
                        self.neso_boost_breakdown_txt = "--"
                        self.neso_boost_charge = "--"
                    self.last_update_str = datetime.now().strftime("%H:%M:%S")
                else:
                    self.has_no_drop = True
                    self.last_update_str = datetime.now().strftime("%H:%M:%S")
            else:
                self.has_no_drop = True
                self.last_update_str = datetime.now().strftime("%H:%M:%S")

            # 🎯 ค้นหาแมพแนะนำในช่วงเลเวลตัวละครที่มีผลดรอป (% Boost หรือ Expected Drop) สูงสุด
            if res and res.get("success"):
                best_score = -1.0
                best_map_obj = None
                target_lids = getattr(self, 'target_recommend_level_layers', [])

                for r_info in reward_infos:
                    f_info = r_info.get("fieldInformation", {})
                    lid = f_info.get("layerId")
                    if lid:
                        # ถ้ามีช่วงเลเวลตัวละคร ให้พิจารณาแมพในช่วงเลเวลก่อน
                        if target_lids and (lid not in target_lids):
                            continue

                        for itm in f_info.get("items", []):
                            if itm.get("key", {}).get("itemId") == 1 and itm.get("enableBoostOption", False):
                                b_rate = _to_f(itm.get("dropProb", {}).get("value", 0))
                                b_stk = _to_f(itm.get("currentStock", {}).get("value", 0))
                                b_min_qty = _to_f(itm.get("dropQuantityMin", {}).get("value", 0))
                                b_max_qty = _to_f(itm.get("dropQuantityMax", {}).get("value", 0))
                                b_exp_min = (b_rate / 100.0) * b_min_qty
                                b_exp_max = (b_rate / 100.0) * b_max_qty

                                # เปรียบเทียบผลลัพธ์การดรอป (คำนวณจาก Expected Drop สูงสุดเป็นหลัก หากเท่ากันดูที่ % เรต)
                                score = b_exp_max if b_exp_max > 0 else (b_rate / 10.0)
                                if score > best_score:
                                    layer_meta = next((l for l in self.layers_list if l["layerId"] == lid), None)
                                    lname = layer_meta.get("layerName", f"Field #{lid}") if layer_meta else f"Field #{lid}"
                                    best_score = score

                                    if b_exp_max > 0:
                                        b_qty_txt = f"{b_exp_min:.2f} ~ {b_exp_max:.2f} N"
                                    else:
                                        b_qty_txt = "-- N"

                                    best_map_obj = {
                                        "layerId": lid,
                                        "layerName": lname,
                                        "rate": b_rate,
                                        "stock": b_stk,
                                        "min_qty": b_min_qty,
                                        "max_qty": b_max_qty,
                                        "exp_min": b_exp_min,
                                        "exp_max": b_exp_max,
                                        "qty_txt": b_qty_txt
                                    }

                # Fallback: ถ้าในช่วงเลเวลไม่พบ ให้หาจากโซนที่ยืน
                if not best_map_obj and reward_infos:
                    for r_info in reward_infos:
                        f_info = r_info.get("fieldInformation", {})
                        lid = f_info.get("layerId")
                        if lid:
                            for itm in f_info.get("items", []):
                                if itm.get("key", {}).get("itemId") == 1 and itm.get("enableBoostOption", False):
                                    b_rate = _to_f(itm.get("dropProb", {}).get("value", 0))
                                    b_stk = _to_f(itm.get("currentStock", {}).get("value", 0))
                                    b_min_qty = _to_f(itm.get("dropQuantityMin", {}).get("value", 0))
                                    b_max_qty = _to_f(itm.get("dropQuantityMax", {}).get("value", 0))
                                    b_exp_min = (b_rate / 100.0) * b_min_qty
                                    b_exp_max = (b_rate / 100.0) * b_max_qty
                                    score = b_exp_max if b_exp_max > 0 else (b_rate / 10.0)
                                    if score > best_score:
                                        layer_meta = next((l for l in self.layers_list if l["layerId"] == lid), None)
                                        lname = layer_meta.get("layerName", f"Field #{lid}") if layer_meta else f"Field #{lid}"
                                        best_score = score
                                        best_map_obj = {
                                            "layerId": lid,
                                            "layerName": lname,
                                            "rate": b_rate,
                                            "stock": b_stk,
                                            "min_qty": b_min_qty,
                                            "max_qty": b_max_qty,
                                            "exp_min": b_exp_min,
                                            "exp_max": b_exp_max,
                                            "qty_txt": f"{b_exp_min:.2f} ~ {b_exp_max:.2f} N" if b_exp_max > 0 else "-- N"
                                        }

                self.best_zone_map = best_map_obj
                if self.best_zone_map:
                    now_ts = time.time()
                    last_log_ts = getattr(self, 'last_hot_log_ts', 0)
                    last_logged_lid = getattr(self, 'last_hot_logged_lid', None)
                    if (now_ts - last_log_ts >= 15) or (last_logged_lid != self.best_zone_map['layerId']):
                        self.last_hot_log_ts = now_ts
                        self.last_hot_logged_lid = self.best_zone_map['layerId']
                        self.log_cmd(f"🔥 แนะนำ: {self.best_zone_map['layerName']} ({self.best_zone_map['rate']:.1f}%)")
            else:
                self.best_zone_map = None

            # ดึงยอดกระเป๋าต่อเสมอ
            self._fetch_wallet_neso_sync()

            # แจ้ง UI อัปเดตข้อมูลบนหน้าจอ
            self.root.after(0, self.update_drop_ui)
        except Exception as e:
            print("Fetch drop data error:", e)
            if self.neso_boost_rate == "...":
                self.neso_boost_rate = "รอข้อมูล"
            if self.neso_boost_stock == "...":
                self.neso_boost_stock = "รอเซิร์ฟเวอร์"
            self.last_update_str = datetime.now().strftime("%H:%M:%S")
            # แม้กระทั่ง error ก็ดึงกระเป๋าและอัปเดต UI เสมอ
            self._fetch_wallet_neso_sync()
            self.root.after(0, self.update_drop_ui)
        finally:
            self.last_fetch_ts = time.time()
            self.is_fetching = False

