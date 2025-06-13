from flask import Flask
import os
from dotenv import load_dotenv
from .auth import auth_bp
from .routes import main_bp
from .models import init_db_connection # เพิ่มส่วนนี้
import secrets
import logging
from logging.handlers import RotatingFileHandler

def create_app():
 
    app = Flask(__name__)

    if not app.debug: # ตั้งค่า Logging เมื่อไม่ได้อยู่ใน Debug Mode
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application startup')
    # ========================

print(secrets.token_hex(24)) 

def create_app():
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env')) # โหลด .env จาก root

    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend', 'templates'),
                static_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend', 'static'))

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
    app.config['DB_USERNAME'] = os.getenv('DB_USERNAME')
    app.config['DB_PASSWORD'] = os.getenv('DB_PASSWORD')
    app.config['DB_DSN'] = os.getenv('DB_DSN')

    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 10 * 1024 * 1024)) # 10MB default
    app.config['ALLOWED_EXTENSIONS'] = set(os.getenv('ALLOWED_EXTENSIONS', 'pdf').split(','))

    # ตรวจสอบว่า UPLOAD_FOLDER มีอยู่จริงหรือไม่ ถ้าไม่มีให้สร้าง
    # ย้ายการสร้าง folder ไปที่ run.py เพื่อให้สร้างตอนเริ่มโปรแกรม
    # upload_dir = os.path.join(app.root_path, '..', app.config['UPLOAD_FOLDER'])
    # if not os.path.exists(upload_dir):
    #     os.makedirs(upload_dir)

    # Initialize Database Connection Pool (or other DB setup)
    init_db_connection(app) # ส่ง app instance ไปให้ models

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app