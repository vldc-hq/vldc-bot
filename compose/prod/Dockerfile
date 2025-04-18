FROM python:3.10.7-slim

RUN apt-get -y update && apt-get install -y ffmpeg

COPY . /app
WORKDIR /app

RUN pip install pipenv==2024.4.1
RUN pipenv install --system

CMD ["python", "bot/main.py"]
