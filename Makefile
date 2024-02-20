ifneq (,$(wildcard .env))
	include .env
endif

HOST ?= 127.0.0.1
PORT ?= 8000
WEB_CONCURRENCY ?= 4

STARTAPP_NAME := web_dashboard
MANAGE := poetry run python manage.py


.PHONY: install
install:
	poetry install

.PHONY: setup
setup:	install migrate
	$(MANAGE) collectstatic --no-input

.PHONY: migrate
migrate:
	$(MANAGE) migrate

.PHONY: makemigrations
makemigrations:
	$(MANAGE) makemigrations

.PHONY: prod
prod:
	poetry run gunicorn -w $(WEB_CONCURRENCY) -b $(HOST):$(PORT) $(STARTAPP_NAME).wsgi:application

.PHONY: dev
dev:
	$(MANAGE) runserver

.PHONY: shell
shell:
	$(MANAGE) shell_plus

.PHONY: makemessages 
makemessages:
	# Use compilemessages when updated translation
	poetry run django-admin makemessages -l ru

.PHONY: compilemessages
compilemessages:
	poetry run django-admin compilemessages

.PHONY: lint
lint:
	poetry run flake8 task_manager --exclude migrations
