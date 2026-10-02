FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models/hf \
    TOKENIZERS_PARALLELISM=false

WORKDIR /srv/backend
COPY requirements.txt requirements-semantic.txt ./
RUN pip install -r requirements.txt
# P2-001: CPU-only torch + sentence-transformers. Model weights are NOT baked in: `python -m app.cli semantic download-model`
# fetches the pinned revision once into the `models` volume (HF_HOME); recommendation runs offline from there.
RUN pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu && pip install -r requirements-semantic.txt
# P5-001A.1: official EGRUL extract parsing (separate layer so the torch layers above stay cached)
COPY requirements-enrichment.txt ./
RUN pip install -r requirements-enrichment.txt

# Code is bind-mounted in development (docker-compose.yml); this copy makes the image usable on its own.
# Organizer CSVs are never copied into the image — they are mounted read-only at /data/raw.
COPY . .
