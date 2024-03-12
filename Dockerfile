FROM python:3.11

ARG PROJECT_ENV

ENV PROJECT_ENV=${PROJECT_ENV} \
  # Poetry
  POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_CREATE=false \
  POETRY_CACHE_DIR='/var/cache/pypoetry' \
  POETRY_HOME='/usr/local'

RUN apt update && apt upgrade -y \
	# Install GEO dependencies
	&& apt install -y \
	binutils \
	libproj-dev \
	gdal-bin \
	libsqlite3-mod-spatialite \
	# Poetry
  	&& curl -sSL 'https://install.python-poetry.org' | python - \
	&& poetry --version

WORKDIR /app
COPY poetry.lock pyproject.toml /code/

COPY . /app
RUN poetry install --no-dev

COPY . /app

EXPOSE 10000 

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["sh", "/entrypoint.sh"]
