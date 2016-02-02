# Copyright (c) 2015-2016 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

image_name = alidron/alidron-openzwave-controller
rpi_image_name = alidron/rpi-alidron-openzwave-controller
private_rpi_registry = neuron.local:6667

container_name = ozw-ctrl

run_args = --net=alidron -p 5555:5555 -p 6666:6666 --device=/dev/ttyACM0:/dev/ttyACM0 -v $(CURDIR)/volume:/usr/src/alidron-openzwave-controller/user-dir
run_alidron_test_args = --net=alidron-test -p 5555:5555 -p 6666:6666 --device=/dev/ttyACM0:/dev/ttyACM0 -v $(CURDIR)/volume:/usr/src/alidron-openzwave-controller/user-dir -e PYTHONUNBUFFERED=1
exec_args = python ozw.py /dev/ttyACM0
exec_cmd_args = python ozw_cmd.py /dev/ttyACM0

.PHONY: clean clean-dangling build build-rpi push push-rpi push-rpi-priv pull pull-rpi pull-rpi-priv run-bash run-bash-rpi run run-rpi run-cmd run-cmd-rpi stop logs

clean:
	docker rmi $(image_name) || true

clean-dangling:
	docker rmi `docker images -q -f dangling=true` || true

build: clean-dangling
	docker build --force-rm=true -t $(image_name) .

build-rpi: clean-dangling
	docker build --force-rm=true -t $(rpi_image_name) -f Dockerfile-rpi .

push:
	docker push $(image_name)

push-rpi:
	docker push $(rpi_image_name)

push-rpi-priv:
	docker tag -f $(rpi_image_name) $(private_rpi_registry)/$(rpi_image_name)
	docker push $(private_rpi_registry)/$(rpi_image_name)

pull:
	docker pull $(image_name)

pull-rpi:
	docker pull $(rpi_image_name)

pull-rpi-priv:
	docker pull $(private_rpi_registry)/$(rpi_image_name)
	docker tag $(private_rpi_registry)/$(rpi_image_name) $(rpi_image_name)

run-bash:
	docker run -it --rm --name=$(container_name) $(run_alidron_test_args) $(image_name) bash

run-bash-rpi:
	docker run -it --rm --name=$(container_name) $(run_args) $(rpi_image_name) bash

run:
	docker run -d --name=$(container_name) $(run_args) $(image_name) $(exec_args)

run-alidron-test:
	docker run -d --name=$(container_name) $(run_alidron_test_args) $(image_name) $(exec_args)

run-rpi:
	docker run -d --name=$(container_name) $(run_args) $(rpi_image_name) $(exec_args)

run-cmd:
	docker run -it --rm --name=$(container_name) $(run_args) $(image_name) $(exec_cmd_args)

run-cmd-rpi:
	docker run -it --rm --name=$(container_name) $(run_args) $(rpi_image_name) $(exec_cmd_args)

stop:
	docker stop ozw-ctrl
	docker rm ozw-ctrl

logs:
	docker logs -f ozw-ctrl
