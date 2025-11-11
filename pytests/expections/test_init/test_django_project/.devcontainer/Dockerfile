# ===== Base image with Python 3.13 =====
FROM python:3.13-slim

# ===== Install Node.js (LTS) =====
# You can pin a specific version by changing "setup_20.x" to "setup_22.x" or similar
RUN apt-get update &&  \
    apt-get install -y curl git build-essential && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    apt-get install -y --no-install-recommends \
    sudo git nano \
    g++ libmagic1



# ===== Install Poetry =====
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python3 -
RUN npm install -g yarn

# ===== Create workspace and non-root user =====
RUN corepack enable
RUN poetry config virtualenvs.create false


WORKDIR /workspace/app



# ===== Copy dependency files =====
COPY pyproject.toml poetry.lock* package*.json* ./

# ===== Preinstall dependencies if available =====
RUN poetry install --no-root || true
# RUN npm install -g yarn
RUN if [ -f "package.json" ]; then yarn install; fi
