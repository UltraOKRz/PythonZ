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
