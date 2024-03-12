HOST=${HOST:=0.0.0.0}
PORT=${PORT:=10000}

poetry run python manage.py runserver ${HOST}:${PORT}
