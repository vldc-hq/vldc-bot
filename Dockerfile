FROM python:3.7-slim

COPY . /app
WORKDIR /app

RUN python setup.py install

CMD ["python", "bot/main.py"]