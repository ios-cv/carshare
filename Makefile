.PHONY: nothing start-docker stop-docker clean-docker format

ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))


start-docker: ## Starts docker containers of dependencies for local development and testing.
	@echo Starting docker containers of dependencies
	docker-compose run --rm start_dependencies

stop-docker: ## Stops docker containers of dependencies for local development and testing.
	@echo Stopping docker containers of dependencies
	docker-compose stop

clean-docker: ## Deletes the docker containers of dependencies for local development and testing.
	@echo Removing docker containers
	docker-compose down -v
	docker-compose rm -v

nothing:
	@echo Please specify a make target.

format:
	poetry run black .

build:
	poetry run python manage.py tailwind build

bundle: build
	tar -czv --exclude-vcs --exclude-vcs-ignores --exclude '*/bundle.tar.gz' --exclude '*/node_modules' --exclude 'carshare/media' --exclude '*/__pycache__' -f bundle.tar.gz ../carshare/* ../crispy-tailwind/*
