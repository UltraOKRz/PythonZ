---
name: tkinter-overlay-floating-window
description: Best practices for building stable, transparent, non-flickering, non-drifting Tkinter overlays and floating HUDs on Windows.
---

# Tkinter Overlay & Floating HUD Window Master Skill

ทักษะเฉพาะทางสำหรับการพัฒนาหน้าต่างลอย (Floating Window / HUD Overlay) ด้วย Python Tkinter บน Windows จากประสบการณ์จริงในโปรเจกต์ MS และ COS

## 1. Safe Right-to-Left Packing Order (แก้ปัญหาปุ่มคอนโทรลหายเมื่อย่อเล็กสุด)
**ปัญหา:** เมื่อหน้าต่างถูกหดขนาด (Resize) ให้แคบลง หรือข้อความทางซ้ายยาว (เช่น `[ServerTime]`) ปุ่มควบคุมฝั่งขวา (ปุ่มย่อ `🗕`, ปุ่มตั้งค่า `⚙`, ปุ่มปิด `✕`) จะถูกเบียดดันจนตกขอบจอหายไป
**วิธีแก้:**
- ในแถบเมนู (Top Bar / Control Bar) **ต้อง `pack(side=tk.RIGHT)` ปุ่มควบคุมทางขวาก่อนเสมอ!**
- กำหนด `width=2` ให้กับปุ่มตัวอักษร/ไอคอน เพื่อให้ปุ่มมีขนาดความกว้างคงที่ ไม่หดหาย
- ฝั่งซ้ายค่อย `pack(side=tk.LEFT)` ตามมาทีหลัง และหลีกเลี่ยงการใช้ `expand=True` ใน Label ที่อาจขยายตัวไปเบียดปุ่มฝั่งขวา

```python
# ✅ ถูกต้อง: Pack ขวาก่อนเสมอ
btn_x = tk.Label(top_bar, text="✕", width=2, ...)
btn_x.pack(side=tk.RIGHT, padx=1)

btn_set = tk.Label(top_bar, text="⚙", width=2, ...)
btn_set.pack(side=tk.RIGHT, padx=1)

btn_mini = tk.Label(top_bar, text="🗕", width=2, ...)
btn_mini.pack(side=tk.RIGHT, padx=1)

# จากนั้นค่อย Pack ซ้าย
lbl_mode = tk.Label(top_bar, text="[ServerTime]", ...)
lbl_mode.pack(side=tk.LEFT)
```

---

## 2. Live Coordinate Anchoring (แก้ปัญหาหน้าต่างดิ้นหนี / กระโดดตำแหน่งตอนย่อ-ขยาย)
**ปัญหา:** เมื่อผู้ใช้ลากหน้าต่างไปไว้ตำแหน่งใหม่ แล้วกดปุ่มย่อ (Mini Mode) หรือขยาย หน้าต่างกลับเด้งหรือเทเลพอร์ตกลับไปตำแหน่งเดิม หรือเลื่อนหนีตำแหน่งเมาส์
**สาเหตุ:** โค้ดดึงพิกัดจากตัวแปรเก่า `self.pos_x`, `self.pos_y` ที่ยังไม่ได้อัปเดตจากตำแหน่งจริงบนจอ ณ เสี้ยววินาทีนั้น
**วิธีแก้:**
- ก่อนสั่งคำนวณ `geometry()` หรือสลับโหมด ให้ดึงพิกัดสดๆ จาก `win_bg.winfo_x()` และ `win_bg.winfo_y()` เสมอ
- กำหนดความกว้างของ Mini Mode ให้เท่ากับ Full Mode (`self.mini_w = self.full_w`) เพื่อให้หน้าต่างหดตัวเฉพาะแนวตั้ง (ความสูง) ส่วนแนวนอนและตำแหน่งปุ่มที่มุมขวาบนจะไม่เลื่อนหนีเคอร์เซอร์เมาส์ของผู้ใช้เลย

```python
def apply_geometry(self):
    try:
        cur_x = self.win_bg.winfo_x()
        cur_y = self.win_bg.winfo_y()
        if cur_x > -10000 and cur_y > -10000:
            self.pos_x = cur_x
            self.pos_y = cur_y
    except Exception:
        pass

    w = self.mini_w if self.is_mini else self.full_w
    h = self.mini_h if self.is_mini else self.full_h
    self.win_bg.geometry(f"{w}x{h}+{self.pos_x}+{self.pos_y}")
    self.win_fg.geometry(f"{w}x{h}+{self.pos_x}+{self.pos_y}")
    self.win_bg.update_idletasks()
    self.win_fg.update_idletasks()
    self.win_fg.lift()
```

---

## 3. MS 2-Layer Transparent Architecture (สูตรแก้จอดำ Z-Order ถาวร)
- สร้าง 2 เลเยอร์แยกกัน: `win_bg` (พื้นหลังโปร่งใสตาม alpha) + `win_fg` (เลเยอร์หน้าสุดโปร่งใสทะลุผ่าน transparentcolor)
- สั่ง `self.win_fg.transient(self.win_bg)` และ `self.win_fg.lift()` ในลูปนาฬิกา
- ช่วยให้เรนเดอร์ข้อความและแคนวาสได้คมชัด สีสันสดใส คอนทราสต์สูง ไม่กลืนเป็นสีดำ

---

## 4. Bottom-Pinned Control & High-Visibility Resize Grip (แก้ปัญหาวิดเจ็ตและ Grip ตกขอบ)
**ปัญหา:** เมื่อหน้าต่างถูกจำกัดความสูง (เช่น ในโหมดแถบข้าง หรือพับย่อ) วิดเจ็ตที่ pack `fill=tk.BOTH, expand=True` ตรงกลาง จะขยายตัวกินพื้นที่จนดันแถบด้านล่าง (`f_fold_bar`) และปุ่ม Grip ปรับขนาด (`◢`) ตกขอบล่างของหน้าต่างหายไป
**วิธีแก้:**
- ในคอนเทนเนอร์หลัก ต้อง `pack(side=tk.BOTTOM)` แถบควบคุมด้านล่าง (`f_fold_bar`, `f_red_box`) **ก่อน** ที่จะ pack โซนตรงกลาง (`f_pool_zone`) ที่ใช้ `expand=True`
- สร้าง Grip ปรับขนาดมุมล่างขวาที่มีดีไซน์สะดุดตาชัดเจน เช่น **กรอบสีแดง-ขาว** (`bg="#dc2626", fg="#ffffff", highlightbackground="#ffffff", highlightthickness=1`) เพื่อให้มองเห็นและคลิกลากขยายได้ง่ายแม้ในโหมดมืดหรือโปร่งใส
- บนหน้าต่างที่แคบ (เช่น กว้าง ≤ 240px) ต้องย่อข้อความของปุ่มข้างเคียง (เช่น จาก `"▲ กางแถบควบคุมล่าง"` เหลือ `"▲ แถบล่าง"`) เพื่อป้องกันข้อความยาวไปเบียด Grip มุมขวาตกขอบ

---

## 5. Multi-Layout Mode Switching & Responsive Balanced UI (ระบบสลับโหมดและตัดบรรทัดบาลานซ์)
**ปัญหา:** ต้องการรองรับทั้งหน้าต่างหลักแบบแนวนอน (Horizontal HUD) และแถบข้างแนวตั้ง (Vertical Sidebar HUD) โดยที่ฟังก์ชันอยู่ครบ ไม่ล้น ไม่ตกขอบ
**วิธีแก้:**
- **One-Click Mode Toggle:** ผูก event คลิกที่ไอคอนหัวแถบ (เช่น ไอคอนรูปนาฬิกา `⏰` บน Title Bar) ให้สลับไป-มาระหว่าง `V.2 แนวนอน (460x275)` กับ `Vertical Sidebar (170x380)`
- **Dynamic Stack Layout Switching:**
  - เมื่อ `w > 240` (แนวนอน): จัดเรียงองค์ประกอบแบบซ้าย-ขวา `pack(side=tk.LEFT)`
  - เมื่อ `w <= 240` (แถบข้าง): สลับเป็นการเรียงซ้อนแนวตั้ง `pack(side=tk.TOP, fill=tk.X)`
- **Responsive Text Wraplength & Font Scaling:**
  - ในฟังก์ชัน `update_auto_scale_ui(w)` และตอน `do_resize` ต้องคำนวณ `wraplength = max(80, w - padding)` ให้กับข้อความชื่อแมพและเทอร์มินัลเสมอ เพื่อตัดบรรทัดใหม่อัตโนมัติ ป้องกันการขยายล้นขอบจอ
  - ปรับขนาดฟอนต์เป็นสัดส่วน (Breakpoint) เช่น 9-10pt เมื่อกว้าง, 7-8pt เมื่อปานกลาง, และ 6-7pt เมื่อแคบกว่า 240px เพื่อให้ทุกส่วนแสดงผลได้อย่างสมดุล (Balance)

