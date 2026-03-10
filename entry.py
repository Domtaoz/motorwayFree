import tkinter as tk
import threading
import time
import ftp_manager
import traceback

from smartcard.System import readers
from smartcard.util import toHexString

is_reading = False
need_sync = False

db_lock = threading.Lock()

nfc_cooldowns = {}
COOLDOWN_SECONDS = 5 

def sync_every_5_mins():
    global need_sync
    while True:
        time.sleep(15)
        if need_sync:
            try:
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

BG_COLOR = "#F4F7F4"
CARD_BG = "#FFFFFF"
TEXT_MAIN = "#2C3E2D"
TEXT_SUB = "#6B7A6F"
ACCENT = "#52796F"
SUCCESS = "#40916C"
ERROR = "#D96C6C"
WARNING = "#F2B872"

FONT_FAMILY = "Segoe UI"

class EntryApp:
    def __init__(self, parent, root_ref):
        self.parent = parent
        self.root = root_ref
        self.is_reading = False
        self.station_var = tk.StringVar(value="")
        self.station_buttons = {}
        self.setup_ui()

    def setup_ui(self):
        self.header_frame = tk.Frame(self.parent, bg=BG_COLOR)
        self.header_frame.pack(fill="x", padx=25, pady=(20, 10))

        tk.Label(self.header_frame, text="ENTRY STATION", font=(FONT_FAMILY, 12, "bold"), fg=ACCENT, bg=BG_COLOR).pack(anchor="w")
        tk.Label(self.header_frame, text="Entry System", font=(FONT_FAMILY, 26, "bold"), fg=TEXT_MAIN, bg=BG_COLOR).pack(anchor="w")

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
        self.card1.pack(fill="x", pady=(5, 10))

        tk.Label(self.card1, text="Select Entry Station", font=(FONT_FAMILY, 14, "bold"), fg=TEXT_MAIN, bg=CARD_BG).pack(anchor="w", pady=(0, 10))

        self.stations_frame = tk.Frame(self.card1, bg=CARD_BG)
        self.stations_frame.pack(fill="x")

        for val in ["Station 1", "Station 2", "Station 3", "Station 4"]:
            btn = tk.Button(self.stations_frame, text=val, font=(FONT_FAMILY, 12, "bold"), 
                           bg=CARD_BG, fg=TEXT_MAIN, activebackground=BG_COLOR, activeforeground=ACCENT,
                           cursor="hand2", highlightthickness=0, bd=0, relief="flat")
            btn.config(command=lambda v=val, b=btn: self.select_station(v, b))
            btn.pack(side="left", expand=True, fill="x", padx=4, ipady=5)
            self.station_buttons[val] = btn

        self.card2 = tk.Frame(self.content_frame, bg=CARD_BG, padx=20, pady=15)
        self.card2.pack(fill="x", pady=5)

        tk.Label(self.card2, text="Scanner Controls", font=(FONT_FAMILY, 14, "bold"), fg=TEXT_MAIN, bg=CARD_BG).pack(anchor="w", pady=(0, 10))

        self.ctrl_frame = tk.Frame(self.card2, bg=CARD_BG)
        self.ctrl_frame.pack(fill="x")

        tk.Button(self.ctrl_frame, text="START NFC", bg=SUCCESS, fg="#FFFFFF", font=(FONT_FAMILY, 12, "bold"), 
                  command=self.btn_start, relief="flat", cursor="hand2", activebackground="#059669", activeforeground="white", bd=0
                  ).pack(side="left", expand=True, fill="x", padx=(0, 5), ipady=8)

        tk.Button(self.ctrl_frame, text="STOP", bg=ERROR, fg="#FFFFFF", font=(FONT_FAMILY, 12, "bold"), 
                  command=self.btn_stop, relief="flat", cursor="hand2", activebackground="#DC2626", activeforeground="white", bd=0
                  ).pack(side="right", expand=True, fill="x", padx=(5, 0), ipady=8)

        self.lbl_nfc_status = tk.Label(self.card2, text="Scanner stopped", font=(FONT_FAMILY, 11), bg=CARD_BG, fg=TEXT_SUB)
        self.lbl_nfc_status.pack(pady=(10, 5))

        self.card3 = tk.Frame(self.content_frame, bg=CARD_BG, padx=20, pady=15)
        self.card3.pack(fill="both", expand=True, pady=(5, 5))

        self.lbl_card = tk.Label(self.card3, text="Tap card to read...", font=(FONT_FAMILY, 12), bg=CARD_BG, fg=TEXT_SUB)
        self.lbl_card.pack(pady=(5, 5))

        self.lbl_status = tk.Label(self.card3, text="-", font=(FONT_FAMILY, 16, "bold"), bg=CARD_BG, fg=TEXT_MAIN, wraplength=380, justify="center")
        self.lbl_status.pack(pady=10, expand=True)

        self.lbl_log = tk.Label(self.card3, text="Log (Thread C): Waiting for action", font=(FONT_FAMILY, 10), bg=CARD_BG, fg=TEXT_SUB, wraplength=400, justify="center")
        self.lbl_log.pack(side="bottom", pady=(5, 0))

    def select_station(self, val, btn_ref):
        if self.station_var.get() == val:
            self.station_var.set("")
        else:
            self.station_var.set(val)
        
        for b_val, b_widget in self.station_buttons.items():
            if self.station_var.get() == b_val:
                b_widget.config(bg=ACCENT, fg="#FFFFFF")
            else:
                b_widget.config(bg=CARD_BG, fg=TEXT_MAIN)

    def btn_start(self):
        self.is_reading = True
        self.lbl_nfc_status.config(text="[Status] Scanning card...", fg=ACCENT)

    def btn_stop(self):
        self.is_reading = False
        self.lbl_nfc_status.config(text="[Status] Scanner stopped", fg=TEXT_SUB)

    def toggle_station_ui(self, state):
        for btn in self.station_buttons.values():
            btn.config(state=state)

    def handle_nfc_uid(self, uid):
        if not self.is_reading: return
        self.check_toll_logic(uid)

    def check_toll_logic(self, uid):
        selected_station = self.station_var.get()
        current_time = time.time()
        
        if not selected_station:
            self.lbl_status.config(text="[Warning] Please select a station before scanning", fg=WARNING)
            self.lbl_log.config(text="Log (Thread C): Waiting for action", fg=TEXT_SUB)
            return

        if uid in nfc_cooldowns:
            if current_time - nfc_cooldowns[uid] < COOLDOWN_SECONDS:
                self.lbl_status.config(text="[Warning] Tapped too fast. Please wait a moment.", fg=WARNING)
                return
        
        nfc_cooldowns[uid] = current_time
        self.toggle_station_ui(tk.DISABLED)
        self.lbl_log.config(text="Log (Thread C): [Info] Processing new card...", fg=ACCENT)
        
        try:
            with db_lock:
                db = ftp_manager.load_local_db()
        except Exception as e:
            self.lbl_status.config(text="[Error] Unable to load database", fg=ERROR)
            self.toggle_station_ui(tk.NORMAL)
            return

        self.lbl_card.config(text=f"Card ID: {uid}")
        
        if uid not in db:
            self.lbl_status.config(text="Card not registered", fg=ERROR)
            self.toggle_station_ui(tk.NORMAL)
            return

        balance = db.get(uid, {}).get('balance', 0)
        
        if db[uid].get('entry_station'):
             self.lbl_status.config(text=f"Already entered at {db[uid]['entry_station']}. Please exit first.", fg=ERROR)
             self.toggle_station_ui(tk.NORMAL)
             return

        if balance < 200:
            self.lbl_status.config(text=f"Insufficient balance! ({balance} THB) Gate locked", fg=ERROR)
            self.toggle_station_ui(tk.NORMAL)
        else:
            self.lbl_status.config(text=f"Balance: {balance} THB >> Gate opened: {selected_station}", fg=SUCCESS)
            threading.Thread(target=self.process_c_sync, args=(uid, selected_station), daemon=True).start()

    def process_c_sync(self, uid, station):
        global need_sync
        try:
            with db_lock:
                db = ftp_manager.load_local_db()
                if uid in db:
                    db[uid]['entry_station'] = station
                    if 'transactions' not in db[uid]: 
                        db[uid]['transactions'] = []
                    db[uid]['transactions'].append(f"[{time.strftime('%H:%M:%S')}] Entered: {station}")
                    
                    ftp_manager.save_local_db(db)
                    need_sync = True 
                    
            self.root.after(0, lambda: self.lbl_log.config(text=f"Log (Thread C): [Success] Entry recorded ({station}), waiting for FTP sync", fg=SUCCESS))
        except Exception as e:
            print(f"Error in process_c_sync: {e}")
            self.root.after(0, lambda: self.lbl_log.config(text=f"Log (Thread C): [Error] Failed to record entry", fg=ERROR))
        finally:
            self.root.after(0, self.toggle_station_ui, tk.NORMAL)

def sync_every_5_mins():
    global need_sync
    while True:
        time.sleep(15)
        if need_sync:
            try:
                with db_lock:
                    ftp_manager.upload_db()
                need_sync = False 
                print(f"[{time.strftime('%H:%M:%S')}] FTP Sync Successful.")
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] FTP Sync Error: {e}")

def nfc_loop(callback_obj):
    try:
        available_readers = readers()
        if not available_readers: 
            print("No NFC readers found.")
            return
            
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
                        time.sleep(1)
            except Exception:
                if last_uid != "": last_uid = ""
            time.sleep(0.2)
    except Exception as e: 
        print(f"NFC Error: {e}")

if __name__ == "__main__":
    def fExit():
        root.destroy()

    root = tk.Tk()
    root.geometry("500x700")
    root.title("NFC Tollway - Entry System")
    root.configure(bg=BG_COLOR)
    root.resizable(False, False)

    bottom_pill = tk.Frame(root, bg=BG_COLOR)
    bottom_pill.pack(side="bottom", fill="x", pady=10)

    tk.Button(bottom_pill, text="EXIT", font=(FONT_FAMILY, 11, "bold"), command=fExit, 
              bg="#E8ECE8", fg=TEXT_SUB, relief="flat", bd=0, cursor="hand2", 
              activebackground=ERROR, activeforeground="#FFFFFF", width=35, pady=8
              ).pack()

    main_frame = tk.Frame(root, bg=BG_COLOR)
    main_frame.pack(fill="both", expand=True)
    
    app = EntryApp(main_frame, root)
    
    threading.Thread(target=nfc_loop, args=(app,), daemon=True).start()
    threading.Thread(target=sync_every_5_mins, daemon=True).start()
    root.mainloop()