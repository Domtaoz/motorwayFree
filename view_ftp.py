import json
import io
from ftplib import FTP

FTP_HOST = '158.108.98.128' 
FTP_USER = 'st03603423'  
FTP_PASS = 'st03603423'      
DB_FILE = 'motorwayFree/database.json'

print(f"connecting to {FTP_HOST} ")

try:
    ftp = FTP(FTP_HOST)
    ftp.connect(timeout=10)
    ftp.login(user=FTP_USER, passwd=FTP_PASS)
    print("connected successfully!\n")
    
    mem_file = io.BytesIO()
    ftp.retrbinary(f'RETR {DB_FILE}', mem_file.write)
    ftp.quit()
    
    print("downloaded data successfully!\n")
    
    mem_file.seek(0)
    file_content = mem_file.read().decode('utf-8')
    data = json.loads(file_content)
    
    print(f" data (folder: {DB_FILE}) ")
    
    formatted_json = json.dumps(data, indent=4, ensure_ascii=False)
    print(formatted_json)
    
    
except Exception as e:
    print(f"\n❌ Error: {e}\n")
