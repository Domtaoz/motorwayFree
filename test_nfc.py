from smartcard.System import readers
from smartcard.util import toHexString
import time

def check_card_presence():
    # 1. เช็คว่ามีเครื่องอ่านต่ออยู่ไหม
    available_readers = readers()
    if not available_readers:
        print("❌ ไม่พบเครื่องอ่าน NFC กรุณาเชื่อมต่อ ACR122U")
        return

    reader = available_readers[0]
    print(f"✅ พบเครื่องอ่าน: {reader}")
    print("⏳ กรุณานำบัตรมาแตะที่เครื่อง... (กด Ctrl+C ที่ Terminal เพื่อหยุดการทำงาน)\n")

    # Command APDU สำหรับดึงรหัสบัตร (UID)
    GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
    
    last_uid = ""

    # 2. วนลูปเช็คสถานะการแตะบัตร
    while True:
        try:
            # พยายามเชื่อมต่อกับบัตร (ถ้าไม่มีบัตรวางอยู่ บรรทัดนี้จะ Error และกระโดดไปที่ except)
            connection = reader.createConnection()
            connection.connect()

            # ส่งคำสั่งไปดึง UID
            data, sw1, sw2 = connection.transmit(GET_UID)

            # ตรวจสอบสถานะการอ่าน (sw1=144 และ sw2=0 คืออ่านสำเร็จ)
            if sw1 == 144 and sw2 == 0:
                uid = toHexString(data).replace(" ", "")
                
                # เช็คว่าเพื่อไม่ให้มันปริ้นข้อความซ้ำรัวๆ ถ้าเป็นบัตรใบเดิมที่ยังวางแช่อยู่
                if uid != last_uid:
                    print(f"💳 พบการแตะบัตร! Card ID: {uid}")
                    last_uid = uid
                    
        except Exception as e:
            # เมื่อไม่มีบัตรแตะอยู่ หรือเอาบัตรออกแล้ว ระบบจะเข้าสู่ส่วนนี้
            if last_uid != "":
                print("👋 เอาบัตรออกแล้ว... รอรับบัตรใบใหม่\n")
                last_uid = "" # รีเซ็ตค่าเพื่อรอรับบัตรใบต่อไป
        
        # หน่วงเวลาสั้นๆ เพื่อไม่ให้ CPU ทำงานหนักเกินไป
        time.sleep(0.5)

if __name__ == '__main__':
    check_card_presence()