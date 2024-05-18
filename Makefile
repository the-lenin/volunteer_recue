ifneq (,$(wildcard .env))
	include .env
endif

HOST ?= 127.0.0.1
PORT ?= 8000
WEB_CONCURRENCY ?= 4

STARTAPP_NAME := web_dashboard
MANAGE := poetry run python manage.py
DOCKER := sudo docker


setup:	install migrate collectstatic

install:
	poetry install

makemigrations:
	$(MANAGE) makemigrations

pg-extension:
	psql "$(DATABASE_URL_EXT)" -c "CREATE EXTENSION IF NOT EXISTS postgis;"

pg-shell:
	$(MANAGE) dbshell

migrate:
	$(MANAGE) migrate

create_superuser:
	poetry run ./manage.py createsuperuser --no-input

collectstatic:
	$(MANAGE) collectstatic --no-input

makemessages:
	# Use compilemessages when updated translation
	poetry run django-admin makemessages -l ru

compilemessages:
	poetry run django-admin compilemessages

lint:
	poetry run flake8 task_manager --exclude migrations

test:
	$(MANAGE) test

shell:
	$(MANAGE) shell_plus

dev:
	$(MANAGE) runserver $(HOST):$(PORT)

prod:
	poetry run gunicorn -w $(WEB_CONCURRENCY) -b $(HOST):$(PORT) $(STARTAPP_NAME).wsgi:application

docker-build:
	$(DOCKER) build -t $(STARTAPP_NAME)_app --network host . 

docker-network:
	$(DOCKER) network create $(STARTAPP_NAME)_db_network

docker-db:
	$(DOCKER) run --name $(STARTAPP_NAME)_db \
		-p 5432:5432 \
		-e POSTGRES_USER=$(POSTGRES_USER) \
		-e POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) \
		-e POSTGRES_DB=$(POSTGRES_DB) \
		--network $(STARTAPP_NAME)_db_network \
		-d postgis/postgis:16-3.4

docker-db-shell:
	$(DOCKER) exec -ti $(STARTAPP_NAME)_db bash 

docker-start:
	$(DOCKER) run --name $(STARTAPP_NAME) \
		-p $(PORT):8000 \
		--env-file .env \
		--network $(STARTAPP_NAME)_db_network \
		-d $(STARTAPP_NAME)_app

docker-migrate:
	$(DOCKER) exec -it $(STARTAPP_NAME) poetry run python manage.py migrate

docker-prune:
	$(DOCKER) container rm $(STARTAPP_NAME) $(STARTAPP_NAME)_db -f

docker-up: docker-prune docker-db sleep docker-start docker-migrate

sleep:
	sleep 3 

bot-start:
	DJANGO_SETTINGS_MODULE=$(STARTAPP_NAME).settings poetry run python tgbot/bot.py
