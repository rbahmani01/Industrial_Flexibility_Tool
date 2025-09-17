FROM python:3.11-slim

# Install CBC solver (faster, avoids PuLP downloading binary at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    coinor-cbc \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 5050
CMD ["python", "app.py"]
