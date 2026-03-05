import tkinter as tk
import threading
import time
import smtplib
from email.mime.text import MIMEText
import random
import ftp_manager

from smartcard.System import readers
from smartcard.util import toHexString

SENDER_EMAIL = "pollapat.r@ku.th" 
APP_PASSWORD = "spok yxyq gjtr iitc "

current_uid = ""
generated_otp = ""
registering_uid = "" 
is_reading = False

# ตัวแปรสำหรับเช็คว่ามีข้อมูลใหม่อัปเดตหรือไม่
need_sync = False 

def process_send_otp_thread(email, otp, target_uid):
    try:
        msg = MIMEText(f"รหัส OTP ของคุณคือ: {otp}")
        msg['Subject'] = 'NFC Tollway - OTP Verification'
        msg['From'] = SENDER_EMAIL
        msg['To'] = email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, email, msg.as_string())
        server.quit()
        root.after(0, lambda: on_otp_sent_success(target_uid))
    except Exception as e:
        root.after(0, lambda: on_otp_sent_fail())

def on_otp_sent_success(target_uid):
    global registering_uid
    registering_uid = target_uid 
    lbl_msg.config(text="✅ ส่งรหัส OTP ไปที่อีเมลแล้ว!", fg="green")
    if current_uid == registering_uid:
        entry_otp.config(state="normal")
        btn_verify_otp.config(state="normal")
    btn_send_otp.config(state="normal", text="ส่งใหม่อีกครั้ง")

def on_otp_sent_fail():
    lbl_msg.config(text="❌ ส่งอีเมลไม่สำเร็จ เช็คเน็ตหรือรหัสผ่าน", fg="red")
    btn_send_otp.config(state="normal", text="ลองใหม่")

def check_card_logic(uid):
    global current_uid
    
    # --- เคลียร์ข้อมูลทุกช่อง หากตรวจพบว่าเป็นบัตรคนละใบกับรอบที่แล้ว ---
    if uid != current_uid:
        entry_email.config(state="normal")
        entry_email.delete(0, 'end')
        entry_otp.config(state="normal")
        entry_otp.delete(0, 'end')
        entry_topup.config(state="normal")
        entry_topup.delete(0, 'end')
    # -----------------------------------------------------------

    current_uid = uid
    lbl_msg.config(text="⚡ กำลังดึงข้อมูลบัตร...", fg="blue") 
    db = ftp_manager.load_local_db()
    lbl_card.config(text=f"Card ID: {uid}")
    
    if uid not in db:
        lbl_status.config(text="บัตรใหม่! กรุณากรอกอีเมลเพื่อลงทะเบียน", fg="blue")
        lbl_msg.config(text="") 
        entry_email.config(state="normal")
        btn_send_otp.config(state="normal", text="รับ OTP")
        if uid == registering_uid:
            entry_otp.config(state="normal")
            btn_verify_otp.config(state="normal")
        else:
            entry_otp.config(state="disabled")
            btn_verify_otp.config(state="disabled")
        entry_topup.config(state="disabled")
        btn_topup.config(state="disabled")
    else:
        balance = db[uid].get('balance', 0)
        lbl_status.config(text=f"บัตรนี้ลงทะเบียนแล้ว\nยอดเงินคงเหลือ: {balance} บาท", fg="green")
        lbl_msg.config(text="") 
        entry_topup.config(state="normal")
        btn_topup.config(state="normal")
        entry_email.config(state="disabled")
        btn_send_otp.config(state="disabled")
        entry_otp.config(state="disabled")
        btn_verify_otp.config(state="disabled")

def handle_send_otp():
    global generated_otp
    email = entry_email.get()
    if email:
        lbl_msg.config(text="⏳ กำลังส่ง OTP ไปที่อีเมล...", fg="orange")
        btn_send_otp.config(state="disabled") 
        generated_otp = str(random.randint(100000, 999999))
        threading.Thread(target=process_send_otp_thread, args=(email, generated_otp, current_uid), daemon=True).start()
    else:
        lbl_msg.config(text="⚠️ กรุณากรอกอีเมลก่อน", fg="red")

def handle_verify_otp():
    global registering_uid, need_sync
    if current_uid != registering_uid:
        lbl_msg.config(text="❌ บัตรไม่ตรงกัน! กรุณาแตะบัตรใบที่ขอ OTP", fg="red")
        return
    if entry_otp.get() == generated_otp:
        db = ftp_manager.load_local_db()
        
        # เพิ่มโครงสร้าง Transaction แยกจากข้อมูล Master
        db[current_uid] = {
            "email": entry_email.get(), 
            "balance": 0, 
            "entry_station": "",
            "transactions": [f"[{time.strftime('%H:%M:%S')}] ลงทะเบียนบัตร"]
        }
        ftp_manager.save_local_db(db)
        need_sync = True # แจ้งเตือนว่ามีอัปเดต
        
        lbl_msg.config(text="✅ ลงทะเบียนสำเร็จ! สามารถเติมเงินได้เลย", fg="green")
        registering_uid = "" 
        entry_topup.config(state="normal")
        btn_topup.config(state="normal")
        entry_email.config(state="disabled")
        btn_send_otp.config(state="disabled")
        entry_otp.config(state="disabled")
        btn_verify_otp.config(state="disabled")
    else:
        lbl_msg.config(text="❌ OTP ไม่ถูกต้อง", fg="red")

def handle_topup():
    global need_sync
    try:
        amount = float(entry_topup.get())
        db = ftp_manager.load_local_db()
        
        db[current_uid]['balance'] += amount
        # เก็บประวัติการเติมเงินแยกต่างหาก
        db[current_uid]['transactions'].append(f"[{time.strftime('%H:%M:%S')}] เติมเงิน +{amount} บาท")
        ftp_manager.save_local_db(db)
        need_sync = True # แจ้งเตือนว่ามีอัปเดต
        
        lbl_msg.config(text=f"✅ เติมเงินสำเร็จ! (+{amount} บ.) รอส่งขึ้น FTP ในรอบถัดไป", fg="green")
        lbl_status.config(text=f"บัตรนี้ลงทะเบียนแล้ว\nยอดเงินคงเหลือ: {db[current_uid]['balance']} บาท", fg="green")
        entry_topup.delete(0, 'end')
    except:
        lbl_msg.config(text="⚠️ กรุณากรอกตัวเลขให้ถูกต้อง", fg="red")

def sync_every_5_mins():
    """ Thread ที่จะเช็คทุก 5 นาทีว่ามีการแตะบัตรไหม ถ้ามีถึงจะอัปโหลด (ประหยัดแบนด์วิดท์) """
    global need_sync
    while True:
        time.sleep(300) # 300 วินาที = 5 นาที (ตอนพรีเซนต์อาจารย์แนะนำให้แก้เป็น 30 วินาที จะได้เห็นผลไวๆ ครับ)
        if need_sync:
            print(f"[{time.strftime('%H:%M:%S')}] ⏳ ถึงรอบ 5 นาที: ตรวจพบข้อมูลอัปเดต กำลังส่ง FTP...")
            try:
                ftp_manager.upload_db()
                need_sync = False # รีเซ็ตสถานะเมื่อส่งเสร็จ
                print("✅ ส่ง FTP สำเร็จ")
            except Exception as e:
                print(f"❌ ส่ง FTP ไม่สำเร็จ: {e}")

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
                        root.after(10, check_card_logic, uid)
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
root.geometry("600x700")
root.title("ระบบ 7-Eleven - ลงทะเบียน & เติมเงิน")
tk.Label(root, text="แตะบัตรที่เครื่องอ่าน (7-Eleven)", font=("Arial", 16, "bold")).pack(pady=10)

frame_ctrl = tk.Frame(root)
frame_ctrl.pack(pady=5)
tk.Button(frame_ctrl, text="▶ Start NFC", bg="#ccffcc", font=("Arial", 12), command=btn_start).grid(row=0, column=0, padx=10)
tk.Button(frame_ctrl, text="⏹ Stop NFC", bg="#ffcccc", font=("Arial", 12), command=btn_stop).grid(row=0, column=1, padx=10)

lbl_nfc_status = tk.Label(root, text="🔴 สถานะ: หยุดสแกน", font=("Arial", 12, "bold"), fg="red")
lbl_nfc_status.pack()
tk.Label(root, text="-"*40).pack(pady=5)
lbl_card = tk.Label(root, text="Card ID: -", font=("Arial", 14))
lbl_card.pack()
lbl_status = tk.Label(root, text="-", font=("Arial", 14, "bold"))
lbl_status.pack(pady=10)
lbl_msg = tk.Label(root, text="", font=("Arial", 14, "bold"))
lbl_msg.pack(pady=5)

frame_reg = tk.LabelFrame(root, text="ลงทะเบียนผู้ใช้ใหม่", font=("Arial", 12))
frame_reg.pack(fill="x", padx=20, pady=5)
tk.Label(frame_reg, text="Email:").grid(row=0, column=0, padx=5, pady=5)
entry_email = tk.Entry(frame_reg, state="disabled", width=30)
entry_email.grid(row=0, column=1, padx=5, pady=5)
btn_send_otp = tk.Button(frame_reg, text="รับ OTP", state="disabled", command=handle_send_otp)
btn_send_otp.grid(row=0, column=2, padx=5, pady=5)
tk.Label(frame_reg, text="OTP:").grid(row=1, column=0, padx=5, pady=5)
entry_otp = tk.Entry(frame_reg, state="disabled", width=30)
entry_otp.grid(row=1, column=1, padx=5, pady=5)
btn_verify_otp = tk.Button(frame_reg, text="ยืนยัน", state="disabled", command=handle_verify_otp)
btn_verify_otp.grid(row=1, column=2, padx=5, pady=5)

frame_topup = tk.LabelFrame(root, text="เติมเงิน", font=("Arial", 12))
frame_topup.pack(fill="x", padx=20, pady=10)
tk.Label(frame_topup, text="จำนวนเงิน:").grid(row=0, column=0, padx=5, pady=5)
entry_topup = tk.Entry(frame_topup, state="disabled", width=30)
entry_topup.grid(row=0, column=1, padx=5, pady=5)
btn_topup = tk.Button(frame_topup, text="เติมเงิน", state="disabled", command=handle_topup)
btn_topup.grid(row=0, column=2, padx=5, pady=5)

tk.Button(root, padx=16, pady=8, bd=8, fg="black", font=('Arial', 14, 'bold'), width=10, text="Exit", bg="#ffcccc", command=fExit).pack(side="bottom", pady=15)

threading.Thread(target=nfc_loop, daemon=True).start()
threading.Thread(target=sync_every_5_mins, daemon=True).start()
root.mainloop()