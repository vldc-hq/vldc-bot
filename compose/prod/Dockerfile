FROM python:3.10-slim

RUN apt-get -y update && apt-get install -y ffmpeg

COPY . /app
WORKDIR /app

RUN pip install pipenv==2022.9.24
RUN pipenv install --system

CMD ["python", "bot/main.py"]
