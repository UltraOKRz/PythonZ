import re
import os

filepath = r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\โพสิชั่น.pyw"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Insert open_dca_manager
method_code = """
    def open_dca_manager(self):
        sym = self.sym_var.get().strip().upper()
        if not sym:
            return
            
        win = tk.Toplevel(self.root)
        win.title(f"Spot DCA Manager: {sym}")
        win.geometry("380x450")
        win.config(bg="#121418")
        win.attributes("-topmost", True)
        
        tk.Label(win, text=f"จัดการประวัติซื้อ (DCA) - {sym}", bg="#121418", fg="#f0b90b", font=("Arial", 12, "bold")).pack(pady=10)
        
        f_input = tk.Frame(win, bg="#121418")
        f_input.pack(fill=tk.X, padx=20)
        
        tk.Label(f_input, text="ราคา (Price):", bg="#121418", fg="#fff").grid(row=0, column=0, sticky=tk.W, pady=2)
        p_var = tk.DoubleVar(value=0.0)
        tk.Entry(f_input, textvariable=p_var, width=15).grid(row=0, column=1, padx=5)
        
        tk.Label(f_input, text="จำนวน (Amount):", bg="#121418", fg="#fff").grid(row=1, column=0, sticky=tk.W, pady=2)
        a_var = tk.DoubleVar(value=0.0)
        tk.Entry(f_input, textvariable=a_var, width=15).grid(row=1, column=1, padx=5)
        
        lb_frame = tk.Frame(win, bg="#121418")
        lb_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        lb = tk.Listbox(lb_frame, bg="#1e2329", fg="#00e676", font=("Arial", 10), selectbackground="#444")
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(lb_frame, command=lb.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lb.config(yscrollcommand=sb.set)
        
        lbl_summary = tk.Label(win, text="", bg="#121418", fg="#00bfff", font=("Arial", 10, "bold"))
        lbl_summary.pack(pady=5)
        
        if "spot_dca" not in self.cfg_data: self.cfg_data["spot_dca"] = {}
        if sym not in self.cfg_data["spot_dca"]: self.cfg_data["spot_dca"][sym] = []
        dca_list = self.cfg_data["spot_dca"][sym]
        
        def refresh_list():
            lb.delete(0, tk.END)
            total_amt = 0.0
            total_cost = 0.0
            for i, d in enumerate(dca_list):
                p = d["p"]
                a = d["a"]
                total_amt += a
                total_cost += p * a
                lb.insert(tk.END, f"#{i+1} | ราคา {p:,.4f} | จำนวน {a:g}")
            
            avg = total_cost / total_amt if total_amt > 0 else 0
            lbl_summary.config(text=f"รวม: {total_amt:g} | ต้นทุนเฉลี่ย: {avg:,.4f}")
            self.save_config()
            
            if self.market_var.get() == "SPOT" and not getattr(self, "is_fetching_api", False):
                self.margin_var.set(total_amt)

        def add_record():
            try:
                p = float(p_var.get())
                a = float(a_var.get())
                if p > 0 and a > 0:
                    dca_list.append({"p": p, "a": a})
                    p_var.set(0.0)
                    a_var.set(0.0)
                    refresh_list()
            except: pass
            
        def del_record():
            sel = lb.curselection()
            if sel:
                idx = sel[0]
                dca_list.pop(idx)
                refresh_list()
                
        def clear_all():
            dca_list.clear()
            refresh_list()
            
        tk.Button(f_input, text="เพิ่ม (Add)", bg="#00e676", fg="#000", font=("Arial", 9, "bold"), command=add_record).grid(row=0, column=2, rowspan=2, sticky=tk.NSEW, padx=5)
        
        btn_f = tk.Frame(win, bg="#121418")
        btn_f.pack(fill=tk.X, padx=20, pady=(0, 20))
        tk.Button(btn_f, text="ลบรายการที่เลือก", bg="#ff9800", fg="#000", command=del_record).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,5))
        tk.Button(btn_f, text="🗑️ ล้างประวัติทั้งหมด", bg="#ff3d57", fg="#fff", command=clear_all).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5,0))
        
        refresh_list()
"""

pattern = r'(    def on_sym_type\(self, event\):)'
replacement = method_code + "\n" + r'\1'

content = re.sub(pattern, replacement, content)
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("DCA Manager added.")
