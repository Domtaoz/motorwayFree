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
APP_PASSWORD = "spok yxyq gjtr iitc"

current_uid = ""
generated_otp = ""
registering_uid = "" 
is_reading = False

need_sync = False 

def sync_every_5_mins():
    global need_sync
    while True:
        time.sleep(30) 
        if need_sync:
            try:
                ftp_manager.upload_db()
                need_sync = False
            except Exception: pass

def nfc_loop(callback_obj):
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

BG_COLOR = "#F4F7F4"
CARD_BG = "#FFFFFF"
TEXT_MAIN = "#2C3E2D"
TEXT_SUB = "#6B7A6F"
ACCENT = "#52796F"
SUCCESS = "#40916C"
ERROR = "#D96C6C"
WARNING = "#F2B872"

FONT_FAMILY = "Segoe UI"

class SevenElevenApp:
    def __init__(self, parent, root_ref):
        self.parent = parent
        self.root = root_ref
        self.is_reading = False
        self.current_uid = ""
        self.generated_otp = ""
        self.registering_uid = ""
        self.setup_ui()

    def setup_ui(self):
        self.header_frame = tk.Frame(self.parent, bg=BG_COLOR)
        self.header_frame.pack(fill="x", padx=25, pady=(20, 10))

        tk.Label(self.header_frame, text="MOTORWAY", font=(FONT_FAMILY, 12, "bold"), fg=ACCENT, bg=BG_COLOR).pack(anchor="w")
        tk.Label(self.header_frame, text="Top-up System", font=(FONT_FAMILY, 26, "bold"), fg=TEXT_MAIN, bg=BG_COLOR).pack(anchor="w")

        self.container_frame = tk.Frame(self.parent, bg=BG_COLOR)
        self.container_frame.pack(fill="both", expand=True, padx=20)

        self.canvas = tk.Canvas(self.container_frame, bg=BG_COLOR, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.container_frame, orient="vertical", command=self.canvas.yview)

        self.content_frame = tk.Frame(self.canvas, bg=BG_COLOR)

        self.content_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        def _on_canvas_configure(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)
        self.canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.card1 = tk.Frame(self.content_frame, bg=CARD_BG, padx=20, pady=15)
        self.card1.pack(fill="x", pady=(5, 5))

        tk.Label(self.card1, text="Scanner Controls", font=(FONT_FAMILY, 14, "bold"), fg=TEXT_MAIN, bg=CARD_BG).pack(anchor="w", pady=(0, 10))

        self.ctrl_frame = tk.Frame(self.card1, bg=CARD_BG)
        self.ctrl_frame.pack(fill="x")

        tk.Button(self.ctrl_frame, text="START NFC", bg=SUCCESS, fg="#FFFFFF", font=(FONT_FAMILY, 12, "bold"), 
                  command=self.btn_start, relief="flat", cursor="hand2", activebackground="#059669", activeforeground="white", bd=0
                  ).pack(side="left", expand=True, fill="x", padx=(0, 5), ipady=8)

        tk.Button(self.ctrl_frame, text="STOP", bg=ERROR, fg="#FFFFFF", font=(FONT_FAMILY, 12, "bold"), 
                  command=self.btn_stop, relief="flat", cursor="hand2", activebackground="#DC2626", activeforeground="white", bd=0
                  ).pack(side="right", expand=True, fill="x", padx=(5, 0), ipady=8)

        self.lbl_nfc_status = tk.Label(self.card1, text="🔴 สถานะ: หยุดสแกน", font=(FONT_FAMILY, 11), bg=CARD_BG, fg=TEXT_SUB)
        self.lbl_nfc_status.pack(pady=(10, 5))

        self.lbl_card = tk.Label(self.card1, text="Card ID: -", font=(FONT_FAMILY, 12), bg=CARD_BG, fg=TEXT_SUB)
        self.lbl_card.pack(pady=(5, 0))

        self.card2 = tk.Frame(self.content_frame, bg=CARD_BG, padx=20, pady=15)
        self.card2.pack(fill="x", pady=5)

        self.lbl_status = tk.Label(self.card2, text="-", font=(FONT_FAMILY, 14, "bold"), bg=CARD_BG, fg=TEXT_MAIN, wraplength=380, justify="center")
        self.lbl_status.pack(pady=5, expand=True)

        self.lbl_msg = tk.Label(self.card2, text="", font=(FONT_FAMILY, 11), bg=CARD_BG, fg=TEXT_SUB, wraplength=400, justify="center")
        self.lbl_msg.pack(pady=(5, 0))

        self.card3 = tk.Frame(self.content_frame, bg=CARD_BG, padx=20, pady=15)
        self.card3.pack(fill="x", pady=5)

        tk.Label(self.card3, text="New User Registration", font=(FONT_FAMILY, 14, "bold"), fg=TEXT_MAIN, bg=CARD_BG).pack(anchor="w", pady=(0, 10))

        tk.Label(self.card3, text="Email Address", font=(FONT_FAMILY, 11), bg=CARD_BG, fg=TEXT_SUB).pack(anchor="w")
        self.em_frame = tk.Frame(self.card3, bg=CARD_BG)
        self.em_frame.pack(fill="x", pady=(5, 10))
        self.entry_email = tk.Entry(self.em_frame, state="disabled", font=(FONT_FAMILY, 11), bg="#F4F7F4", fg=TEXT_MAIN, relief="flat", highlightthickness=1, highlightbackground="#D1D5DB")
        self.entry_email.pack(side="left", fill="both", expand=True, padx=(0, 5), ipady=5)
        self.btn_send_otp = tk.Button(self.em_frame, text="Get OTP", state="disabled", command=self.handle_send_otp, font=(FONT_FAMILY, 10, "bold"), bg=ACCENT, fg="white", disabledforeground="white", relief="flat", cursor="hand2", bd=0)
        self.btn_send_otp.pack(side="right", ipady=5, ipadx=5)

        tk.Label(self.card3, text="OTP Code", font=(FONT_FAMILY, 11), bg=CARD_BG, fg=TEXT_SUB).pack(anchor="w")
        self.otp_frame = tk.Frame(self.card3, bg=CARD_BG)
        self.otp_frame.pack(fill="x", pady=(5, 5))
        self.entry_otp = tk.Entry(self.otp_frame, state="disabled", font=(FONT_FAMILY, 11), bg="#F4F7F4", fg=TEXT_MAIN, relief="flat", highlightthickness=1, highlightbackground="#D1D5DB")
        self.entry_otp.pack(side="left", fill="both", expand=True, padx=(0, 5), ipady=5)
        self.btn_verify_otp = tk.Button(self.otp_frame, text="Verify", state="disabled", command=self.handle_verify_otp, font=(FONT_FAMILY, 10, "bold"), bg=SUCCESS, fg="white", disabledforeground="white", relief="flat", cursor="hand2", bd=0)
        self.btn_verify_otp.pack(side="right", ipady=5, ipadx=5)

        self.card4 = tk.Frame(self.content_frame, bg=CARD_BG, padx=20, pady=15)
        self.card4.pack(fill="x", pady=(5, 10))

        tk.Label(self.card4, text="Top-up Account", font=(FONT_FAMILY, 14, "bold"), fg=TEXT_MAIN, bg=CARD_BG).pack(anchor="w", pady=(0, 10))

        tk.Label(self.card4, text="Top-up Amount (THB)", font=(FONT_FAMILY, 11), bg=CARD_BG, fg=TEXT_SUB).pack(anchor="w")
        self.topup_frame = tk.Frame(self.card4, bg=CARD_BG)
        self.topup_frame.pack(fill="x", pady=(5, 5))
        self.entry_topup = tk.Entry(self.topup_frame, state="disabled", font=(FONT_FAMILY, 11), bg="#F4F7F4", fg=TEXT_MAIN, relief="flat", highlightthickness=1, highlightbackground="#D1D5DB")
        self.entry_topup.pack(side="left", fill="both", expand=True, padx=(0, 5), ipady=5)
        self.btn_topup = tk.Button(self.topup_frame, text="Top-up", state="disabled", command=self.handle_topup, font=(FONT_FAMILY, 10, "bold"), bg=SUCCESS, fg="white", disabledforeground="white", relief="flat", cursor="hand2", bd=0)
        self.btn_topup.pack(side="right", ipady=5, ipadx=5)

    def btn_start(self):
        self.is_reading = True
        self.lbl_nfc_status.config(text="🟢 Status : Scanning", fg=ACCENT)

    def btn_stop(self):
        self.is_reading = False
        self.lbl_nfc_status.config(text="🔴 Status : Stop", fg=TEXT_SUB)

    def handle_nfc_uid(self, uid):
        if not self.is_reading: return
        self.check_card_logic(uid)

    def check_card_logic(self, uid):
        if uid != self.current_uid:
            self.entry_email.config(state="normal")
            self.entry_email.delete(0, 'end')
            self.entry_otp.config(state="normal")
            self.entry_otp.delete(0, 'end')
            self.entry_topup.config(state="normal")
            self.entry_topup.delete(0, 'end')

        self.current_uid = uid
        self.lbl_msg.config(text="⚡ Retrieving card information...", fg="blue") 
        db = ftp_manager.load_local_db()
        self.lbl_card.config(text=f"Card ID: {uid}")
        
        if uid not in db:
            self.lbl_status.config(text="New card! Please enter your email to register.", fg="blue")
            self.lbl_msg.config(text="") 
            self.entry_email.config(state="normal")
            self.btn_send_otp.config(state="normal", text="รับ OTP")
            if uid == self.registering_uid:
                self.entry_otp.config(state="normal")
                self.btn_verify_otp.config(state="normal")
            else:
                self.entry_otp.config(state="disabled")
                self.btn_verify_otp.config(state="disabled")
            self.entry_topup.config(state="disabled")
            self.btn_topup.config(state="disabled")
        else:
            balance = db[uid].get('balance', 0)
            self.lbl_status.config(text=f"This card is already registered.\nBalance remaining. : {balance} bath", fg="green")
            self.lbl_msg.config(text="") 
            self.entry_topup.config(state="normal")
            self.btn_topup.config(state="normal")
            self.entry_email.config(state="disabled")
            self.btn_send_otp.config(state="disabled")
            self.entry_otp.config(state="disabled")
            self.btn_verify_otp.config(state="disabled")

    def handle_send_otp(self):
        email = self.entry_email.get()
        if email:
            self.lbl_msg.config(text="⏳ Sending OTP to email...", fg="orange")
            self.btn_send_otp.config(state="disabled") 
            self.generated_otp = str(random.randint(100000, 999999))
            threading.Thread(target=self.process_send_otp_thread, args=(email, self.generated_otp, self.current_uid), daemon=True).start()
        else:
            self.lbl_msg.config(text="⚠️ Please enter your email first", fg="red")

    def process_send_otp_thread(self, email, otp, target_uid):
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
            self.root.after(0, lambda: self.on_otp_sent_success(target_uid))
        except Exception as e:
            self.root.after(0, lambda: self.on_otp_sent_fail())

    def on_otp_sent_success(self, target_uid):
        self.registering_uid = target_uid 
        self.lbl_msg.config(text="✅ OTP sent to your email!", fg="green")
        if self.current_uid == self.registering_uid:
            self.entry_otp.config(state="normal")
            self.btn_verify_otp.config(state="normal")
        self.btn_send_otp.config(state="normal", text="Send Again")

    def on_otp_sent_fail(self):
        self.lbl_msg.config(text="❌ Failed to send email. Check internet connection or password.", fg="red")
        self.btn_send_otp.config(state="normal", text="Try Again")

    def handle_verify_otp(self):
        global need_sync
        if self.current_uid != self.registering_uid:
            self.lbl_msg.config(text="❌ Card does not match! Please tap the card that requested the OTP.", fg="red")
            return
        if self.entry_otp.get() == self.generated_otp:
            db = ftp_manager.load_local_db()
            db[self.current_uid] = {
                "email": self.entry_email.get(), 
                "balance": 0, 
                "entry_station": "",
                "transactions": [f"[{time.strftime('%H:%M:%S')}] Register."]
            }
            ftp_manager.save_local_db(db)
            need_sync = True 
            self.lbl_msg.config(text="Registration successful! You can top up your balance now.", fg="green")
            self.registering_uid = "" 
            self.entry_topup.config(state="normal")
            self.btn_topup.config(state="normal")
            self.entry_email.config(state="disabled")
            self.btn_send_otp.config(state="disabled")
            self.entry_otp.config(state="disabled")
            self.btn_verify_otp.config(state="disabled")
        else:
            self.lbl_msg.config(text="❌ OTP is incorrect", fg="red")

    def handle_topup(self):
        global need_sync
        try:
            amount = float(self.entry_topup.get())
            db = ftp_manager.load_local_db()
            db[self.current_uid]['balance'] += amount
            db[self.current_uid]['transactions'].append(f"[{time.strftime('%H:%M:%S')}] Top up +{amount} บาท")
            ftp_manager.save_local_db(db)
            need_sync = True 
            self.lbl_msg.config(text=f"Top-up successful! (+{amount} bath) Waiting to upload to FTP in the next cycle.", fg="green")
            self.lbl_status.config(text=f"This card is already registered.\nBalance remaining: {db[self.current_uid]['balance']} bath", fg="green")
            self.entry_topup.delete(0, 'end')
        except:
            self.lbl_msg.config(text="⚠️ Please enter a valid number", fg="red")

def sync_every_5_mins():
    global need_sync
    while True:
        time.sleep(15) 
        if need_sync:
            try:
                ftp_manager.upload_db()
                need_sync = False 
            except Exception: pass

def nfc_loop(callback_obj):
    try:
        available_readers = readers()
        if not available_readers: return
        reader = available_readers[0]
        GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        last_uid = ""
        while True:
            if hasattr(callback_obj, 'is_reading') and not callback_obj.is_reading:
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
                        if hasattr(callback_obj, 'handle_nfc_uid'):
                            callback_obj.root.after(10, callback_obj.handle_nfc_uid, uid)
                        last_uid = uid
                        time.sleep(2)
            except Exception:
                if last_uid != "": last_uid = ""
            time.sleep(0.5)
    except Exception as e: print(f"NFC Error: {e}")

if __name__ == "__main__":
    def fExit():
        root.destroy()

    root = tk.Tk()
    root.geometry("500x700")
    root.title("Motorway - Registration & Top-up")
    root.configure(bg=BG_COLOR)
    root.resizable(False, False)

    # Bottom Exit Pill Base
    bottom_pill = tk.Frame(root, bg=BG_COLOR)
    bottom_pill.pack(side="bottom", fill="x", pady=10)

    tk.Button(bottom_pill, text="EXIT", font=(FONT_FAMILY, 11, "bold"), command=fExit, 
              bg="#E8ECE8", fg=TEXT_SUB, relief="flat", bd=0, cursor="hand2", 
              activebackground=ERROR, activeforeground="#FFFFFF", width=35, pady=8
              ).pack()

    main_frame = tk.Frame(root, bg=BG_COLOR)
    main_frame.pack(fill="both", expand=True)

    app = SevenElevenApp(main_frame, root)

    threading.Thread(target=nfc_loop, args=(app,), daemon=True).start()
    threading.Thread(target=sync_every_5_mins, daemon=True).start()
    root.mainloop()
