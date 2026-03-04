FROM python:3.12-slim

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# install python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# copy project
COPY . .

# ensure db directory exists
RUN mkdir -p /app/db

# collect static files (SECRET_KEY needed at build time for collectstatic)
ARG SECRET_KEY=build-only-key
ENV SECRET_KEY=${SECRET_KEY}
RUN python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 5005

# entrypoint: run migrations then start gunicorn
CMD python manage.py makemigrations --noinput && \
    python manage.py migrate --noinput && \
    gunicorn --config gunicorn-cfg.py config.wsgi
