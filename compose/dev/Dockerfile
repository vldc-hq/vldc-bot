FROM python:3.10.7-slim

RUN apt-get -y update && apt-get install -y ffmpeg build-essential

ENV PYTHONPATH /app

COPY . /app
WORKDIR /app

RUN pip install pipenv==2024.4.1
RUN pipenv install --dev --system

# source from mounted volume (see docker-compose-dev.yml)
CMD ["python", "bot/main.py"]
