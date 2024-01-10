# We use Python 3 in our project
FROM python:3.10

ENV NODE_VERSION=18.18.0
RUN apt install -y curl
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
ENV NVM_DIR=/root/.nvm
RUN . "$NVM_DIR/nvm.sh" && nvm install ${NODE_VERSION}
RUN . "$NVM_DIR/nvm.sh" && nvm use v${NODE_VERSION}
RUN . "$NVM_DIR/nvm.sh" && nvm alias default v${NODE_VERSION}
ENV PATH="/root/.nvm/versions/node/v${NODE_VERSION}/bin/:${PATH}"
RUN node --version
RUN npm --version

WORKDIR /usr/src/app

ENV POETRY_VERSION=1.5.1

# System deps:
RUN pip install --upgrade pip
RUN pip install "poetry==$POETRY_VERSION"

# Copy only requirements to cache them in docker layer

COPY poetry.lock pyproject.toml package.json ./

# Project initialization:
RUN poetry config virtualenvs.create false
RUN poetry export -o ./requirements.txt --without-hashes --with dev
RUN pip install --no-cache-dir -r ./requirements.txt

RUN npm install

