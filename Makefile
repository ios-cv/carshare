.PHONY: nothing start-docker stop-docker clean-docker format setup-crispy-tailwind

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

generate-er-diagram:
	@echo Generating DOT file
	poetry run python manage.py graph_models -a > documentation/model.dot
	@echo Converting to SVG
	dot -Tsvg documentation/model.dot -o documentation/model.svg
	@echo Inserting into html viewer
	poetry run python documentation/insert-diagram.py documentation/template_entity_relationship_diagram.html documentation/model.svg documentation/entity_relationship_diagram.html

setup-crispy-tailwind:
	@echo Setting up our modified version of crispy tailwind...
	test -s crispy_tailwind || (\
		git clone https://github.com/grundleborg/crispy-tailwind.git ../crispy-tailwind && \
		cd ../crispy-tailwind && git checkout carshare && cd ../carshare && \
		ln -s ../crispy-tailwind/crispy_tailwind crispy_tailwind \
	)
