FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 1001 transitai && \
    useradd --system --uid 1001 --gid 1001 --shell /sbin/nologin transitai

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir piper-tts

COPY --chown=transitai:transitai backend/ .

ENV PYTHONPATH=/app:/project \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER transitai

EXPOSE 8000

CMD sh -c "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips=*"
