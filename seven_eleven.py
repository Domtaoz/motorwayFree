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
    # ---------------------------------------------------

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

# --- Minimalist Green Theme UI ---
# Colors (Matcha/Sage Minimalist Mode)
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
    lbl_nfc_status.config(text="🟢 สถานะ: กำลังสแกนบัตร...", fg=ACCENT)

def btn_stop():
    global is_reading
    is_reading = False
    lbl_nfc_status.config(text="🔴 สถานะ: หยุดสแกน", fg=TEXT_SUB)

def fExit():
    root.destroy()

root = tk.Tk()
root.geometry("500x700")
root.title("Motorway - Registration & Top-up")
root.configure(bg=BG_COLOR)
root.resizable(False, False)

# --- Header Section ---
header_frame = tk.Frame(root, bg=BG_COLOR)
header_frame.pack(fill="x", padx=25, pady=(20, 10))

tk.Label(header_frame, text="MOTORWAY", font=(FONT_FAMILY, 12, "bold"), fg=ACCENT, bg=BG_COLOR).pack(anchor="w")
tk.Label(header_frame, text="Top-up System", font=(FONT_FAMILY, 26, "bold"), fg=TEXT_MAIN, bg=BG_COLOR).pack(anchor="w")

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

# 1. Scanner Controls Card
card1 = tk.Frame(content_frame, bg=CARD_BG, padx=20, pady=15)
card1.pack(fill="x", pady=(5, 5))

tk.Label(card1, text="Scanner Controls", font=(FONT_FAMILY, 14, "bold"), fg=TEXT_MAIN, bg=CARD_BG).pack(anchor="w", pady=(0, 10))

ctrl_frame = tk.Frame(card1, bg=CARD_BG)
ctrl_frame.pack(fill="x")

tk.Button(ctrl_frame, text="START NFC", bg=SUCCESS, fg="#FFFFFF", font=(FONT_FAMILY, 12, "bold"), 
          command=btn_start, relief="flat", cursor="hand2", activebackground="#059669", activeforeground="white", bd=0
          ).pack(side="left", expand=True, fill="x", padx=(0, 5), ipady=8)

tk.Button(ctrl_frame, text="STOP", bg=ERROR, fg="#FFFFFF", font=(FONT_FAMILY, 12, "bold"), 
          command=btn_stop, relief="flat", cursor="hand2", activebackground="#DC2626", activeforeground="white", bd=0
          ).pack(side="right", expand=True, fill="x", padx=(5, 0), ipady=8)

lbl_nfc_status = tk.Label(card1, text="🔴 สถานะ: หยุดสแกน", font=(FONT_FAMILY, 11), bg=CARD_BG, fg=TEXT_SUB)
lbl_nfc_status.pack(pady=(10, 5))

lbl_card = tk.Label(card1, text="Card ID: -", font=(FONT_FAMILY, 12), bg=CARD_BG, fg=TEXT_SUB)
lbl_card.pack(pady=(5, 0))

# 2. Status Card
card2 = tk.Frame(content_frame, bg=CARD_BG, padx=20, pady=15)
card2.pack(fill="x", pady=5)

lbl_status = tk.Label(card2, text="-", font=(FONT_FAMILY, 14, "bold"), bg=CARD_BG, fg=TEXT_MAIN, wraplength=380, justify="center")
lbl_status.pack(pady=5, expand=True)

lbl_msg = tk.Label(card2, text="", font=(FONT_FAMILY, 11), bg=CARD_BG, fg=TEXT_SUB, wraplength=400, justify="center")
lbl_msg.pack(pady=(5, 0))

# 3. Registration Card
card3 = tk.Frame(content_frame, bg=CARD_BG, padx=20, pady=15)
card3.pack(fill="x", pady=5)

tk.Label(card3, text="New User Registration", font=(FONT_FAMILY, 14, "bold"), fg=TEXT_MAIN, bg=CARD_BG).pack(anchor="w", pady=(0, 10))

# Email Block
tk.Label(card3, text="Email Address", font=(FONT_FAMILY, 11), bg=CARD_BG, fg=TEXT_SUB).pack(anchor="w")
em_frame = tk.Frame(card3, bg=CARD_BG)
em_frame.pack(fill="x", pady=(5, 10))
entry_email = tk.Entry(em_frame, state="disabled", font=(FONT_FAMILY, 11), bg="#F4F7F4", fg=TEXT_MAIN, relief="flat", highlightthickness=1, highlightbackground="#D1D5DB")
entry_email.pack(side="left", fill="both", expand=True, padx=(0, 5), ipady=5)
btn_send_otp = tk.Button(em_frame, text="Get OTP", state="disabled", command=handle_send_otp, font=(FONT_FAMILY, 10, "bold"), bg=ACCENT, fg="white", relief="flat", cursor="hand2", bd=0)
btn_send_otp.pack(side="right", ipady=5, ipadx=5)

# OTP Block
tk.Label(card3, text="OTP Code", font=(FONT_FAMILY, 11), bg=CARD_BG, fg=TEXT_SUB).pack(anchor="w")
otp_frame = tk.Frame(card3, bg=CARD_BG)
otp_frame.pack(fill="x", pady=(5, 5))
entry_otp = tk.Entry(otp_frame, state="disabled", font=(FONT_FAMILY, 11), bg="#F4F7F4", fg=TEXT_MAIN, relief="flat", highlightthickness=1, highlightbackground="#D1D5DB")
entry_otp.pack(side="left", fill="both", expand=True, padx=(0, 5), ipady=5)
btn_verify_otp = tk.Button(otp_frame, text="Verify", state="disabled", command=handle_verify_otp, font=(FONT_FAMILY, 10, "bold"), bg=SUCCESS, fg="white", relief="flat", cursor="hand2", bd=0)
btn_verify_otp.pack(side="right", ipady=5, ipadx=5)

# 4. Top-up Card
card4 = tk.Frame(content_frame, bg=CARD_BG, padx=20, pady=15)
card4.pack(fill="x", pady=(5, 10))

tk.Label(card4, text="Top-up Account", font=(FONT_FAMILY, 14, "bold"), fg=TEXT_MAIN, bg=CARD_BG).pack(anchor="w", pady=(0, 10))

tk.Label(card4, text="Top-up Amount (THB)", font=(FONT_FAMILY, 11), bg=CARD_BG, fg=TEXT_SUB).pack(anchor="w")
topup_frame = tk.Frame(card4, bg=CARD_BG)
topup_frame.pack(fill="x", pady=(5, 5))
entry_topup = tk.Entry(topup_frame, state="disabled", font=(FONT_FAMILY, 11), bg="#F4F7F4", fg=TEXT_MAIN, relief="flat", highlightthickness=1, highlightbackground="#D1D5DB")
entry_topup.pack(side="left", fill="both", expand=True, padx=(0, 5), ipady=5)
btn_topup = tk.Button(topup_frame, text="Top-up", state="disabled", command=handle_topup, font=(FONT_FAMILY, 10, "bold"), bg=SUCCESS, fg="white", relief="flat", cursor="hand2", bd=0)
btn_topup.pack(side="right", ipady=5, ipadx=5)

threading.Thread(target=nfc_loop, daemon=True).start()
threading.Thread(target=sync_every_5_mins, daemon=True).start()
root.mainloop()