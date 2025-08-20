FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /usr/src/app
COPY . /usr/src/app/

RUN apt-get update && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/*