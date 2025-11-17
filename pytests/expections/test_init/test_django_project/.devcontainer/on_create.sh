poetry config virtualenvs.create false

if [ ! -f pyproject.toml ]; then
  poetry init --no-interaction --name "test_django_project" --python ">=3.13,<4.0"
fi