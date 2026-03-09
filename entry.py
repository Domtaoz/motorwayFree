import tkinter as tk
import threading
import time
import ftp_manager
import traceback

from smartcard.System import readers
from smartcard.util import toHexString

is_reading = False
need_sync = False

# 1. เพิ่ม Lock สำหรับจัดการไฟล์ ป้องกันไฟล์พังจากการแย่งกันอ่าน/เขียน
db_lock = threading.Lock()

# 2. เพิ่ม Dictionary เก็บเวลาที่แตะบัตรล่าสุดของแต่ละ UID (Debounce/Cooldown)
nfc_cooldowns = {}
COOLDOWN_SECONDS = 5 # ห้ามแตะบัตรใบเดิมซ้ำภายใน 5 วินาที

def process_c_sync(uid, station):
    global need_sync
    
    try:
        # ใช้ Lock ก่อนทำอะไรกับไฟล์ DB เสมอ
        with db_lock:
            db = ftp_manager.load_local_db()
            if uid in db:
                db[uid]['entry_station'] = station
                if 'transactions' not in db[uid]: 
                    db[uid]['transactions'] = []
                db[uid]['transactions'].append(f"[{time.strftime('%H:%M:%S')}] เข้าด่าน: {station}")
                
                ftp_manager.save_local_db(db)
                need_sync = True 
                
        root.after(0, lambda: lbl_log.config(text=f"Log (Thread C): [Success] บันทึกเข้าด่าน ({station}) รอส่ง FTP", fg=SUCCESS))
    except Exception as e:
        print(f"Error in process_c_sync: {e}")
        traceback.print_exc()
        root.after(0, lambda: lbl_log.config(text=f"Log (Thread C): [Error] เกิดข้อผิดพลาดในการบันทึก", fg=ERROR))
    finally:
        # ปลดล็อค UI ให้กลับมากดเปลี่ยนสถานีได้
        root.after(0, toggle_station_ui, tk.NORMAL)

def check_toll_logic(uid):
    selected_station = station_var.get()
    current_time = time.time()
    
    # Check if a station is selected
    if not selected_station:
        lbl_status.config(text="[Warning] กรุณาเลือกสถานีก่อนสแกนบัตร", fg=WARNING)
        lbl_log.config(text="Log (Thread C): รอการทำงาน", fg=TEXT_SUB)
        return

    # เช็ค Cooldown ป้องกันการแตะรัวๆ (Tailgating)
    if uid in nfc_cooldowns:
        if current_time - nfc_cooldowns[uid] < COOLDOWN_SECONDS:
            lbl_status.config(text="[Warning] แตะบัตรเร็วเกินไป กรุณารอสักครู่", fg=WARNING)
            return
    
    # อัปเดตเวลาแตะล่าสุด
    nfc_cooldowns[uid] = current_time

    # ล็อค UI ห้ามเปลี่ยนสถานีกลางอากาศ
    toggle_station_ui(tk.DISABLED)

    lbl_log.config(text="Log (Thread C): [Info] กำลังประมวลผลบัตรใหม่...", fg=ACCENT)
    
    try:
        with db_lock:
            db = ftp_manager.load_local_db()
    except Exception as e:
        lbl_status.config(text="[Error] ไม่สามารถโหลดฐานข้อมูลได้", fg=ERROR)
        toggle_station_ui(tk.NORMAL)
        return

    lbl_card.config(text=f"Card ID: {uid}")
    
    if uid not in db:
        lbl_status.config(text="บัตรยังไม่ลงทะเบียน", fg=ERROR)
        toggle_station_ui(tk.NORMAL)
        return

    balance = db.get(uid, {}).get('balance', 0)
    
    # Check if already entered
    if db[uid].get('entry_station'):
         lbl_status.config(text=f"บัตรนี้เข้าด่านแล้ว ({db[uid]['entry_station']}) กรุณาออกด่านก่อน", fg=ERROR)
         toggle_station_ui(tk.NORMAL)
         return

    if balance < 200:
        lbl_status.config(text=f"ยอดเงินไม่พอ! ({balance} บ.) ไม่เปิดไม้กั้น", fg=ERROR)
        toggle_station_ui(tk.NORMAL)
    else:
        lbl_status.config(text=f"ยอดเงิน {balance} บ. >> เปิดไม้กั้นเข้า {selected_station}", fg=SUCCESS)
        # ส่ง selected_station ไปให้ Thread แยก เพื่อไม่ให้สับสนถ้าเผลอเปลี่ยนค่า
        threading.Thread(target=process_c_sync, args=(uid, selected_station)).start()

def sync_every_5_mins():
    global need_sync
    while True:
        time.sleep(15)
        if need_sync:
            try:
                # ล็อคก่อนจะอัปโหลด เพื่อไม่ให้ชนกับการเขียน DB ข้างล่าง
                with db_lock:
                    ftp_manager.upload_db()
                need_sync = False 
                print(f"[{time.strftime('%H:%M:%S')}] FTP Sync Successful.")
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] FTP Sync Error: {e}")

def nfc_loop():
    try:
        available_readers = readers()
        if not available_readers: 
            print("No NFC readers found.")
            return
            
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
                        root.after(10, check_toll_logic, uid) 
                        last_uid = uid
                        time.sleep(1)
            except Exception:
                if last_uid != "": last_uid = ""
            time.sleep(0.2)
    except Exception as e: 
        print(f"NFC Error: {e}")

# Colors 
BG_COLOR = "#F4F7F4"
CARD_BG = "#FFFFFF"
TEXT_MAIN = "#2C3E2D"
TEXT_SUB = "#6B7A6F"
ACCENT = "#52796F"
SUCCESS = "#40916C"
ERROR = "#D96C6C"
WARNING = "#F2B872"

# Font setting
FONT_FAMILY = "Segoe UI"

def btn_start():
    global is_reading
    is_reading = True
    lbl_nfc_status.config(text="[Status] กำลังสแกนบัตร...", fg=ACCENT)

def btn_stop():
    global is_reading
    is_reading = False
    lbl_nfc_status.config(text="[Status] หยุดสแกน", fg=TEXT_SUB)

def toggle_station_ui(state):
    try:
        for btn in station_buttons.values():
            btn.config(state=state)
    except NameError:
        pass

def fExit():
    root.destroy()

root = tk.Tk()
root.geometry("500x700")
root.title("NFC Tollway - Entry System")
root.configure(bg=BG_COLOR)
root.resizable(False, False)

# --- Header Section -
header_frame = tk.Frame(root, bg=BG_COLOR)
header_frame.pack(fill="x", padx=25, pady=(20, 10))

tk.Label(header_frame, text="ENTRY STATION", font=(FONT_FAMILY, 12, "bold"), fg=ACCENT, bg=BG_COLOR).pack(anchor="w")
tk.Label(header_frame, text="Entry System", font=(FONT_FAMILY, 26, "bold"), fg=TEXT_MAIN, bg=BG_COLOR).pack(anchor="w")

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

tk.Label(card1, text="Select Entry Station", font=(FONT_FAMILY, 14, "bold"), fg=TEXT_MAIN, bg=CARD_BG).pack(anchor="w", pady=(0, 10))

station_var = tk.StringVar(value="")
stations_frame = tk.Frame(card1, bg=CARD_BG)
stations_frame.pack(fill="x")

def select_station(val, btn_ref):
    if station_var.get() == val:
        station_var.set("")
    else:
        station_var.set(val)
    
    for b_val, b_widget in station_buttons.items():
        if station_var.get() == b_val:
            b_widget.config(bg=ACCENT, fg="#FFFFFF")
        else:
            b_widget.config(bg=CARD_BG, fg=TEXT_MAIN)

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

lbl_log = tk.Label(card3, text="Log (Thread C): รอการทำงาน", font=(FONT_FAMILY, 10), bg=CARD_BG, fg=TEXT_SUB, wraplength=400, justify="center")
lbl_log.pack(side="bottom", pady=(5, 0))

threading.Thread(target=nfc_loop, daemon=True).start()
threading.Thread(target=sync_every_5_mins, daemon=True).start()
root.mainloop()