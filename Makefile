image_name = alidron/alidron-openzwave-controller
rpi_image_name = alidron/rpi-alidron-openzwave-controller
registry = neuron.local:6666

.PHONY: clean clean-dangling build build-rpi push push-rpi pull pull-rpi run-bash run-bash-rpi run run-rpi stop logs

clean:
	docker rmi $(image_name) || true

clean-dangling:
	docker rmi $(docker images -q -f dangling=true) || true

build: clean-dangling
	docker build --force-rm=true -t $(image_name) .
	docker tag -f $(image_name) $(registry)/$(image_name)

build-rpi: clean-dangling
	docker build --force-rm=true -t $(rpi_image_name) -f Dockerfile-rpi .
	docker tag -f $(rpi_image_name) $(registry)/$(rpi_image_name)

push:
	docker push $(registry)/$(image_name)

push-rpi:
	docker push $(registry)/$(rpi_image_name)

pull:
	docker pull $(registry)/$(image_name)
	docker tag $(registry)/$(image_name) $(image_name)

pull-rpi:
	docker pull $(registry)/$(rpi_image_name)
	docker tag $(registry)/$(rpi_image_name) $(rpi_image_name)

run-bash:
	docker run -it --rm -p 5555:5555 -p 6666:6666 --device=/dev/ttyACM0:/dev/ttyACM0 -v $(CURDIR)/volume:/usr/src/alidron-openzwave-controller/user-dir -v /media/nas/Homes/Axel/Development/Alidron/ZWave/axel/alidron-isac:/usr/src/alidron-isac --name=ozw-ctrl $(image_name) bash

run-bash-rpi:
	docker run -it --rm -p 5555:5555 -p 6666:6666 --device=/dev/ttyACM0:/dev/ttyACM0 -v $(CURDIR)/volume:/usr/src/alidron-openzwave-controller/user-dir -v /media/homes/Axel/Development/Alidron/ZWave/axel/alidron-isac:/usr/src/alidron-isac --name=ozw-ctrl $(rpi_image_name) bash

run:
	docker run -d -p 5555:5555 -p 6666:6666 --device=/dev/ttyACM0:/dev/ttyACM0 -v $(CURDIR)/volume:/usr/src/alidron-openzwave-controller/user-dir -v /media/nas/Homes/Axel/Development/Alidron/ZWave/axel/alidron-isac:/usr/src/alidron-isac --name=ozw-ctrl $(image_name) python ozw.py /dev/ttyACM0

run-rpi:
	docker run -d -p 5555:5555 -p 6666:6666 --device=/dev/ttyACM0:/dev/ttyACM0 -v $(CURDIR)/volume:/usr/src/alidron-openzwave-controller/user-dir -v /media/homes/Axel/Development/Alidron/ZWave/axel/alidron-isac:/usr/src/alidron-isac --name=ozw-ctrl $(rpi_image_name) python ozw.py /dev/ttyACM0

stop:
	docker stop ozw-ctrl
	docker rm ozw-ctrl

logs:
	docker logs -f ozw-ctrl
