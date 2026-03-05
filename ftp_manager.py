import json
import os
from ftplib import FTP

FTP_HOST = '158.108.98.128' 
FTP_USER = 'st03603423'  
FTP_PASS = 'st03603423'      

LOCAL_DB_FILE = 'database.json' 
REMOTE_FOLDER = 'motorwayFree' # ระบุชื่อโฟลเดอร์ตรงนี้

def download_db():
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        ftp.cwd(REMOTE_FOLDER) # สั่งให้เดินเข้าไปในโฟลเดอร์ก่อน
        with open(LOCAL_DB_FILE, 'wb') as localfile:
            ftp.retrbinary('RETR database.json', localfile.write, 1024)
        ftp.quit()
    except Exception as e:
        print(f"FTP Download Error (ใช้ Local DB แทน): {e}")

def upload_db():
    try:
        ftp = FTP(FTP_HOST)
        ftp.connect(timeout=10)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        
        ftp.cwd(REMOTE_FOLDER) # สั่งให้เดินเข้าไปในโฟลเดอร์ก่อน
        
        with open(LOCAL_DB_FILE, 'rb') as localfile:
            ftp.storbinary('STOR database.json', localfile) # วางไฟล์ด้วยชื่อเพียวๆ
        ftp.quit()
        print("✅ FTP Sync: อัปโหลดไฟล์ขึ้นเซิร์ฟเวอร์สำเร็จ!") # แจ้งเตือนเมื่อส่งผ่าน
        return True
    except Exception as e:
        print(f"❌ FTP Sync Error: {e}")
        return False

def load_local_db():
    try:
        with open(LOCAL_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_local_db(data):
    with open(LOCAL_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)