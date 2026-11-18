FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0

COPY app.py forecaster.py ./

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 5000

# BIND_HOST=:: permite escuchar por IPv6 (por ejemplo, en la red privada de Railway).
CMD ["sh", "-c", "exec gunicorn --bind \"${BIND_HOST:-0.0.0.0}:${PORT}\" --workers 2 --timeout 30 --access-logfile - app:app"]
