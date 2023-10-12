import sys

from django.core.management.base import BaseCommand, CommandError

from sdc_core.management.commands.init_add import settings_manager


class Command(BaseCommand):
    help = 'This function checks if sdc is already installed'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **ops):
        manage_py_file_path = sys.argv[0] if len(sys.argv) > 0 else 'manage.py'

        sdc_settings = settings_manager.SettingsManager(manage_py_file_path)

        if 'sdc_tools' not in sdc_settings.get_setting_vals().INSTALLED_APPS:
            raise CommandError('Sdc is not installed: run sdc_init', 3)

        self.stdout.write(self.style.SUCCESS('SDC is installed!'))
