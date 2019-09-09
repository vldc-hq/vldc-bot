.PHONY: install start

all: install start

# create new venv and install deps
install:
	python3 -m venv env
	./env/bin/python setup.py install

# start bot from venv (TOKEN should by in ENV)
start:
	export DEBUG=True && ./env/bin/python smilebot.py