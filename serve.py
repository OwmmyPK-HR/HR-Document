# serve.py 
from backend.app import create_app
from waitress import serve
import os

# โหลด .env
from dotenv import load_dotenv
load_dotenv()

app = create_app()

# สร้าง UPLOAD_FOLDER ถ้ายังไม่มี
upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
if not os.path.exists(upload_folder):
   os.makedirs(upload_folder)
   print(f"Created upload folder: {upload_folder}")

# รันแอปด้วย Waitress
serve(app, host='0.0.0.0', port=5000, threads=8) # อาจเพิ่ม threads ตามความเหมาะสมของ CPU