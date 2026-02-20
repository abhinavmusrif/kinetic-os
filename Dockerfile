FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Optional OCR runtime dependency.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY config ./config
COPY core ./core
COPY cognition ./cognition
COPY llm ./llm
COPY vision ./vision
COPY os_controller ./os_controller
COPY memory ./memory
COPY world_model ./world_model
COPY planner ./planner
COPY executor ./executor
COPY tools ./tools
COPY governance ./governance
COPY ui ./ui
COPY docs ./docs
COPY tests ./tests
COPY CHANGELOG.md ./
COPY .env.example ./

RUN pip install --upgrade pip && pip install -e ".[dev]"

# Runtime directories.
RUN mkdir -p /app/workspace /app/logs

# Non-root execution for safer default container behavior.
RUN useradd -m -u 10001 operator
RUN chown -R operator:operator /app
USER operator

CMD ["ao", "--help"]
