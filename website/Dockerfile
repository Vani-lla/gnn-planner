FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project
COPY . /app/

# Patch settings at build-time to use docker DB host if provided
# This substitutes the HOST in DATABASES to use env DATABASE_HOST (default: db)
ARG DATABASE_HOST=db
RUN sed -i "s/\"HOST\": \"localhost\"/\"HOST\": \"${DATABASE_HOST}\"/" /app/inzynierka/settings.py

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
