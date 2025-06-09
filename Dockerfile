FROM python:3.11

RUN apt-get update && apt-get upgrade -y && apt-get clean && apt-get autoremove
RUN pip install --upgrade pip

WORKDIR /usr/src/app

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir --force-reinstall -r requirements.txt &&\
    playwright install --with-deps chromium &&\
    apt-get clean && apt-get autoremove

COPY . /usr/src/app/

WORKDIR /usr/src/app