.PHONY: dev test lint start dev_build dev_start dev_test

all: dev_start

# docker stuff
dev_build:
	docker-compose -f docker-compose-dev.yml build

dev_start:
	docker-compose -f docker-compose-dev.yml up -d && docker-compose -f docker-compose-dev.yml logs -f --tail=10

dev_stop:
	docker-compose -f docker-compose-dev.yml stop

dev_down:
	docker-compose -f docker-compose-dev.yml down

dev_test:
	docker-compose -f docker-compose-dev.yml run --rm bot pytest

# venv stuff
dev:
	python3 -m venv env
	./env/bin/pip install -r requirements-dev.txt

test:
	export PYTHONPATH=./bot && pytest

lint:
	flake8 ./bot --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 ./bot --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	mypy --config-file mypy.ini ./bot

mongo-up:
	docker-compose -f docker-compose-dev.yml up -d mongo

# start bot from venv (TOKEN and CHAT_ID should be in ENV)
start:
	export DEBUG=True && ./env/bin/python bot.py
