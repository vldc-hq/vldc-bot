FROM python:3.8-slim

RUN apt-get -y update && apt-get install -y ffmpeg

COPY . /app
WORKDIR /app

RUN python setup.py install

CMD ["python", "bot/main.py"]