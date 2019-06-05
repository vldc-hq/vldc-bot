all: venv start

# create new venv and install deps
dev:
	python3 -m venv env
	source ./env/bin/activate && pip install -r requirements.txt

install:
	python3 -m venv env
	./env/bin/python setup.py install


# start bot from venv (TOKEN should by in ENV)
start:
	./env/bin/python smilebot.py

