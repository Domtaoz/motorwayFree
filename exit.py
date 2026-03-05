import tkinter as tk
import threading
import time
import ftp_manager

from smartcard.System import readers
from smartcard.util import toHexString

is_reading = False
need_sync = False

def calculate_toll(entry_station, exit_station):
    # Extract numbers from strings like "สถานี 1"
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
        root.after(0, lambda: lbl_log.config(text=f"Log (Thread C,D): ✅ หักเงิน {fee} บ. และรอส่ง FTP รอบถัดไป", fg="green"))
    except RuntimeError: pass

def exit_toll_logic(uid):
    selected_exit_station = station_var.get()
    
    if not selected_exit_station:
        lbl_status.config(text="⚠️ กรุณาเลือกสถานีก่อนสแกนบัตร", fg="orange")
        lbl_log.config(text="Log (Thread C,D): รอการทำงาน", fg="blue")
        return

    lbl_log.config(text="Log (Thread C,D): ⚡ กำลังประมวลผลบัตรใหม่...", fg="blue")
    db = ftp_manager.load_local_db()
    lbl_card.config(text=f"Card ID: {uid}")
    
    if uid not in db or not db[uid].get('entry_station'):
        lbl_status.config(text="ไม่พบข้อมูลการเข้าด่าน", fg="red")
        return

    entry_station = db[uid]['entry_station']
    balance = db[uid]['balance']
    
    if entry_station == selected_exit_station:
         lbl_status.config(text=f"คุณเข้าจาก {entry_station}\nนี่คือสถานีเดิม ไม่คิดค่าบริการ", fg="blue")
         lbl_log.config(text="Log (Thread C,D): ยกเลิกการหักเงิน (สถานีเดิม)", fg="blue")
         return # Stop here, don't deduct fee, don't clear entry

    toll_fee = calculate_toll(entry_station, selected_exit_station)
    
    if balance < toll_fee:
        lbl_status.config(text=f"ยอดเงินไม่พอจ่ายค่าทางด่วน ({balance} บ. ขาดอีก {toll_fee-balance} บ.)", fg="red")
    else:
        lbl_status.config(text=f"เข้าจาก: {entry_station}\nค่าทางด่วน: {toll_fee} บ.\n>> เปิดไม้กั้นออก {selected_exit_station}", fg="green")
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
    lbl_nfc_status.config(text="🟢 สถานะ: กำลังสแกนบัตร...", fg="green")

def btn_stop():
    global is_reading
    is_reading = False
    lbl_nfc_status.config(text="🔴 สถานะ: หยุดสแกน", fg="red")

def fExit():
    root.destroy()

root = tk.Tk()
root.geometry("550x550")
root.title("NFC Tollway - ด่านทางออก")
tk.Label(root, text="ระบบด่านทางออก", font=("Arial", 20, "bold")).pack(pady=10)

# Station Selection
frame_station = tk.LabelFrame(root, text="เลือกสถานีทางออก")
frame_station.pack(pady=10)
station_var = tk.StringVar(value="") 
tk.Radiobutton(frame_station, text="สถานี 1", variable=station_var, value="สถานี 1", font=("Arial", 12)).pack(side="left", padx=5)
tk.Radiobutton(frame_station, text="สถานี 2", variable=station_var, value="สถานี 2", font=("Arial", 12)).pack(side="left", padx=5)
tk.Radiobutton(frame_station, text="สถานี 3", variable=station_var, value="สถานี 3", font=("Arial", 12)).pack(side="left", padx=5)
tk.Radiobutton(frame_station, text="สถานี 4", variable=station_var, value="สถานี 4", font=("Arial", 12)).pack(side="left", padx=5)


frame_ctrl = tk.Frame(root)
frame_ctrl.pack(pady=5)
tk.Button(frame_ctrl, text="▶ Start NFC", bg="#ccffcc", font=("Arial", 12), command=btn_start).grid(row=0, column=0, padx=10)
tk.Button(frame_ctrl, text="⏹ Stop NFC", bg="#ffcccc", font=("Arial", 12), command=btn_stop).grid(row=0, column=1, padx=10)

lbl_nfc_status = tk.Label(root, text="🔴 สถานะ: หยุดสแกน", font=("Arial", 12, "bold"), fg="red")
lbl_nfc_status.pack()
tk.Label(root, text="-"*40).pack(pady=5)
lbl_card = tk.Label(root, text="แตะบัตรเพื่ออ่าน...", font=("Arial", 16))
lbl_card.pack()
lbl_status = tk.Label(root, text="-", font=("Arial", 14, "bold"))
lbl_status.pack(pady=15)
lbl_log = tk.Label(root, text="Log (Thread C,D): รอการทำงาน", font=("Arial", 12), fg="blue")
lbl_log.pack(pady=5)
tk.Button(root, padx=16, pady=8, bd=8, fg="black", font=('Arial', 14, 'bold'), width=10, text="Exit", bg="#ffcccc", command=fExit).pack(side="bottom", pady=15)

threading.Thread(target=nfc_loop, daemon=True).start()
threading.Thread(target=sync_every_5_mins, daemon=True).start()
root.mainloop()