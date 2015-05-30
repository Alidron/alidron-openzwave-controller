FROM alidron/python-openzwave:0.2.6
MAINTAINER Axel Voitier <axel.voitier@gmail.com>

# RUN pip install prospector

WORKDIR /usr/src/alidron-openzwave-controller

EXPOSE 5555 6666

ADD . /usr/src/alidron-openzwave-controller