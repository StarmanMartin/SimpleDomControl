import os
import sys
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.core import serializers
from django.utils import timezone
from sdc_core.management.commands.init_add import options, settings_manager
from sdc_core.management.commands.init_add.add_controller_manager import AddControllerManager
from sdc_core.management.commands.init_add.sdc_core_manager import add_sdc_to_main_urls
from sdc_core.management.commands.init_add.utils import copy, copy_and_prepare, prepare_as_string
from sdc_core.management.commands.sdc_update_links import make_app_links
from sdc_core.management.commands.sdc_db_tools import update_to_sdc_user


class Command(BaseCommand):
    help = 'This function inits SDC in your django Project'

    def add_arguments(self, parser):
        parser.add_argument('-u', '--update', action='store_true',
                            help='The name of the new controller as snake_case')
        parser.add_argument('-y', '--assume-yes',
                            action='store_true',
                            help="Automatically assume 'yes' for all prompts.")
        parser.add_argument('-n', '--assume-no',
                            action='store_true',
                            help="Automatically assume 'no' for all prompts.")

    def _yes_no_prompt(self, question: str) -> bool:
        self.stdout.write(f"{question} (y/n) [default=n]")
        if self._assume_yes:
            return True
        if self._assume_no:
            return False

        # Get user input
        while True:
            answer = input().strip().lower()
            if answer in ["yes", "y"]:
                return True
            elif answer in ["no", "n", ""]:
                return False
            else:
                self.stdout.write("Invalid input. Please enter 'yes' or 'no'.")

    def handle(self, *args, **ops):
        manage_py_file_path = sys.argv[0] if len(sys.argv) > 0 else 'manage.py'
        update = ops.get('update', False)
        self._assume_yes = ops.get('assume_yes', False)
        self._assume_no = ops.get('assume_no', False)

        sdc_settings = settings_manager.SettingsManager(manage_py_file_path)
        # sdc_settings.check_settings()

        sdc_settings.find_and_set_project_name()
        sdc_settings.find_and_set_whitespace_sep()

        project_app_root = os.path.join(options.PROJECT_ROOT, options.PROJECT)
        main_static = os.path.join(options.PROJECT_ROOT, "Assets")
        dev_container = os.path.join(options.PROJECT_ROOT, ".devcontainer")
        main_templates = os.path.join(options.PROJECT_ROOT, "templates")
        formatted_now = timezone.now().strftime("%Y_%m_%d_%H_%M_%S")
        backup_directory = Path(f'./backup/{formatted_now}')

        if 'sdc_tools' in sdc_settings.get_setting_vals().INSTALLED_APPS:
            if not update:
                raise CommandError("SimpleDomControl has initialized already! run sdc_init -u", 2)
        else:
            update = False
        sdc_settings.update_settings()

        os.makedirs(main_templates, exist_ok=True)

        copy(os.path.join(options.SCRIPT_ROOT, "template_files", "settings_extension.py.txt"),
                          sdc_settings.get_settings_file_path(),
                          options.REPLACEMENTS, self._yes_no_prompt)

        copy(os.path.join(options.SCRIPT_ROOT, "template_files", ".devcontainer"), dev_container, options.REPLACEMENTS,
             self._yes_no_prompt)
        copy(os.path.join(options.SCRIPT_ROOT, "template_files", "Assets"), main_static, options.REPLACEMENTS,
             self._yes_no_prompt)
        copy(os.path.join(options.SCRIPT_ROOT, "template_files", "templates"), main_templates, options.REPLACEMENTS,
             self._yes_no_prompt)
        os.makedirs(os.path.join(main_static, 'static'), exist_ok=True)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "template_files", "routing.py.txt"),
                         os.path.join(project_app_root, "routing.py"),
                         options.REPLACEMENTS, self._yes_no_prompt)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "template_files", "package.json"),
                         os.path.join(options.PROJECT_ROOT, "package.json"),
                         options.REPLACEMENTS, self._yes_no_prompt)

        asgi_file = os.path.join(project_app_root, "asgi.py")
        if os.path.exists(asgi_file):
            os.remove(asgi_file)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "template_files", "asgi.py.txt"),
                         asgi_file,
                         options.REPLACEMENTS, self._yes_no_prompt)

        if not update:
            add_sdc_to_main_urls(sdc_settings.get_main_url_path())
        else:
            for sdc_app in sdc_settings.get_sdc_apps():
                AddControllerManager.add_js_app_to_organizer(sdc_app)
                AddControllerManager.add_css_app_to_organizer(sdc_app)

        make_app_links('sdc_tools')
        make_app_links('sdc_user')


