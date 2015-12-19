image_name = alidron/alidron-openzwave-controller
rpi_image_name = alidron/rpi-alidron-openzwave-controller
registry = neuron.local:6666

container_name = ozw-ctrl

run_args = --net=alidron -p 5555:5555 -p 6666:6666 --device=/dev/ttyACM0:/dev/ttyACM0 -v $(CURDIR)/volume:/usr/src/alidron-openzwave-controller/user-dir # -v /media/nas/Homes/Axel/Development/Alidron/ZWave/axel/alidron-isac:/usr/src/alidron-isac
exec_args = python ozw.py /dev/ttyACM0
exec_cmd_args = python ozw_cmd.py /dev/ttyACM0

.PHONY: clean clean-dangling build build-rpi push push-rpi pull pull-rpi run-bash run-bash-rpi run run-rpi run-cmd run-cmd-rpi stop logs

clean:
	docker rmi $(image_name) || true

clean-dangling:
	docker rmi `docker images -q -f dangling=true` || true

build: clean-dangling
	docker build --force-rm=true -t $(image_name) .

build-rpi: clean-dangling
	docker build --force-rm=true -t $(rpi_image_name) -f Dockerfile-rpi .

push:
	docker tag -f $(image_name) $(registry)/$(image_name)
	docker push $(registry)/$(image_name)

push-rpi:
	docker tag -f $(rpi_image_name) $(registry)/$(rpi_image_name)
	docker push $(registry)/$(rpi_image_name)

pull:
	docker pull $(registry)/$(image_name)
	docker tag $(registry)/$(image_name) $(image_name)

pull-rpi:
	docker pull $(registry)/$(rpi_image_name)
	docker tag $(registry)/$(rpi_image_name) $(rpi_image_name)

run-bash:
	docker run -it --rm --name=$(container_name) $(run_args) $(image_name) bash

run-bash-rpi:
	docker run -it --rm --name=$(container_name) $(run_args) $(rpi_image_name) bash

run:
	docker run -d --name=$(container_name) $(run_args) $(image_name) $(exec_args)

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
