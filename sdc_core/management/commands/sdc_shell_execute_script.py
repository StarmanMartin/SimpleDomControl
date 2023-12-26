import os

from django.core.management import BaseCommand, CommandError
from django.db import connections, transaction


class Command(BaseCommand):
    help = 'Execute a python script in the Django environment.'
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument('-s', '--script', type=str, help='The path to the executable python script.')

    def switch_default_database(self, database_alias):
        # Check if the specified database alias exists in DATABASES
        if database_alias in connections.databases:
            # Set the specified database as the default
            transaction.commit()

            connections.databases['default'] = connections.databases[database_alias]
            transaction.commit()

        else:
            raise CommandError(f"Database alias '{database_alias}' does not exist in DATABASES.")

    def handle(self, *args, **ops):
        script_path = ops.get('script')

        if os.path.exists(script_path):
            try:
                exec(open(script_path, 'r').read())
            except Exception as e:
                raise CommandError(f'{e}', 3)
        else:
            raise CommandError(f'"{script_path}" does not exist!', 2)