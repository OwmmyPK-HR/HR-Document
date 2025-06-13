# Dockerfile

# 1. ใช้ Python image เป็น base
FROM python:3-slim

# 2. ตั้งค่า working directory ภายใน container
WORKDIR /app

# 3. คัดลอกไฟล์ requirements.txt และติดตั้งไลบรารี
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 4. คัดลอกโค้ดโปรเจกต์ทั้งหมดเข้าไปใน container
COPY . .

# 5. คำสั่งที่จะรันเมื่อ container เริ่มทำงาน
CMD ["python", "serve.py"]