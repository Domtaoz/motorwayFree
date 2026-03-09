import tkinter as tk
import threading
import time
from smartcard.System import readers
from smartcard.util import toHexString

# Import the refactored apps
import entry
import exit
import seven_eleven
from entry import EntryApp
from exit import ExitApp
from seven_eleven import SevenElevenApp
import ftp_manager

# Colors (Consistent with the apps)
BG_COLOR = "#F4F7F4"
CARD_BG = "#FFFFFF"
TEXT_MAIN = "#2C3E2D"
TEXT_SUB = "#6B7A6F"
ACCENT = "#52796F"
SUCCESS = "#40916C"
ERROR = "#D96C6C"
WARNING = "#F2B872"
FONT_FAMILY = "Segoe UI"

class MainApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("NFC Tollway System - Multi-Platform")
        self.root.geometry("500x800")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)

        self.current_app = None
        self.active_app_instance = None

        self.setup_navigation()
        self.main_container = tk.Frame(self.root, bg=BG_COLOR)
        self.main_container.pack(fill="both", expand=True)

        # Bottom Exit Pill
        bottom_pill = tk.Frame(self.root, bg=BG_COLOR)
        bottom_pill.pack(side="bottom", fill="x", pady=10)

        tk.Button(bottom_pill, text="EXIT SYSTEM", font=(FONT_FAMILY, 11, "bold"), 
                  command=self.root.destroy, 
                  bg="#E8ECE8", fg=TEXT_SUB, relief="flat", bd=0, cursor="hand2", 
                  activebackground=ERROR, activeforeground="#FFFFFF", width=35, pady=8
                  ).pack()

        # Start NFC Thread
        self.nfc_thread = threading.Thread(target=self.global_nfc_loop, daemon=True)
        self.nfc_thread.start()

        # Start Sync Thread
        self.sync_thread = threading.Thread(target=self.global_sync_loop, daemon=True)
        self.sync_thread.start()

        # Default view
        self.show_entry()

    def setup_navigation(self):
        nav_frame = tk.Frame(self.root, bg=CARD_BG, pady=10)
        nav_frame.pack(fill="x")

        self.btn_entry = tk.Button(nav_frame, text="ENTRY", font=(FONT_FAMILY, 10, "bold"), 
                                  command=self.show_entry, bg=CARD_BG, fg=TEXT_MAIN, 
                                  relief="flat", cursor="hand2", width=15)
        self.btn_entry.pack(side="left", expand=True)

        self.btn_exit = tk.Button(nav_frame, text="EXIT", font=(FONT_FAMILY, 10, "bold"), 
                                 command=self.show_exit, bg=CARD_BG, fg=TEXT_MAIN, 
                                 relief="flat", cursor="hand2", width=15)
        self.btn_exit.pack(side="left", expand=True)

        self.btn_711 = tk.Button(nav_frame, text="7-ELEVEN", font=(FONT_FAMILY, 10, "bold"), 
                                command=self.show_711, bg=CARD_BG, fg=TEXT_MAIN, 
                                relief="flat", cursor="hand2", width=15)
        self.btn_711.pack(side="left", expand=True)

    def clear_container(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()
        if self.active_app_instance:
            self.active_app_instance.is_reading = False

    def update_nav_buttons(self, active_btn):
        for btn in [self.btn_entry, self.btn_exit, self.btn_711]:
            btn.config(bg=CARD_BG, fg=TEXT_MAIN)
        active_btn.config(bg=ACCENT, fg="white")

    def show_entry(self):
        self.clear_container()
        self.update_nav_buttons(self.btn_entry)
        self.active_app_instance = EntryApp(self.main_container, self.root)
        self.active_app_instance.is_reading = True

    def show_exit(self):
        self.clear_container()
        self.update_nav_buttons(self.btn_exit)
        self.active_app_instance = ExitApp(self.main_container, self.root)
        self.active_app_instance.is_reading = True

    def show_711(self):
        self.clear_container()
        self.update_nav_buttons(self.btn_711)
        self.active_app_instance = SevenElevenApp(self.main_container, self.root)
        self.active_app_instance.is_reading = True

    def global_sync_loop(self):
        while True:
            time.sleep(15)
            # Check if any app needs sync
            if entry.need_sync or exit.need_sync or seven_eleven.need_sync:
                print(f"[{time.strftime('%H:%M:%S')}] Global Sync: Syncing database...")
                try:
                    # Using entry.db_lock if it exists, or just calling upload
                    if hasattr(entry, 'db_lock'):
                        with entry.db_lock:
                            ftp_manager.upload_db()
                    else:
                        ftp_manager.upload_db()
                    
                    # Reset all sync flags
                    entry.need_sync = False
                    exit.need_sync = False
                    seven_eleven.need_sync = False
                    print(f"[{time.strftime('%H:%M:%S')}] Global Sync: Successful.")
                except Exception as e:
                    print(f"Global Sync Error: {e}")

    def global_nfc_loop(self):
        try:
            available_readers = readers()
            if not available_readers:
                print("No NFC readers found.")
                return
            
            reader = available_readers[0]
            GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            last_uid = ""
            
            while True:
                if not self.active_app_instance or not self.active_app_instance.is_reading:
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
                            # Forward to active instance
                            if self.active_app_instance and hasattr(self.active_app_instance, 'handle_nfc_uid'):
                                self.root.after(0, self.active_app_instance.handle_nfc_uid, uid)
                            last_uid = uid
                            time.sleep(1.5) # Debounce
                    else:
                        last_uid = ""
                except Exception:
                    last_uid = ""
                
                time.sleep(0.3)
        except Exception as e:
            print(f"Global NFC Error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApplication(root)
    root.mainloop()
