FROM python:3.14.2-slim

RUN apt-get -y update && apt-get install -y ffmpeg

ENV PYTHONPATH /app
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN pip install uv==0.9.28

COPY pyproject.toml /app/
RUN python -m venv /opt/venv
RUN uv sync --active --no-dev --no-install-project \
    && python -c "import os, shutil, site; p=os.path.join(site.getsitepackages()[0],'google','_upb'); shutil.rmtree(p, ignore_errors=True)"

COPY . /app

CMD ["python", "bot/main.py"]
