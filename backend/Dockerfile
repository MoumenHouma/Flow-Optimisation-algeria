# Multi-stage, non-root, healthcheck — see docs/RULES.md §4.1
FROM python:3.11-slim AS builder

WORKDIR /app
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS runtime

RUN groupadd -r appgroup && useradd -r -g appgroup appuser \
    && apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "routeopt.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
