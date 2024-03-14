FROM python:3.11

ENV PYTHONFAULTHANDLER=1 \
	PYTHONUNBUFFERED=1 \
	PYTHONDONTWRITEBYTECODE=1
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
	libsqlite3-mod-spatialite

	# Poetry
RUN curl -sSL 'https://install.python-poetry.org' | python - \
	&& poetry --version

WORKDIR /app

COPY poetry.lock pyproject.toml /app

COPY . /app
RUN poetry install --no-dev

CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
