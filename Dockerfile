FROM nikolaik/python-nodejs:python3.8-nodejs13-alpine

COPY requirements.txt /
WORKDIR /
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install -r requirements.txt
