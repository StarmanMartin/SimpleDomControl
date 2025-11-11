poetry config virtualenvs.create false
poetry install --no-root
poetry run pip install -e /workspace/SimpleDomControl
yarn install

poetry run ./manage.py sdc_update_links