import json
import os
from ftplib import FTP

FTP_HOST = '158.108.97.1287' 
FTP_USER = 'st036034230'  
FTP_PASS = 'st03603423'      

# 1. กำหนดชื่อโฟลเดอร์ที่ต้องการเก็บข้อมูล (แก้ชื่อโฟลเดอร์ตรงนี้ได้เลย)
DATA_FOLDER = 'motorwayFree'

# 2. รวมชื่อโฟลเดอร์เข้ากับชื่อไฟล์
DB_FILE = os.path.join(DATA_FOLDER, 'database.json')

# 3. เช็คว่ามีโฟลเดอร์นี้หรือยัง ถ้ายังไม่มีให้สร้างขึ้นมาอัตโนมัติ
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

def download_db():
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        with open(DB_FILE, 'wb') as localfile:
            # ดึงไฟล์จาก FTP มาเก็บในโฟลเดอร์
            ftp.retrbinary('RETR database.json', localfile.write, 1024)
        ftp.quit()
    except Exception as e:
        print(f"FTP Download Error (ใช้ Local DB แทน): {e}")

def upload_db():
    try:
        ftp = FTP(FTP_HOST)
        ftp.connect(timeout=5) 
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        with open(DB_FILE, 'rb') as localfile:
            # ส่งไฟล์ขึ้น FTP (บน FTP จะไม่มีโฟลเดอร์ nfc_data เพื่อไม่ให้อาจารย์สับสน)
            ftp.storbinary('STOR database.json', localfile)
        ftp.quit()
        return True 
    except Exception as e:
        print(f"📡 FTP Sync ปล่อยเบลอไปก่อน: {e}") 
        return False 

def load_local_db():
    try:
        # โหลดไฟล์จากในโฟลเดอร์ nfc_data
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_local_db(data):
    # เซฟไฟล์ลงไปในโฟลเดอร์ nfc_data
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)