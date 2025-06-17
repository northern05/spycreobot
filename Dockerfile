FROM python:3.11-slim

WORKDIR /usr/src/app

COPY . /usr/src/app/

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    curl \
    gnupg \
    xvfb \
    xauth \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxss1 \
    libasound2 \
    libxcomposite1 \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    fonts-liberation \
    libappindicator3-1 \
    libdrm2 \
    libxdamage1 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libx11-xcb1 && \
    pip install --no-cache-dir --force-reinstall -r requirements.txt && \
    python -m playwright install --with-deps chromium && \
    apt-get clean && rm -rf /var/lib/apt/lists/*