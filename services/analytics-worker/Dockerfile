FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir --no-deps ultralytics==8.4.41
RUN pip install --no-cache-dir setuptools==80.9.0
ENV YOLO_CONFIG_DIR=/tmp

COPY app ./app

EXPOSE 9101

CMD ["python", "-m", "app.main"]
