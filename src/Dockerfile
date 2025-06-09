# 基于官方 Python 3.11 镜像
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/log

ENV TZ=Asia/Shanghai
EXPOSE 286 387
CMD ["python", "run387.py"]
