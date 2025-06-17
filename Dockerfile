FROM python:3.11-slim

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y \
    libglib2.0-0 libnss3 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 \
    libxext6 libxfixes3 libxi6 libxtst6 libatk1.0-0 libgtk-3-0 libdbus-1-3 \
    libx11-6 libxcb1 libx11-data libasound2 libatspi2.0-0 \
    curl wget gnupg unzip fonts-liberation libappindicator3-1 \
    && rm -rf /var/lib/apt/lists/*

COPY . /usr/src/app/

RUN pip install --no-cache-dir --force-reinstall -r requirements.txt && \
    playwright install --with-deps chromium &&\
    apt-get install -y xvfb &&\
    apt-get clean &&  \
    apt-get autoremove