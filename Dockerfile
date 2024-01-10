# We use Python 3 in our project
FROM python:3.10
WORKDIR /usr/src/app

ENV POETRY_VERSION=1.5.1

# System deps:
RUN pip install --upgrade pip
RUN pip install "poetry==$POETRY_VERSION"

# Copy only requirements to cache them in docker layer

COPY poetry.lock pyproject.toml ./

# Project initialization:
RUN poetry config virtualenvs.create false
RUN poetry export -o ./requirements.txt --without-hashes
RUN pip install --no-cache-dir -r ./requirements.txt

