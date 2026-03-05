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
                
        root.after(0, lambda: lbl_log.config(text=f"Log (Thread C): [Success] บันทึกเข้าด่าน ({station}) รอส่ง FTP", fg="green"))
    except Exception as e:
        print(f"Error in process_c_sync: {e}")
        traceback.print_exc()
        root.after(0, lambda: lbl_log.config(text=f"Log (Thread C): [Error] เกิดข้อผิดพลาดในการบันทึก", fg="red"))
    finally:
        # ปลดล็อค UI ให้กลับมากดเปลี่ยนสถานีได้
        root.after(0, toggle_station_ui, tk.NORMAL)

def check_toll_logic(uid):
    selected_station = station_var.get()
    current_time = time.time()
    
    # Check if a station is selected
    if not selected_station:
        lbl_status.config(text="[Warning] กรุณาเลือกสถานีก่อนสแกนบัตร", fg="orange")
        lbl_log.config(text="Log (Thread C): รอการทำงาน", fg="blue")
        return

    # เช็ค Cooldown ป้องกันการแตะรัวๆ (Tailgating)
    if uid in nfc_cooldowns:
        if current_time - nfc_cooldowns[uid] < COOLDOWN_SECONDS:
            lbl_status.config(text="[Warning] แตะบัตรเร็วเกินไป กรุณารอสักครู่", fg="orange")
            return
    
    # อัปเดตเวลาแตะล่าสุด
    nfc_cooldowns[uid] = current_time

    # ล็อค UI ห้ามเปลี่ยนสถานีกลางอากาศ
    toggle_station_ui(tk.DISABLED)

    lbl_log.config(text="Log (Thread C): [Info] กำลังประมวลผลบัตรใหม่...", fg="blue")
    
    try:
        with db_lock:
            db = ftp_manager.load_local_db()
    except Exception as e:
        lbl_status.config(text="[Error] ไม่สามารถโหลดฐานข้อมูลได้", fg="red")
        toggle_station_ui(tk.NORMAL)
        return

    lbl_card.config(text=f"Card ID: {uid}")
    
    if uid not in db:
        lbl_status.config(text="บัตรยังไม่ลงทะเบียน", fg="red")
        toggle_station_ui(tk.NORMAL)
        return

    balance = db.get(uid, {}).get('balance', 0)
    
    # Check if already entered
    if db[uid].get('entry_station'):
         lbl_status.config(text=f"บัตรนี้เข้าด่านแล้ว ({db[uid]['entry_station']}) กรุณาออกด่านก่อน", fg="red")
         toggle_station_ui(tk.NORMAL)
         return

    if balance < 200:
        lbl_status.config(text=f"ยอดเงินไม่พอ! ({balance} บ.) ไม่เปิดไม้กั้น", fg="red")
        toggle_station_ui(tk.NORMAL)
    else:
        lbl_status.config(text=f"ยอดเงิน {balance} บ. >> เปิดไม้กั้นเข้า {selected_station}", fg="green")
        # ส่ง selected_station ไปให้ Thread แยก เพื่อไม่ให้สับสนถ้าเผลอเปลี่ยนค่า
        threading.Thread(target=process_c_sync, args=(uid, selected_station)).start()

def sync_every_5_mins():
    global need_sync
    while True:
        time.sleep(1)
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

def btn_start():
    global is_reading
    is_reading = True
    lbl_nfc_status.config(text="[Status] กำลังสแกนบัตร...", fg="green")

def btn_stop():
    global is_reading
    is_reading = False
    lbl_nfc_status.config(text="[Status] หยุดสแกน", fg="red")

def toggle_station_ui(state):
    rb_station1.config(state=state)
    rb_station2.config(state=state)
    rb_station3.config(state=state)
    rb_station4.config(state=state)

def fExit():
    root.destroy()

# === UI Setup ===
root = tk.Tk()
root.geometry("550x550")
root.title("NFC Tollway - ด่านทางเข้า")
tk.Label(root, text="ระบบด่านทางเข้า", font=("Arial", 20, "bold")).pack(pady=10)

frame_station = tk.LabelFrame(root, text="เลือกสถานีทางเข้า")
frame_station.pack(pady=10)
station_var = tk.StringVar(value="") 

rb_station1 = tk.Radiobutton(frame_station, text="สถานี 1", variable=station_var, value="สถานี 1", font=("Arial", 12))
rb_station1.pack(side="left", padx=5)
rb_station2 = tk.Radiobutton(frame_station, text="สถานี 2", variable=station_var, value="สถานี 2", font=("Arial", 12))
rb_station2.pack(side="left", padx=5)
rb_station3 = tk.Radiobutton(frame_station, text="สถานี 3", variable=station_var, value="สถานี 3", font=("Arial", 12))
rb_station3.pack(side="left", padx=5)
rb_station4 = tk.Radiobutton(frame_station, text="สถานี 4", variable=station_var, value="สถานี 4", font=("Arial", 12))
rb_station4.pack(side="left", padx=5)

frame_ctrl = tk.Frame(root)
frame_ctrl.pack(pady=5)
tk.Button(frame_ctrl, text="Start NFC", bg="#ccffcc", font=("Arial", 12), command=btn_start).grid(row=0, column=0, padx=10)
tk.Button(frame_ctrl, text="Stop NFC", bg="#ffcccc", font=("Arial", 12), command=btn_stop).grid(row=0, column=1, padx=10)

lbl_nfc_status = tk.Label(root, text="[Status] หยุดสแกน", font=("Arial", 12, "bold"), fg="red")
lbl_nfc_status.pack()
tk.Label(root, text="-"*40).pack(pady=5)
lbl_card = tk.Label(root, text="แตะบัตรเพื่ออ่าน...", font=("Arial", 16))
lbl_card.pack()
lbl_status = tk.Label(root, text="-", font=("Arial", 14, "bold"))
lbl_status.pack(pady=15)
lbl_log = tk.Label(root, text="Log (Thread C): รอการทำงาน", font=("Arial", 12), fg="blue")
lbl_log.pack(pady=5)
tk.Button(root, padx=16, pady=8, bd=8, fg="black", font=('Arial', 14, 'bold'), width=10, text="Exit", bg="#ffcccc", command=fExit).pack(side="bottom", pady=15)

threading.Thread(target=nfc_loop, daemon=True).start()
threading.Thread(target=sync_every_5_mins, daemon=True).start()
root.mainloop()