#!/usr/bin/env bash
# Render build script: ติดตั้ง package -> รวมไฟล์ static -> อัปเดตฐานข้อมูล
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

# สร้าง superuser จาก DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD (ตั้งใน Render Dashboard)
# - ไม่ได้ตั้งค่าไว้ -> ข้าม
# - มี user นี้อยู่แล้ว -> ไม่ทำให้ build ล้ม
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ]; then
    python manage.py createsuperuser --noinput || echo "createsuperuser skipped (user may already exist)"
fi
