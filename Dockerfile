FROM python:3.11

RUN apt-get update && apt-get upgrade -y && apt-get install -y chromium-driver
RUN pip install --upgrade pip

WORKDIR /usr/src/app

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir --force-reinstall -r requirements.txt

COPY . /usr/src/app/

WORKDIR /usr/src/app