FROM python:3.11-slim

WORKDIR /usr/src/app

COPY . /usr/src/app/

RUN apt-get install -y wget gnupg xvfb xauth libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxss1 libasound2  \
    libxcomposite1 libxrandr2 libgbm1 libgtk-3-0 &&  \
    pip install --no-cache-dir --force-reinstall -r requirements.txt && \
    playwright install --with-deps chromium &&\
    apt-get clean &&  \
    apt-get autoremove