# Dockerfile

# 1. Python tabanlı, hafif ve stabil bir imaj seç
FROM python:3.11-slim

# 2. Çalışma dizinini ayarla
WORKDIR /app

# 3. Gereken sistem bağımlılıklarını kur (opsiyonel, örnek: gcc, libssl-dev, libffi-dev, git)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libssl-dev libffi-dev git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4. Python bağımlılıklarını yükle
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 5. Proje dosyalarını kopyala
COPY . .

# 6. Ortam değişkenlerini ayarla (gizli bilgileri .env dosyası ile dışarıdan verebilirsin)
ENV PYTHONUNBUFFERED=1

# 7. Ana başlatıcıyı tanımla
CMD ["python", "main.py"]
