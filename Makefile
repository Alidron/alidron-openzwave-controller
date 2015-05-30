image_name = alidron/alidron-openzwave-controller

.PHONY: clean clean-dangling build run-bash run stop logs

clean:
	docker rmi $(image_name) || true

clean-dangling:
	docker rmi $(docker images -q -f dangling=true) || true

build: clean-dangling
	docker build --force-rm=true -t $(image_name) .

run-bash:
	docker run -it --rm -p 5555:5555 -p 6666:6666 --device=/dev/ttyACM0:/dev/ttyACM0 -v $(CURDIR)/volume:/usr/src/alidron-openzwave-controller/user-dir -v /media/nas/Homes/Axel/Development/Alidron/ZWave/axel/alidron-isac:/usr/src/alidron-isac --name=ozw-ctrl $(image_name) bash

run:
	docker run -d -p 5555:5555 -p 6666:6666 --device=/dev/ttyACM0:/dev/ttyACM0 -v $(CURDIR)/volume:/usr/src/alidron-openzwave-controller/user-dir -v /media/nas/Homes/Axel/Development/Alidron/ZWave/axel/alidron-isac:/usr/src/alidron-isac --name=ozw-ctrl $(image_name) python ozw.py /dev/ttyACM0

stop:
	docker stop ozw-ctrl
	docker rm ozw-ctrl

logs:
	docker logs -f ozw-ctrl
