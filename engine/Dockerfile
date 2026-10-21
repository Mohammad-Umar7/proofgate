# ProofGate engine: FastAPI server + pipeline. Build from the repo root:
#   docker build -f engine/Dockerfile -t proofgate-engine .
FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY engine/pyproject.toml engine/
COPY engine/proofgate engine/proofgate
RUN pip install --no-cache-dir -e ./engine
COPY bench bench

ENV PG_CACHE_DIR=/data \
    PG_SANDBOX=off \
    HOST=0.0.0.0 \
    PORT=8000
VOLUME /data
EXPOSE 8000

# First start clones the project's full history into /data (about 140 MB for curl).
CMD ["sh", "-c", "python -c 'from proofgate.repo import get_repo; get_repo()' && proofgate serve"]
