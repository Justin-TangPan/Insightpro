# Pinned upstream source + its isolated Python dependencies; no Hermes server runs.
FROM nousresearch/hermes-agent:v2026.8.19@sha256:3811ed13da874fba2ac99b6d492db9a203d34cb6dccf90d886948c00d0ccec09 AS runtime

USER root

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

WORKDIR /app

RUN groupadd --gid 10001 insight \
    && useradd --uid 10001 --gid insight --create-home insight

COPY backend/requirements.txt ./requirements.txt
RUN uv venv /opt/insight-venv --python /usr/bin/python3 \
    && uv pip install --python /opt/insight-venv/bin/python -r requirements.txt \
    && chmod -R a+rX /opt/insight-venv

ENV PATH="/opt/insight-venv/bin:/usr/local/bin:/usr/bin:/bin"

# Local ignored checkout at the same revision as the dependency image.
COPY vendor/hermes-agent/ /opt/hermes/

COPY --chown=insight:insight backend/ .
COPY --chown=insight:insight services/insight-agent/ ./agent_knowledge/

USER insight

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/system/health/live', timeout=3)" || exit 1

ENTRYPOINT []
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
