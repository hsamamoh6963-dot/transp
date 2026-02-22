# استخدم نسخة بايثون خفيفة
FROM python:3.12-slim

# ضبط المتغيرات لضمان عدم تأخير المخرجات (Logs)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# تحديد مجلد العمل داخل الحاوية
WORKDIR /app

# تثبيت مكتبات النظام اللازمة لـ PostgreSQL و Whitenoise
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# تثبيت المكتبات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ ملفات المشروع
COPY . .

# تجميع الملفات الثابتة (Static Files)
RUN python manage.py collectstatic --noinput

# فتح المنفذ (Koyeb يستخدم 8000 افتراضياً)
EXPOSE 8000

# أمر التشغيل النهائي
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "core.wsgi:application"]