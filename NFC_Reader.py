from smartcard.scard import *
from smartcard.util import toHexString
import time

VERBOSE = False

# Constants and APDU Commands
BLOCK_NUMBER = 0x04
AUTHENTICATE = [0xFF, 0x88, 0x00, BLOCK_NUMBER, 0x60, 0x00] # ใช้ Key A (0x60)
GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
READ_16_BINARY_BLOCKS = [0xFF, 0xB0, 0x00, BLOCK_NUMBER, 0x10]

class NFC_Reader():
    def __init__(self):
        self.uid = ""
        self.reader = None
        self.hcard = None
        
        try:
            self.hresult, self.hcontext = SCardEstablishContext(SCARD_SCOPE_USER)
            self.hresult, self.readers = SCardListReaders(self.hcontext, [])
            
            if len(self.readers) == 0:
                print("[Error] ไม่พบเครื่องอ่าน NFC/RFID กรุณาตรวจสอบการเชื่อมต่อ")
                return
                
            self.reader = self.readers[0]
            print(f"[Success] Found reader: {self.reader}")
            
            self.hresult, self.hcard, self.dwActiveProtocol = SCardConnect(
                self.hcontext,
                self.reader,
                SCARD_SHARE_SHARED,
                SCARD_PROTOCOL_T0 | SCARD_PROTOCOL_T1
            )
        except Exception as e:
            print(f"[Error] Initializer Error: {e}")

    def read_uid(self):
        if not self.hcard: return None
        response, value = self.send_command(GET_UID)
        if response and len(response) >= 4:
            self.uid = value
            return self.uid
        return None

    def send_command(self, command):
        if not self.hcard: return None, None
        for iteration in range(1):
            try:
                self.hresult, response = SCardTransmit(self.hcard, self.dwActiveProtocol, command)
                value = toHexString(response, format=0).replace(" ", "")
                if VERBOSE:
                    print(f"Command: {command} | Value: {value} | Response: {response}")
                return response, value
            except Exception as e:
                if VERBOSE: print(f"Send Command Error: {e}")
            time.sleep(0.1)
        return None, None

    def write_data(self, string):
        if not self.hcard: return False
        
        int_array = list(map(ord, string))
        print(f"Writing data: {int_array}")

        if len(int_array) > 16:
            print("[Error] ข้อมูลยาวเกินไป (จำกัด 16 bytes)")
            return False

        update_command = [0xFF, 0xD6, 0x00, BLOCK_NUMBER, 0x10]
        
        # เติมข้อมูลให้ครบ 16 bytes (Padding ด้วย 0x00)
        padded_array = int_array + [0x00] * (16 - len(int_array))
        update_command.extend(padded_array)

        response, value = self.send_command(AUTHENTICATE)

        if response == [144, 0]: 
            print("[Success] Authentication successful.")
            res, val = self.send_command(update_command)
            if res == [144, 0]:
                print(f"[Success] เขียนข้อมูล '{string}' ลงบัตรสำเร็จ")
                return True
            else:
                print("[Error] เขียนข้อมูลล้มเหลว")
        else:
            print("[Error] Unable to authenticate. เช็ค Key หรือ Block Number")
        return False

    def read_data(self):
        if not self.hcard: return None
        
        response, value = self.send_command(AUTHENTICATE)
        if response == [144, 0]:
            print("[Success] Authentication successful.")
            result, value = self.send_command(READ_16_BINARY_BLOCKS)
            
            if result and result[-2:] == [144, 0]: 
                data_bytes = result[:-2] 
                try:
                    decoded_string = "".join(chr(b) for b in data_bytes if b != 0x00)
                    return decoded_string
                except Exception:
                    return data_bytes
            return None
        else:
            print("[Error] Unable to authenticate.")
            return None

if __name__ == '__main__':
    reader = NFC_Reader()
    if reader.reader:
        uid = reader.read_uid()
        print(f"นำข้อมูลนี้ไปใช้ map กับ รหัสนิสิต : {uid}")