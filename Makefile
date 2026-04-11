DOCKER_USER  ?= ayushsingh23
IMAGE_NAME   ?= deeptrace-ml
WORKER_NAME  ?= deeptrace-worker
TAG          ?= $(shell git rev-parse --short HEAD 2>NUL || echo latest)
FULL_IMAGE   := $(DOCKER_USER)/$(IMAGE_NAME)
FULL_WORKER  := $(DOCKER_USER)/$(WORKER_NAME)
PLATFORM     ?= linux/amd64

.DEFAULT_GOAL := all
.PHONY: all build build-worker push push-worker release login clean help

all: build build-worker push push-worker

build:
	@echo Building $(FULL_IMAGE):$(TAG) ...
	docker build --platform $(PLATFORM) \
	  --cache-from $(FULL_IMAGE):latest \
	  --tag $(FULL_IMAGE):$(TAG) \
	  --file Dockerfile --progress=plain .

build-worker: build
	@echo Building $(FULL_WORKER):$(TAG) from $(FULL_IMAGE):$(TAG) ...
	docker build --platform $(PLATFORM) \
	  --build-arg BASE_IMAGE=$(FULL_IMAGE):$(TAG) \
	  --tag $(FULL_WORKER):$(TAG) \
	  --file Dockerfile.worker --progress=plain .

push:
	docker push $(FULL_IMAGE):$(TAG)

push-worker:
	docker push $(FULL_WORKER):$(TAG)

release: build build-worker push push-worker
	docker tag $(FULL_IMAGE):$(TAG) $(FULL_IMAGE):latest
	docker push $(FULL_IMAGE):latest
	docker tag $(FULL_WORKER):$(TAG) $(FULL_WORKER):latest
	docker push $(FULL_WORKER):latest
	@echo Released both images as latest.

login:
	docker login --username $(DOCKER_USER)

clean:
	-docker rmi $(FULL_IMAGE):$(TAG) $(FULL_IMAGE):latest
	-docker rmi $(FULL_WORKER):$(TAG) $(FULL_WORKER):latest

help:
	@echo.
	@echo   make build          Flask image only
	@echo   make build-worker   Worker image (reuses Flask layers)
	@echo   make release        Build + push + tag latest
	@echo   make login          Docker Hub login
	@echo   make clean          Remove local images