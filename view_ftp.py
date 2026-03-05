import json
import io
from ftplib import FTP

FTP_HOST = '158.108.98.128' 
FTP_USER = 'st03603423'  
FTP_PASS = 'st03603423'      
DB_FILE = 'motorwayFree/database.json'

print("--- 🚀 เริ่มรันโปรแกรมดึงข้อมูล ---")
print(f"📡 กำลังพยายามเชื่อมต่อ FTP ไปที่ {FTP_HOST} ... (อาจใช้เวลา 5-10 วินาที)")

try:
    ftp = FTP(FTP_HOST)
    ftp.connect(timeout=10)
    ftp.login(user=FTP_USER, passwd=FTP_PASS)
    print("✅ เชื่อมต่อเซิร์ฟเวอร์สำเร็จ! กำลังค้นหาไฟล์...")
    
    mem_file = io.BytesIO()
    ftp.retrbinary(f'RETR {DB_FILE}', mem_file.write)
    ftp.quit()
    
    print("✅ ดาวน์โหลดข้อมูลสำเร็จ! กำลังเปิดอ่าน...\n")
    
    mem_file.seek(0)
    file_content = mem_file.read().decode('utf-8')
    data = json.loads(file_content)
    
    print("="*60)
    print(f" 📂 ข้อมูลล่าสุดบน FTP (โฟลเดอร์: {DB_FILE}) ")
    print("="*60)
    
    formatted_json = json.dumps(data, indent=4, ensure_ascii=False)
    print(formatted_json)
    
    print("="*60 + "\n")
    
except Exception as e:
    print(f"\n❌ เกิดข้อผิดพลาด: {e}\n")
    print("💡 คำแนะนำ: ")
    print("1. เช็คว่าต่อ VPN มหาลัยแล้วหรือยัง (ถ้าไม่ต่อ โค้ดจะค้างตรงคำว่า 'กำลังพยายามเชื่อมต่อ...' ประมาณ 10 วินาทีแล้วขึ้น Error)")
    print("2. เช็คว่าโฟลเดอร์ motorwayFree และไฟล์ database.json มีอยู่จริงบนเซิร์ฟเวอร์")