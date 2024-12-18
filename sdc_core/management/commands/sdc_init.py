import os
import sys

from django.core.management.base import BaseCommand, CommandError

from sdc_core.management.commands.init_add import options, settings_manager
from sdc_core.management.commands.init_add.add_controller_manager import AddControllerManager
from sdc_core.management.commands.init_add.sdc_core_manager import add_sdc_to_main_urls
from sdc_core.management.commands.init_add.utils import copy, copy_and_prepare, prepare_as_string
from sdc_core.management.commands.sdc_update_links import make_app_links


class Command(BaseCommand):
    help = 'This function inits SDC in your django Project'

    def add_arguments(self, parser):
        parser.add_argument('-u', '--update', action='store_true',
                            help='The name of the new controller as snake_case')
        parser.add_argument('-y', '--assume-yes',
                            action='store_true',
                            help="Automatically assume 'yes' for all prompts.")

    def _yes_no_prompt(self, question: str) -> bool:
        self.stdout.write(f"{question} (y/n) [default=y]")
        if self._assume_yes:
            return True

        # Get user input
        while True:
            answer = input().strip().lower()
            if answer in ["yes", "y"]:
                return True
            elif answer in ["no", "n"]:
                return False
            else:
                self.stdout.write("Invalid input. Please enter 'yes' or 'no'.")

    def handle(self, *args, **ops):
        manage_py_file_path = sys.argv[0] if len(sys.argv) > 0 else 'manage.py'
        update = ops.get('update', False)
        self._assume_yes = ops.get('assume_yes', False)

        sdc_settings = settings_manager.SettingsManager(manage_py_file_path)
        sdc_settings.check_settings()

        sdc_settings.find_and_set_project_name()
        sdc_settings.find_and_set_whitespace_sep()

        project_app_root = os.path.join(options.PROJECT_ROOT, options.PROJECT)
        main_static = os.path.join(options.PROJECT_ROOT, "Assets")
        main_templates = os.path.join(options.PROJECT_ROOT, "templates")

        if 'sdc_tools' in sdc_settings.get_setting_vals().INSTALLED_APPS:
            if not update:
                raise CommandError("SimpleDomControl has initialized already! run sdc_init -u", 2)
        else:
            update = False
        sdc_settings.update_settings(
            prepare_as_string(os.path.join(options.SCRIPT_ROOT, "template_files", "settings_extension.py.txt"),
                              options.REPLACEMENTS))

        os.makedirs(main_templates, exist_ok=True)
        copy(os.path.join(options.SCRIPT_ROOT, "template_files", "Assets"), main_static, options.REPLACEMENTS,
             self._yes_no_prompt)
        copy(os.path.join(options.SCRIPT_ROOT, "template_files", "templates"), main_templates, options.REPLACEMENTS,
             self._yes_no_prompt)

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

