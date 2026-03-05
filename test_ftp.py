from ftplib import FTP
import sys

# กำหนดค่าตัวแปรอ้างอิงจากไฟล์ upload.py และ download.py ของคุณ
FTP_HOST = '158.108.98.128' 
FTP_USER = 'st03603423'
FTP_PASS = 'st03603423'

def test_ftp_connection():
    print(f"⏳ กำลังพยายามเชื่อมต่อไปยัง FTP Server: {FTP_HOST}...")
    try:
        # 1. เชื่อมต่อ FTP
        ftp = FTP(FTP_HOST)
        
        # 2. Login ด้วย User และ Password
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        print("✅ เชื่อมต่อและ Login สำเร็จ!")
        
        # 3. แสดงข้อความต้อนรับจาก Server
        print("💬 ข้อความต้อนรับ:", ftp.getwelcome())
        
        # 4. ลองแสดงรายการไฟล์และโฟลเดอร์ เพื่อยืนยันว่าอ่านข้อมูลได้จริง
        print("\n📂 --- รายการไฟล์และโฟลเดอร์ใน Server ---")
        ftp.retrlines('LIST')
        print("--------------------------------------\n")
        
        try:
            ftp.cwd('motorwayFree')
            print("✅ สามารถเข้าไปที่โฟลเดอร์ 'motorwayFree' ได้สำเร็จ")
        except Exception as e:
            print(f"⚠️ ไม่สามารถเข้าโฟลเดอร์ 'motorwayFree' ได้ (โฟลเดอร์อาจจะยังไม่ถูกสร้าง): {e}")

        # ปิดการเชื่อมต่อ
        ftp.quit()
        print("ปิดการเชื่อมต่อเรียบร้อยแล้ว")

    except Exception as e:
        print(f"❌ ไม่สามารถเชื่อมต่อ FTP ได้")

if __name__ == '__main__':
    test_ftp_connection()