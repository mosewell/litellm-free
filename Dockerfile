FROM python:3.12-slim

RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/

RUN echo "0 0 * * * root /usr/local/bin/python /app/refresh_cron.py > /proc/1/fd/1 2>&1" > /etc/cron.d/refresh-models && \
    chmod 0644 /etc/cron.d/refresh-models

CMD ["python", "entrypoint.py"]
