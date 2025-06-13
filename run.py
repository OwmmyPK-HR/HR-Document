# -*- coding: utf-8 -*-
from backend.app import create_app
import os

# โหลด environment variables จาก .env 
from dotenv import load_dotenv
load_dotenv()

app = create_app()

if __name__ == '__main__':
    # ตรวจสอบว่า UPLOAD_FOLDER มีอยู่จริงหรือไม่ ถ้าไม่มีให้สร้าง
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        print(f"Created upload folder: {upload_folder}")

    app.run(host='0.0.0.0', port=5000)