FROM nikolaik/python-nodejs:python3.6-nodejs13-alpine

RUN apk --no-cache add gcc libc-dev libxml2-dev libxslt-dev
RUN apk --no-cache add chromium chromium-chromedriver

COPY requirements.txt /

RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install -r requirements.txt
