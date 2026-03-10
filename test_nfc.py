from smartcard.System import readers
from smartcard.util import toHexString
import time

def check_card_presence():
    available_readers = readers()
    if not available_readers:
        print("NFC not found.")
        return

    reader = available_readers[0]
    print(f"found: {reader}")

    GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
    
    last_uid = ""

    while True:
        try:
            connection = reader.createConnection()
            connection.connect()

            data, sw1, sw2 = connection.transmit(GET_UID)

            if sw1 == 144 and sw2 == 0:
                uid = toHexString(data).replace(" ", "")
                
                if uid != last_uid:
                    print(f"Card ID: {uid}")
                    last_uid = uid
                    
        except Exception as e:
            if last_uid != "":
                print("Card removed.\n")
                last_uid = "" 
        
        time.sleep(0.5)

if __name__ == '__main__':
    check_card_presence()