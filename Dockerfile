FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client && \
    rm -rf /var/lib/apt/lists/*

COPY Requirements.txt .
RUN pip install --no-cache-dir -r Requirements.txt

COPY . .

# Create media directories and set permissions
RUN mkdir -p media/reports media/temp && \
    chmod -R 777 media

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"] 