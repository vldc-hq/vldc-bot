FROM python:3.8-slim

RUN apt-get -y update && apt-get install -y ffmpeg

ENV POETRY_VERSION=1.1.4

COPY . /app
WORKDIR /app

RUN pip install "poetry==$POETRY_VERSION"
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

CMD ["python", "bot/main.py"]
