FROM python:3.8-slim

ENV PYTHONPATH /app/bot

COPY ./setup.py /app/setup.py
COPY ./requirements.txt /app/requirements.txt
COPY ./requirements-dev.txt /app/requirements-dev.txt

WORKDIR /app

RUN python -m pip install -r ./requirements-dev.txt

# source from mounted volume (see docker-compose-dev.yml)
CMD ["python", "bot/main.py"]