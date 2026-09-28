# dump_per_model.py
import json
from pathlib import Path
import errno
import subprocess
import sys
import os
from django.utils import timezone
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from django.core import serializers
from django.db import connection
from django.test.utils import override_settings
from django.core.management import call_command
from sdc_core.management.commands.init_add import settings_manager
from django.db.utils import OperationalError


def update_to_sdc_user(backup_directory: str | Path):
    manage_py_file_path = sys.argv[0] if len(sys.argv) > 0 else 'manage.py'
    sdc_settings = settings_manager.SettingsManager(manage_py_file_path)
    settings_path = Path(sdc_settings.get_settings_file_path())
    settings_import_path = sdc_settings.get_settings_import_path()
    new_settings_import_path =  f"{'.'.join(settings_import_path.split('.')[:-1])}.temp_setting"
    settings_new_path = settings_path.parent / 'temp_setting.py'
    try:
        backup_directory = Path(backup_directory)
        with open(settings_new_path, 'w+') as f:
            f.write(f'from {settings_import_path} import *\n\ndel AUTH_USER_MODEL')

        cmd_prefix = f'DJANGO_SETTINGS_MODULE="{new_settings_import_path}" {sys.executable} ./manage.py'
        cmds = ['migrate', f'sdc_db_tools -b -p "{backup_directory.absolute()}"']
        for cmd in cmds:
            p = subprocess.Popen(f'{cmd_prefix} {cmd}', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd=os.getcwd())
            res = p.communicate()
            if p.returncode != 0:
                raise ChildProcessError(res[1].decode('utf8'))
    except ChildProcessError as e:
        print(e.__str__())
        return
    finally:
        settings_new_path.unlink()

    fp_user_json = backup_directory / "auth__User.json"
    if fp_user_json.exists():
        with fp_user_json.open() as f:
            users = json.load(f)
        for elm in users:
            elm['model'] = 'sdc_user.sdcuser'
        with fp_user_json.open('w') as f:
            json.dump(users, f)

        drop_all_tables();
        call_command("makemigrations")
        call_command("migrate")
        restore_backup(backup_directory)


BACKUP_EXCLUDED_MODELS = ("contenttypes.ContentType", "auth.Permission")


def make_backup(backup_directory: str | Path):
    backup_directory = Path(backup_directory)
    backup_directory.mkdir(parents=True, exist_ok=True)
    if not backup_directory.is_dir():
        raise NotADirectoryError(backup_directory.absolute())
    if any(backup_directory.iterdir()):
        raise OSError(errno.ENOTEMPTY, "Folder is not empty", str(backup_directory.absolute()))
    for model in apps.get_models():
        # Content types and permissions are created by migrate; references to them are
        # written as natural keys, so they stay valid in a new database.
        if f"{model._meta.app_label}.{model.__name__}" in BACKUP_EXCLUDED_MODELS:
            continue
        filename = f"{model._meta.app_label}__{model.__name__}.json"

        qs = model._base_manager.all()
        if not qs.exists():
            continue

        data = serializers.serialize("json", qs, use_natural_foreign_keys=True)

        with open(backup_directory / filename, "w") as f:
            f.write(data)
    return backup_directory


def drop_all_tables():
    with connection.cursor() as cursor:
        tables = connection.introspection.table_names()

    with connection.schema_editor() as schema_editor:
        for table in tables:
            schema_editor.execute(schema_editor.sql_delete_table % {
                "table": schema_editor.quote_name(table)
            })


def restore_backup(backup_directory):
    """
    Loads all ``*.json`` files of a backup with ``loaddata``: all files in one
    transaction, with foreign-key checks deferred until everything is loaded, so
    the order of the files does not matter. Raises an error (and loads nothing)
    if the data is inconsistent.
    """
    backup_directory = Path(backup_directory)
    if not backup_directory.is_dir():
        raise CommandError(f"Backup directory not found: {backup_directory.absolute()}")
    files = sorted(str(file.absolute()) for file in backup_directory.glob("*.json"))
    if not files:
        raise CommandError(f"No backup files (*.json) in {backup_directory.absolute()}")
    call_command("loaddata", *files)


class Command(BaseCommand):
    help = 'Backs up, restores or clears the database, or migrates auth.User to sdc_user.SdcUser.'

    def add_arguments(self, parser):
        parser.add_argument('-p', '--path', type=str, help='Path to write Backup [./backup/<TIMESTAMP>]')
        parser.add_argument('--update_to_sdc_user',
                            action='store_true',
                            help="Update from Djangos auth.User model to SDCs sdc_user.SdcUser")
        parser.add_argument('-c', '--clear',
                            action='store_true',
                            help="Makes a backup and then DROPS all tables of the database")
        parser.add_argument('-b', '--backup',
                            action='store_true',
                            help="If set a (only values) backup will be generated")
        parser.add_argument('-r', '--restore',
                            action='store_true',
                            help="If set the (value) backup in the path will be restored")

    def handle(self, *args, **ops):
        self._is_restore = ops.get('restore', False)
        self._is_backup = ops.get('backup', False)
        self._is_clear = ops.get('clear', False)
        self._update_to_sdc_user = ops.get('update_to_sdc_user', False)

        if self._is_restore + self._is_backup + self._is_clear + self._update_to_sdc_user != 1:
            raise CommandError('Exactly one of -r/--restore, -b/--backup, -c/--clear or --update_to_sdc_user '
                               'must be set.')
        formatted_now = timezone.now().strftime("%Y_%m_%d_%H_%M_%S")
        self._backup_directory = ops.get('path') or f'./backup/{formatted_now}'
        if self._is_restore:
            restore_backup(self._backup_directory)
        elif self._is_backup:
            make_backup(self._backup_directory)
        elif self._is_clear:
            try:
                make_backup(self._backup_directory)
            except OperationalError:
                pass
            drop_all_tables()
        elif self._update_to_sdc_user:
            update_to_sdc_user(self._backup_directory)
