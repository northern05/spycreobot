FROM python:3.11-slim

WORKDIR /usr/src/app

RUN apt-get update && apt-get upgrade -y && \
    playwright install --with-deps chromium &&\
    apt-get clean && apt-get autoremove

COPY . /usr/src/app/

RUN pip install --no-cache-dir --force-reinstall -r requirements.txt