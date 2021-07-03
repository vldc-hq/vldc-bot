FROM python:3.9-slim

RUN apt-get -y update && apt-get install -y ffmpeg

COPY . /app
WORKDIR /app

RUN pip install pipenv
RUN pipenv install --system

CMD ["python", "bot/main.py"]
