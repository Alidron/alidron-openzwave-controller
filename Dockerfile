# Copyright (c) 2015-2016 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

FROM alidron/python-openzwave:master
MAINTAINER Axel Voitier <axel.voitier@gmail.com>

# RUN pip install prospector

WORKDIR /usr/src/alidron-openzwave-controller

EXPOSE 5555 6666

ADD . /usr/src/alidron-openzwave-controller
