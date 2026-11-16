FROM python:3.11-slim

# command injection 점검 도구(/admin/tools)가 ping을 사용하므로 설치
RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 18080
CMD ["python", "run.py"]
