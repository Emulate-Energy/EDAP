deps:
	pip install --no-cache-dir -r requirements.txt

build-linux-image:
	 docker build -f ./Dockerfile -t edap_gateway:latest --ssh=default .

run-linux-container-local: build-linux-image
	docker run --rm --name edap_gateway \
	--net ghidorah_default \
	-e LOG_LEVEL=DEBUG \
	-e COMMANDER_PROXY_BASE_URL=ws://connect_commander_proxy:8000/ws/edap/ \
	-e DEVICE_ID=b63b9773-d234-4415-99e7-3cac574d48ac \
	-e RANDOM_DUMMY_DATA=true \
	edap_gateway:latest

build-pi-image:
	docker buildx build --builder=arm-builder --platform=linux/arm/v8 -f Dockerfile --load -t edap_basic:latest_arm .

tag-arm-image: build-pi-image
	docker tag edap_basic:latest_arm edapter/basic:latest_arm

push-pi-image: tag-arm-image
	docker push edapter/basic:latest_arm
