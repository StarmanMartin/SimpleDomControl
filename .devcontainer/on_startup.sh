poetry lock
poetry install --no-root
yarn install

poetry run ./manage.py sdc_update_links