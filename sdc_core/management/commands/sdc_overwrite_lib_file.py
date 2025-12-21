import os
import shutil
from pathlib import Path

from django.core.management import BaseCommand
from sdc_core.management.commands.init_add import options
from sdc_core.management.commands.utils import cli_select, multi_cli_select


class Command(BaseCommand):
    def handle(self, *args, **opts):
        self.libs_path = os.path.join(options.PROJECT_ROOT, 'Assets', 'libs')
        apps = [a for a in os.listdir(self.libs_path)]
        app = cli_select('Select an App', apps)
        controller_path = os.path.join(self.libs_path , app, 'controller')
        controllers = [a for a in os.listdir(controller_path)]
        controller = cli_select('Select a controller', controllers)


        file_list_path = os.path.join(controller_path, controller)
        files = [a for a in os.listdir(file_list_path) if a.endswith('.js') or a.endswith('.scss')]

        file_types = multi_cli_select('Filetypes [select with space]', files)
        for file_type in file_types:
            dist = Path(str(os.path.join(options.PROJECT_ROOT, 'Assets', 'overwrite_libs', app, 'controller', file_type)))
            src = Path(str(os.path.join(file_list_path, file_type)))
            dist.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dist)