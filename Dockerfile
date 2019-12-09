FROM python:3.6
RUN mkdir /simpals
WORKDIR /simpals
ADD requirements.txt /simpals/
RUN pip install -r requirements.txt
ADD . /simpals/
