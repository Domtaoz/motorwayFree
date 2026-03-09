import tkinter as tk
import threading
import time
import ftp_manager

from smartcard.System import readers
from smartcard.util import toHexString

is_reading = False
need_sync = False

def calculate_toll(entry_station, exit_station):
    # Extract numbers from strings like "Station 1"
    try:
        entry_num = int(entry_station.split()[1])
        exit_num = int(exit_station.split()[1])
        difference = abs(entry_num - exit_num)
        
        if difference == 1:
            return 50
        elif difference == 2:
            return 100
        elif difference == 3:
            return 150
        else:
            return 0 # Should only happen if entry == exit, handled elsewhere
    except:
        return 0

def process_cd_sync(uid, fee, exit_station):
    global need_sync
    db = ftp_manager.load_local_db()
    if uid in db:
        entry_station = db[uid].get('entry_station', 'ไม่ระบุ')
        db[uid]['balance'] -= fee
        db[uid]['entry_station'] = "" # Clear status
        
        if 'transactions' not in db[uid]: db[uid]['transactions'] = []
        db[uid]['transactions'].append(f"[{time.strftime('%H:%M:%S')}] ออกด่าน: {exit_station} (จาก {entry_station}) หัก -{fee} บาท")
        
        ftp_manager.save_local_db(db)
        need_sync = True 
        
    try:
        root.after(0, lambda: lbl_log.config(text=f"Log (Thread C,D): ✅ หักเงิน {fee} บ. และรอส่ง FTP รอบถัดไป", fg=SUCCESS))
    except RuntimeError: pass

def exit_toll_logic(uid):
    selected_exit_station = station_var.get()
    
    if not selected_exit_station:
        lbl_status.config(text="⚠️ กรุณาเลือกสถานีก่อนสแกนบัตร", fg=WARNING)
        lbl_log.config(text="Log (Thread C,D): รอการทำงาน", fg=TEXT_SUB)
        return

    lbl_log.config(text="Log (Thread C,D): ⚙ กำลังประมวลผลบัตรใหม่...", fg=ACCENT)
    db = ftp_manager.load_local_db()
    lbl_card.config(text=f"Card ID: {uid}")
    
    if uid not in db or not db[uid].get('entry_station'):
        lbl_status.config(text="ไม่พบข้อมูลการเข้าด่าน", fg=ERROR)
        return

    entry_station = db[uid]['entry_station']
    balance = db[uid]['balance']
    
    if entry_station == selected_exit_station:
         lbl_status.config(text=f"คุณเข้าจาก {entry_station}\nนี่คือสถานีเดิม ไม่คิดค่าบริการ", fg=TEXT_MAIN)
         lbl_log.config(text="Log (Thread C,D): ยกเลิกการหักเงิน (สถานีเดิม)", fg=TEXT_SUB)
         return 

    toll_fee = calculate_toll(entry_station, selected_exit_station)
    
    if balance < toll_fee:
        lbl_status.config(text=f"ยอดเงินไม่พอจ่ายค่าทางด่วน ({balance} บ. ขาดอีก {toll_fee-balance} บ.)", fg=ERROR)
    else:
        lbl_status.config(text=f"เข้าจาก: {entry_station}\nค่าทางด่วน: {toll_fee} บ.\n>> เปิดไม้กั้นออก {selected_exit_station}", fg=SUCCESS)
        threading.Thread(target=process_cd_sync, args=(uid, toll_fee, selected_exit_station)).start()

def sync_every_5_mins():
    global need_sync
    while True:
        time.sleep(15) # Changed to 15s for faster testing
        if need_sync:
            try:
                ftp_manager.upload_db()
                need_sync = False 
            except Exception: pass

def nfc_loop():
    try:
        available_readers = readers()
        if not available_readers: return
        reader = available_readers[0]
        GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        last_uid = ""
        while True:
            if not is_reading:
                last_uid = ""
                time.sleep(0.5)
                continue
            try:
                connection = reader.createConnection()
                connection.connect()
                data, sw1, sw2 = connection.transmit(GET_UID)
                if sw1 == 144 and sw2 == 0:
                    uid = toHexString(data).replace(" ", "")
                    if uid and uid != last_uid:
                        root.after(10, exit_toll_logic, uid) 
                        last_uid = uid
                        time.sleep(2)
            except Exception:
                if last_uid != "": last_uid = ""
            time.sleep(0.5)
    except Exception as e: print(f"NFC Error: {e}")

def btn_start():
    global is_reading
    is_reading = True
    lbl_nfc_status.config(text="🟢 สถานะ: กำลังสแกนบัตร...", fg=ACCENT)

def btn_stop():
    global is_reading
    is_reading = False
    lbl_nfc_status.config(text="🔴 สถานะ: หยุดสแกน", fg=TEXT_SUB)

def fExit():
    root.destroy()

# --- Minimalist Green Theme UI ---
# Colors (Matcha/Sage Minimalist Mode)
BG_COLOR = "#F4F7F4"         # Very soft warm green/gray background
CARD_BG = "#FFFFFF"          # White - Elevated card background
TEXT_MAIN = "#2C3E2D"        # Deep moss green for primary text
TEXT_SUB = "#6B7A6F"         # Muted sage for secondary text
ACCENT = "#52796F"           # Elegant muted green
SUCCESS = "#40916C"          # Success green
ERROR = "#D96C6C"            # Pastel red
WARNING = "#F2B872"          # Soft warm yellow

# Font setting
FONT_FAMILY = "Segoe UI"

root = tk.Tk()
root.geometry("500x700")
root.title("NFC Tollway - Modern")
root.configure(bg=BG_COLOR)
root.resizable(False, False)

# --- Header Section ---
header_frame = tk.Frame(root, bg=BG_COLOR)
header_frame.pack(fill="x", padx=25, pady=(20, 10))

tk.Label(header_frame, text="EXIT STATION", font=(FONT_FAMILY, 12, "bold"), fg=ACCENT, bg=BG_COLOR).pack(anchor="w")
tk.Label(header_frame, text="Exit System", font=(FONT_FAMILY, 26, "bold"), fg=TEXT_MAIN, bg=BG_COLOR).pack(anchor="w")

# Bottom Exit Pill Base
bottom_pill = tk.Frame(root, bg=BG_COLOR)
bottom_pill.pack(side="bottom", fill="x", pady=10)

tk.Button(bottom_pill, text="EXIT", font=(FONT_FAMILY, 11, "bold"), command=fExit, 
          bg="#E8ECE8", fg=TEXT_SUB, relief="flat", bd=0, cursor="hand2", 
          activebackground=ERROR, activeforeground="#FFFFFF", width=35, pady=8
          ).pack()

# --- Content Area ---
container_frame = tk.Frame(root, bg=BG_COLOR)
container_frame.pack(fill="both", expand=True, padx=20)

canvas = tk.Canvas(container_frame, bg=BG_COLOR, highlightthickness=0)
scrollbar = tk.Scrollbar(container_frame, orient="vertical", command=canvas.yview)

content_frame = tk.Frame(canvas, bg=BG_COLOR)

content_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

canvas_window = canvas.create_window((0, 0), window=content_frame, anchor="nw")

def _on_canvas_configure(event):
    canvas.itemconfig(canvas_window, width=event.width)
canvas.bind("<Configure>", _on_canvas_configure)

def _on_mousewheel(event):
    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
canvas.bind_all("<MouseWheel>", _on_mousewheel)

canvas.configure(yscrollcommand=scrollbar.set)
canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# 1. Station Selection Card
card1 = tk.Frame(content_frame, bg=CARD_BG, padx=20, pady=15)
card1.pack(fill="x", pady=(5, 10))

tk.Label(card1, text="Select Exit Station", font=(FONT_FAMILY, 14, "bold"), fg=TEXT_MAIN, bg=CARD_BG).pack(anchor="w", pady=(0, 10))

station_var = tk.StringVar(value="")
stations_frame = tk.Frame(card1, bg=CARD_BG)
stations_frame.pack(fill="x")

def select_station(val, btn_ref):
    if station_var.get() == val:
        # If already selected, unselect it
        station_var.set("")
    else:
        station_var.set(val)
    
    # Update UI for all buttons based on selection
    for b_val, b_widget in station_buttons.items():
        if station_var.get() == b_val:
            b_widget.config(bg=ACCENT, fg="#FFFFFF") # Selected state
        else:
            b_widget.config(bg=CARD_BG, fg=TEXT_MAIN) # Unselected state

station_buttons = {}
for val in ["สถานี 1", "สถานี 2", "สถานี 3", "สถานี 4"]:
    btn = tk.Button(stations_frame, text=val, font=(FONT_FAMILY, 12, "bold"), 
                   bg=CARD_BG, fg=TEXT_MAIN, activebackground=BG_COLOR, activeforeground=ACCENT,
                   cursor="hand2", highlightthickness=0, bd=0, relief="flat")
    btn.config(command=lambda v=val, b=btn: select_station(v, b))
    btn.pack(side="left", expand=True, fill="x", padx=4, ipady=5)
    station_buttons[val] = btn

# 2. Scanner Controls Card
card2 = tk.Frame(content_frame, bg=CARD_BG, padx=20, pady=15)
card2.pack(fill="x", pady=5)

tk.Label(card2, text="Scanner Controls", font=(FONT_FAMILY, 14, "bold"), fg=TEXT_MAIN, bg=CARD_BG).pack(anchor="w", pady=(0, 10))

ctrl_frame = tk.Frame(card2, bg=CARD_BG)
ctrl_frame.pack(fill="x")

# Big bold buttons
tk.Button(ctrl_frame, text="START NFC", bg=SUCCESS, fg="#FFFFFF", font=(FONT_FAMILY, 12, "bold"), 
          command=btn_start, relief="flat", cursor="hand2", activebackground="#059669", activeforeground="white", bd=0
          ).pack(side="left", expand=True, fill="x", padx=(0, 5), ipady=8)

tk.Button(ctrl_frame, text="STOP", bg=ERROR, fg="#FFFFFF", font=(FONT_FAMILY, 12, "bold"), 
          command=btn_stop, relief="flat", cursor="hand2", activebackground="#DC2626", activeforeground="white", bd=0
          ).pack(side="right", expand=True, fill="x", padx=(5, 0), ipady=8)

lbl_nfc_status = tk.Label(card2, text="Scanner is stopped", font=(FONT_FAMILY, 11), bg=CARD_BG, fg=TEXT_SUB)
lbl_nfc_status.pack(pady=(10, 5))

# 3. Status display Card
card3 = tk.Frame(content_frame, bg=CARD_BG, padx=20, pady=15)
card3.pack(fill="both", expand=True, pady=(5, 5))

lbl_card = tk.Label(card3, text="แตะบัตรเพื่ออ่าน...", font=(FONT_FAMILY, 12), bg=CARD_BG, fg=TEXT_SUB)
lbl_card.pack(pady=(5, 5))

lbl_status = tk.Label(card3, text="-", font=(FONT_FAMILY, 16, "bold"), bg=CARD_BG, fg=TEXT_MAIN, wraplength=380, justify="center")
lbl_status.pack(pady=10, expand=True)

lbl_log = tk.Label(card3, text="Log (Thread C,D): รอการทำงาน", font=(FONT_FAMILY, 10), bg=CARD_BG, fg=TEXT_SUB, wraplength=400, justify="center")
lbl_log.pack(side="bottom", pady=(5, 0))

# Bottom exit pill moved above content frame to prevent layout shifting

threading.Thread(target=nfc_loop, daemon=True).start()
threading.Thread(target=sync_every_5_mins, daemon=True).start()
root.mainloop()