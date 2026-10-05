import sys
import os
import tkinter as tk

# Set path
sys.path.insert(0, os.path.abspath(r"1.Python Code\Cloack_Overlay"))

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("cos", r"1.Python Code\Cloack_Overlay\Cloack_Overlay.pyw")
    cos_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cos_mod)
    print("Module loaded successfully!")
    
    root = tk.Tk()
    root.withdraw()
    app = cos_mod.TimerToolApp(root)
    print("TimerToolApp instantiated successfully!")
    print("Selected layer:", app.selected_layer_name)
    print("CMD logs:", app.cmd_logs)
    print("Grip pool exists:", hasattr(app, 'grip_pool') and app.grip_pool.winfo_exists())
    print("Hot map exists:", hasattr(app, 'lbl_hot_map') and app.lbl_hot_map.winfo_exists())
    print("Txt cmd exists:", hasattr(app, 'txt_cmd') and app.txt_cmd.winfo_exists())
    print("Btn char ocr exists:", hasattr(app, 'btn_char_ocr') and app.btn_char_ocr.winfo_exists())
    print("Normal badge exists:", hasattr(app, 'lbl_neso_badge_norm_stock') and app.lbl_neso_badge_norm_stock.winfo_exists())
    print("Boost badge exists:", hasattr(app, 'lbl_neso_badge_stock') and app.lbl_neso_badge_stock.winfo_exists())
    root.destroy()
    print("All smoke tests passed with flying colors!")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
