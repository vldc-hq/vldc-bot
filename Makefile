.PHONY: dev start

all: dev start

# create new venv and install deps
dev:
	python3 -m venv env
	./env/bin/python setup.py install

# start bot from venv (TOKEN should by in ENV)
start:
	export DEBUG=True && ./env/bin/python bot.py