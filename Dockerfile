# check=skip=SecretsUsedInArgOrEnv

# 1. First - Builder stage
FROM python:3.14-slim AS builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    DEBUG=True 
    
RUN apt-get update && apt-get install -y --no-install-recommends gettext 

COPY requirements.txt /app/
RUN pip install --no-cache-dir --no-compile --user -r requirements.txt

# Copy application code
COPY . /app/

# Compile translations and collect static files
RUN python manage.py compilemessages -v 0 --ignore=.git/* --ignore=static/* --ignore=.mypy_cache/* \
    && python manage.py collectstatic --noinput -v 2 \
    && echo "=== Verifying collected static files ===" \
    && ls -la /app/static/ \
    && echo "=== Static files count ===" \
    && find /app/static -type f | wc -l


# 2. Second - Final stage - minimal runtime image
FROM python:3.14-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    SCHEDULER_ENABLED=true \
    DEBUG=True \
    SECRET_KEY=build-time-insecure-secret-key \
    PATH=/root/.local/bin:$PATH

# Copy Python packages from builder stage
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . /app/

# Copy collected static files from builder stage
COPY --from=builder /app/static /app/static

RUN apt-get update && apt-get install -y --no-install-recommends \
    mc \
    sqlite3 \
    vim \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /app/db /app/media /app/static

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py update_site && python manage.py runserver 0.0.0.0:8000"]