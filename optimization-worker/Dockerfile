# Multi-stage, non-root — docs/RULES.md §4.1
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS runtime

RUN groupadd -r appgroup && useradd -r -g appgroup appuser
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

RUN chown -R appuser:appgroup /app
USER appuser

# src-layout package lives at /app/src/optimizer — put it on the path (the
# backend image does the equivalent via uvicorn's --app-dir src).
ENV PYTHONPATH=/app/src

CMD ["python", "-m", "optimizer.worker"]
