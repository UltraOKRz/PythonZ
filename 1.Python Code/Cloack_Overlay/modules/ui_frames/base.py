import tkinter as tk

class BaseUIFrame(tk.Frame):
    """
    คลาสฐาน (Universal Base Class) สำหรับโมดูล UI ทั้งหมด
    - รองรับ Universal Adaptive Layout: ขยายกรอบอัตโนมัติเมื่อขนาดฟอนต์เปลี่ยนหรือขนาดหน้าต่างเปลี่ยน
    - รองรับการฝัง Resize Grip (กริบแดงลากขยาย) ไว้ที่มุมขวาล่างสำหรับทุกโมดูล/หน้าต่าง
    """
    def __init__(self, parent, app, has_resize_grip=False, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        
        # ผูกอีเวนต์ Configure เพื่อให้ Label ด้านในรู้ตัวว่าต้องปรับ wraplength ดันกรอบลงล่าง
        self.bind("<Configure>", self._on_base_configure)

    def _on_base_configure(self, event):
        """เมื่อความกว้าง Frame เปลี่ยน ให้ Label ลูกปรับ wraplength เพื่อห่อคำและดันความสูง (Height) ขึ้น"""
        w = event.width
        if w > 20:
            for child in self.winfo_children():
                self._update_wraplength_recursive(child, w)
                
    def _update_wraplength_recursive(self, widget, max_width):
        # รีเคอร์ซีฟอัปเดต Label ที่ซ้อนอยู่ข้างใน Frame ย่อยๆ
        if isinstance(widget, tk.Frame):
            for child in widget.winfo_children():
                self._update_wraplength_recursive(child, max_width)
        elif isinstance(widget, tk.Label) or type(widget).__name__ == "StrokeLabel":
            try:
                # ถ้า Label นี้ถูกกำหนด wraplength ไว้แล้ว หรือตั้งค่าให้ปรับตามความกว้าง
                if "wraplength" in widget.keys():
                    # หักลบขอบซ้ายขวานิดหน่อย
                    new_wrap = max(50, max_width - 15)
                    widget.config(wraplength=new_wrap)
            except:
                pass

    def _add_resize_grip(self):
        """สร้างกริบแดงขวาล่างสำหรับ Resize"""
        self.grip = tk.Label(self, text=" ◢ ", font=("Segoe UI", 8, "bold"),
                             fg="#ffffff", bg="#dc2626", relief="solid", bd=1,
                             highlightbackground="#ffffff", highlightthickness=1,
                             cursor="size_nw_se", padx=2, pady=0)
        self.grip.place(relx=1.0, rely=1.0, anchor="se")
        self.grip.lift()
        
        # ผูก Event ไปที่ฟังก์ชัน resize ของหน้าต่างหลัก/App
        if hasattr(self.app, "start_resize"):
            self.grip.bind("<ButtonPress-1>", self.app.start_resize)
            self.grip.bind("<B1-Motion>", self.app.do_resize)
            self.grip.bind("<ButtonRelease-1>", self.app.end_resize)
