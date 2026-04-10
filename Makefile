# ─────────────────────────────────────────────────────────────
#  DeepTrace — Docker Build & Push (Windows Compatible)
#  Usage: make release
# ─────────────────────────────────────────────────────────────

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

## build: build the Docker image
build:
	@echo Building $(FULL_IMAGE):$(TAG) ...
	@if not exist weights mkdir weights
	@if not exist logs mkdir logs
	docker build --platform $(PLATFORM) --tag $(FULL_IMAGE):$(TAG) --file Dockerfile --progress=plain .
	@echo Build complete: $(FULL_IMAGE):$(TAG)

## build-worker: build the Celery worker Docker image
build-worker:
	@echo Building $(FULL_WORKER):$(TAG) ...
	@if not exist logs mkdir logs
	docker build --platform $(PLATFORM) --tag $(FULL_WORKER):$(TAG) --file Dockerfile.worker --progress=plain .
	@echo Build complete: $(FULL_WORKER):$(TAG)

## push: push image to Docker Hub
push:
	@echo Pushing $(FULL_IMAGE):$(TAG) ...
	docker push $(FULL_IMAGE):$(TAG)
	@echo Pushed: $(FULL_IMAGE):$(TAG)

## push-worker: push worker image to Docker Hub
push-worker:
	@echo Pushing $(FULL_WORKER):$(TAG) ...
	docker push $(FULL_WORKER):$(TAG)
	@echo Pushed: $(FULL_WORKER):$(TAG)

## release: build + push + tag and push as latest
release: build build-worker push push-worker
	@echo Tagging as latest ...
	docker tag $(FULL_IMAGE):$(TAG) $(FULL_IMAGE):latest
	docker push $(FULL_IMAGE):latest
	docker tag $(FULL_WORKER):$(TAG) $(FULL_WORKER):latest
	docker push $(FULL_WORKER):latest
	@echo Released: $(FULL_IMAGE):latest and $(FULL_WORKER):latest

## login: log in to Docker Hub
login:
	docker login --username $(DOCKER_USER)

## clean: remove local images
clean:
	-docker rmi $(FULL_IMAGE):$(TAG)
	-docker rmi $(FULL_IMAGE):latest
	-docker rmi $(FULL_WORKER):$(TAG)
	-docker rmi $(FULL_WORKER):latest

## help: show available targets
help:
	@echo.
	@echo DeepTrace Docker Makefile
	@echo.
	@echo   make / make all       build + push (all images)
	@echo   make build            build Flask app only
	@echo   make build-worker     build Celery worker only
	@echo   make push             push Flask app only
	@echo   make push-worker      push Celery worker only
	@echo   make release          build + push + tag latest (all images)
	@echo   make login            docker login
	@echo   make clean            remove local images
	@echo.
	@echo   DOCKER_USER = $(DOCKER_USER)
	@echo   IMAGE_NAME  = $(IMAGE_NAME)
	@echo   WORKER_NAME = $(WORKER_NAME)
	@echo   TAG         = $(TAG)
	@echo   PLATFORM    = $(PLATFORM)
	@echo.