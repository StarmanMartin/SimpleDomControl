import os
import shutil
from pathlib import Path

from django.core.management import BaseCommand
from sdc_core.management.commands.init_add import options
from sdc_core.management.commands.utils import cli_select, multi_cli_select


class Command(BaseCommand):
    help = ("Copies JavaScript files of a library controller (Assets/libs/<app>/controller/<controller>/) to "
            "Assets/overwrite_libs/ with the same path. The build then uses the copy instead of the library file.")

    def handle(self, *args, **opts):
        self.libs_path = os.path.join(options.PROJECT_ROOT, 'Assets', 'libs')
        apps = [a for a in os.listdir(self.libs_path)]
        app = cli_select('Select an App', apps)
        controller_path = os.path.join(self.libs_path , app, 'controller')
        controllers = [a for a in os.listdir(controller_path)]
        controller = cli_select('Select a controller', controllers)


        file_list_path = os.path.join(controller_path, controller)
        # Only JavaScript can be overwritten: library styles are included with relative @use paths
        # in Assets/src/index.style.scss. Override styles by adding rules after those imports.
        files = [a for a in os.listdir(file_list_path) if a.endswith('.js')]

        file_types = multi_cli_select('Filetypes [select with space]', files)
        for file_type in file_types:
            dist = Path(os.path.join(options.PROJECT_ROOT, 'Assets', 'overwrite_libs', app, 'controller', controller,
                                     file_type))
            src = Path(str(os.path.join(file_list_path, file_type)))
            dist.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dist)
            self.stdout.write(f"Copied to {dist}")