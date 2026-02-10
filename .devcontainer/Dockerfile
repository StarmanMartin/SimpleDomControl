# ===== Base image with Python 3.13 =====
FROM python:3.13-slim

# ===== Install Node.js (LTS) =====
# You can pin a specific version by changing "setup_20.x" to "setup_22.x" or similar
RUN apt-get update &&  \
    apt-get install -y curl git build-essential python3-dev && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs sqlite3 libsqlite3-dev && \
    apt-get install -y --no-install-recommends \
    sudo git nano \
    g++ libmagic1


RUN corepack enable
RUN corepack prepare yarn@stable --activate

ARG USERNAME=dev
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
  && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# ===== Install Poetry =====
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python3 -


USER $USERNAME
RUN mkdir /home/$USERNAME/SdcTest
WORKDIR /home/$USERNAME/SdcTest


# ===== Create workspace and non-root user =====

RUN poetry config virtualenvs.create false
