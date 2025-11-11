FROM python:3.11.12-slim

RUN apt-get -y update && apt-get install -y ffmpeg gnupg

COPY . /app
WORKDIR /app

RUN pip install pipenv==2024.4.1
RUN pipenv install --system

CMD ["python", "bot/main.py"]
