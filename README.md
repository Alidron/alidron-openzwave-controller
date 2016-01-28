Openzwave controller for Alidron
================================

[![build status](https://git.tinigrifi.org/ci/projects/8/status.png?ref=master)](https://git.tinigrifi.org/ci/projects/8?ref=master) [![Gitter](https://badges.gitter.im/gitterHQ/gitter.svg)](https://gitter.im/Alidron/talk)

This is an OpenZwave controller for Alidron. It bridges data on a ZWave network with data on an Alidron network.

The Docker images are accessibles on:
* x86: [alidron/alidron-openzwave-controller](https://hub.docker.com/r/alidron/alidron-openzwave-controller/)
* ARM/Raspberry Pi: [alidron/rpi-alidron-openzwave-controller](https://hub.docker.com/r/alidron/rpi-alidron-openzwave-controller/)

Dockerfiles are accessible from the Github repository:
* x86: [Dockerfile](https://github.com/Alidron/alidron-openzwave-controller/blob/master/Dockerfile)
* ARM/Raspberry Pi: [Dockerfile](https://github.com/Alidron/alidron-openzwave-controller/blob/master/Dockerfile-rpi)

Run
===

Assuming your ZWave controller is available on /dev/ttyACM0:
```
$ docker run -d --name=ozw-ctrl --device=/dev/ttyACM0:/dev/ttyACM0 -v `pwd`/volume:/usr/src/alidron-openzwave-controller/user-dir alidron/alidron-openzwave-controller python ozw.py /dev/ttyACM0
$ docker logs -f ozw-ctrl
```

After initialising the ZWave network (couple of minutes) all known devices command classes should be published as ISAC values on the Alidron network.

License and contribution policy
===============================

This project is licensed under LGPLv3.

To contribute, please, follow the [C4.1](http://rfc.zeromq.org/spec:22) contribution policy.


