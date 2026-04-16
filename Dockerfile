FROM python:3.11-slim

WORKDIR /app

# Install system deps (curl for font download)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Amiri Arabic font
RUN mkdir -p /app/bot/pdf/assets && \
    curl -fsSL \
    "https://github.com/aliftype/amiri/releases/download/1.000/Amiri-1.000.zip" \
    -o /tmp/amiri.zip && \
    unzip -o /tmp/amiri.zip "Amiri-1.000/Amiri-Regular.ttf" -d /tmp/amiri_ext/ && \
    mv /tmp/amiri_ext/Amiri-1.000/Amiri-Regular.ttf /app/bot/pdf/assets/ && \
    rm -rf /tmp/amiri.zip /tmp/amiri_ext

# Copy source code
COPY . .

# Create runtime directories
RUN mkdir -p /app/data/generated

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["python", "-m", "bot.main"]
