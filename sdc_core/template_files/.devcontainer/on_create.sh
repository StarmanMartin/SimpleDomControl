poetry config virtualenvs.create false

if [ ! -f pyproject.toml ]; then
  poetry init --no-interaction --name "§PROJECT§" --python ">=3.13,<4.0"
fi