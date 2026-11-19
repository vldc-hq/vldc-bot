FROM python:3.14.10-slim

RUN apt-get -y update && apt-get install -y ffmpeg build-essential

ENV PYTHONPATH /app
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN pip install uv==0.9.28

COPY pyproject.toml uv.lock /app/
RUN python -m venv /opt/venv
RUN uv sync --active --dev --no-install-project

COPY . /app

# source from mounted volume (see docker-compose-dev.yml)
CMD ["python", "bot/main.py"]
