poetry config virtualenvs.create false

if [ ! -f pyproject.toml ]; then
  poetry init --no-interaction --name "SdcTest" --python ">=3.13,<4.0"
fi

if [ ! -f poetry.lock ]; then
  poetry lock
fi
poetry add SimpleDomControl