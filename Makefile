.PHONY: help install migrate redis web worker beat all test shell user clean

PORT ?= 8888
HOST ?= 127.0.0.1

help:
	@echo "Targets:"
	@echo "  install   uv sync deps"
	@echo "  redis     docker compose up -d redis"
	@echo "  migrate   apply migrations"
	@echo "  user      create superuser interactively"
	@echo "  web       granian on PORT (default $(PORT))"
	@echo "  worker    celery worker"
	@echo "  beat      celery beat (django scheduler)"
	@echo "  test      run scheduler test suite"
	@echo "  shell     django shell"
	@echo "  clean     stop redis container"

install:
	uv sync

redis:
	docker compose up -d redis

migrate:
	uv run python manage.py migrate

user:
	uv run python manage.py createsuperuser

web:
	uv run granian --interface asginl app.asgi:application --host $(HOST) --port $(PORT) --reload

worker:
	uv run celery -A app worker -l info --autoscale=24,0

beat:
	uv run celery -A app beat -l info -S django

test:
	uv run python manage.py test scheduler

shell:
	uv run python manage.py shell

clean:
	docker compose down
