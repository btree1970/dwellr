FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    supervisor \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

RUN mkdir -p /var/log/supervisor

COPY . .

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# server
EXPOSE 8000
# flower ui
EXPOSE 5555

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
