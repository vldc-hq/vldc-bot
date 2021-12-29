# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.209.6/containers/python-3/.devcontainer/base.Dockerfile

# [Choice] Python version (use -bullseye variants on local arm64/Apple Silicon): 3, 3.10, 3.9, 3.8, 3.7, 3.6, 3-bullseye, 3.10-bullseye, 3.9-bullseye, 3.8-bullseye, 3.7-bullseye, 3.6-bullseye, 3-buster, 3.10-buster, 3.9-buster, 3.8-buster, 3.7-buster, 3.6-buster
ARG VARIANT="3.9"
FROM mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT}

RUN apt-get -y update && apt-get install -y ffmpeg

# [Optional] If your pip requirements rarely change, uncomment this section to add them to the image.
# RUN mkdir -p /tmp/pip-tmp
COPY Pipfile* /tmp/pip-tmp/
RUN cd /tmp/pip-tmp && pip install pipenv==2021.5.29 \
 && pipenv install --dev --deploy --system --ignore-pipfile
# RUN pip install -U pip \
#  && pip install pipenv==2021.5.29 \
#  && pipenv lock -r > /tmp/pip-tmp/requirements.txt \
#  && pipenv lock -r --dev > /tmp/pip-tmp/requirements-dev.txt

# RUN pip --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
#  && pip --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements-dev.txt

# RUN /usr/local/bin/pip install pipenv==2021.5.29
# RUN mkdir -p /tmp/pip-tmp/
# RUN /usr/local/bin/python -m pipenv lock -r > /tmp/pip-tmp/requirements.txt
# RUN /usr/local/bin/pip --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
#     && rm -rf /tmp/pip-tmp
# RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
#    && rm -rf /tmp/pip-tmp

# [Optional] Uncomment this section to install additional OS packages.
# RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
#     && apt-get -y install --no-install-recommends <your-package-list-here>