from ftplib import FTP
import sys

FTP_HOST = '158.108.98.128' 
FTP_USER = 'st03603423'
FTP_PASS = 'st03603423'

def test_ftp_connection():
    print(f"connecting to FTP Server: {FTP_HOST}...")
    try:
        ftp = FTP(FTP_HOST)
        
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        print("Login successful!")
        print("Welcome message:", ftp.getwelcome())
        
        print("\n--- List ---")
        ftp.retrlines('LIST')
        
        try:
            ftp.cwd('motorwayFree')
            print("Changed to 'motorwayFree' successfully!")
        except Exception as e:
            print(f"Cannot change to 'motorwayFree' (folder might not be created): {e}")

        ftp.quit()
        print("Connection closed successfully!")

    except Exception as e:
        print(f"cannot connect to FTP Server: {e}")

if __name__ == '__main__':
    test_ftp_connection()