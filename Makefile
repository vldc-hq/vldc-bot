.PHONY: dev start

all: dev start

# create new venv and install deps
dev:
	python3 -m venv env
	./env/bin/pip install -r requirements-dev.txt

test:
	export PYTHONPATH=./bot && pytest

lint:
	flake8 ./bot --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 ./bot --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	mypy --config-file mypy.ini ./bot

# start bot from venv (TOKEN and CHAT_ID should by in ENV)
start:
	export DEBUG=True && ./env/bin/python bot.py

build:
	docker build -t vldcbot .