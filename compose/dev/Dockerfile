FROM python:3.9-slim

RUN apt-get -y update && apt-get install -y ffmpeg

ENV PYTHONPATH /app

COPY . /app
WORKDIR /app

RUN pip install pipenv==2021.5.29
RUN pipenv install --dev --system

# source from mounted volume (see docker-compose-dev.yml)
CMD ["python", "bot/main.py"]
