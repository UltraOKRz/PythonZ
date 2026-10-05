import re

file_path = r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\โพสิชั่น.pyw"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Save is_float_mode and hide win_set
init_search = """        self.win_set = tk.Toplevel(self.root)
        self.win_set.title("Binance Position Simulator")
        self.win_set.config(bg="#1e2329")
        self.win_set.protocol("WM_DELETE_WINDOW", self.on_closing)"""
init_replace = """        self.is_float_mode = is_float_mode
        self.win_set = tk.Toplevel(self.root)
        self.win_set.title("Binance Position Simulator")
        self.win_set.config(bg="#1e2329")
        self.win_set.protocol("WM_DELETE_WINDOW", self.on_closing)
        if is_float_mode:
            self.win_set.withdraw()"""
content = content.replace(init_search, init_replace)

# 2. Fix gear icon in float mode to just close (since settings is already open in main app) or hide it
setup_floating_search = """        tk.Button(f, text="✖", command=self.close_widget, bg=self.trans_key, fg="#ff3d57", bd=0, font=("Arial", 10, "bold"), cursor="hand2").pack(side=tk.RIGHT, padx=(2, 4))
        tk.Button(f, text="⚙", command=self.show_settings, bg=self.trans_key, fg="#aaa", bd=0, font=("Arial", 10), cursor="hand2").pack(side=tk.RIGHT, padx=4)"""
setup_floating_replace = """        tk.Button(f, text="✖", command=self.close_widget, bg=self.trans_key, fg="#ff3d57", bd=0, font=("Arial", 10, "bold"), cursor="hand2").pack(side=tk.RIGHT, padx=(2, 4))
        if not getattr(self, 'is_float_mode', False):
            tk.Button(f, text="⚙", command=self.show_settings, bg=self.trans_key, fg="#aaa", bd=0, font=("Arial", 10), cursor="hand2").pack(side=tk.RIGHT, padx=4)"""
content = content.replace(setup_floating_search, setup_floating_replace)

# 3. close_widget must kill the process if in float mode
close_widget_search = """    def close_widget(self):
        self.ws_keep_running = False
        if self.ws:
            try: self.ws.close()
            except: pass
        self.win_bg.withdraw()
        self.win_fg.withdraw()
        self.close_full_chart()
        self.close_hover_chart()"""
close_widget_replace = """    def close_widget(self):
        self.ws_keep_running = False
        if self.ws:
            try: self.ws.close()
            except: pass
        self.win_bg.withdraw()
        self.win_fg.withdraw()
        self.close_full_chart()
        self.close_hover_chart()
        if getattr(self, 'is_float_mode', False):
            self.root.destroy()
            import sys
            sys.exit(0)"""
content = content.replace(close_widget_search, close_widget_replace)

# 4. In start_simulation, we also don't want the original win_bg/win_fg to show up if it's main process
start_sim_search = """        subprocess.Popen([sys.executable, sys.argv[0], "--float", sim_json])
        
        # Do not close the settings window so they can launch more
        # self.win_set.withdraw()"""
start_sim_replace = """        # If this is the main process, we spawn a subprocess and KEEP the settings window open!
        if not getattr(self, 'is_float_mode', False):
            subprocess.Popen([sys.executable, sys.argv[0], "--float", sim_json], creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        else:
            self.launch_float_window()"""
content = content.replace(start_sim_search, start_sim_replace)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fix applied.")
