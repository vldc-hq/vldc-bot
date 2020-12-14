FROM python:3.8-slim

RUN apt-get -y update && apt-get install -y ffmpeg

ENV PYTHONPATH /app/bot
ENV POETRY_VERSION=1.1.4

COPY . /app
WORKDIR /app

RUN pip install "poetry==$POETRY_VERSION"
RUN poetry config virtualenvs.create false
RUN poetry install

# source from mounted volume (see docker-compose-dev.yml)
CMD ["python", "bot/main.py"]
