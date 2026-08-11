FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 TZ=Asia/Ho_Chi_Minh

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

EXPOSE 8000

# Shell form (khong phai JSON array) de $PORT duoc expand. Railway/Render tu inject
# PORT; local va docker-compose khong co bien nay nen fallback ve 8000.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
