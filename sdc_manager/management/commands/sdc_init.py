import os
import sys

from django.core.management.base import BaseCommand

from sdc_manager.management.commands.init_add import options, settings_manager
from sdc_manager.management.commands.init_add.sdc_core_manager import add_sdc_core, clean_up, add_sdc_to_main_urls
from sdc_manager.management.commands.init_add.utils import makedirs_if_not_exist, copy, copy_and_prepare


class Command(BaseCommand):
    help = 'This function inits SDC in your django Project'


    def add_arguments(self, parser):
        pass

    def handle(self, *args, **ops):
        manage_py_file_path = sys.argv[1] if len(sys.argv) > 2 else 'manage.py'

        sdc_settings = settings_manager.SettingsManager(manage_py_file_path)

        if not sdc_settings.get_setting_vals().TEMPLATES[0]['APP_DIRS']:
            print(options.CMD_COLORS.as_error("simpleDomControl only works if TEMPLATES -> APP_DIRS is ture"))
            exit(1)

        sdc_settings.find_and_set_whitespace_sep()
        main_static = os.path.join(options.PROJECT_ROOT, options.MAIN_APP_NAME, "static")
        main_templates = os.path.join(options.PROJECT_ROOT, options.MAIN_APP_NAME, "templates")

        sdc_dir = os.path.join(main_static, "simpleDomControl")
        if os.path.exists(sdc_dir):
            print(options.CMD_COLORS.as_error("SimpleDomControl has init already!"))
            exit(2)

        add_sdc_core()
        clean_up()

        sdc_settings.get_setting_vals().INSTALLED_APPS.append(options.MAIN_APP_NAME)
        sdc_settings.update_settings()

        makedirs_if_not_exist(main_static)
        makedirs_if_not_exist(main_templates)
        copy(os.path.join(options.SCRIPT_ROOT, "templates", "static", "simpleDomControl"), sdc_dir)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", ".bowerrc"),
                         os.path.join(options.PROJECT_ROOT, ".bowerrc"),
                         options.REPLACEMENTS)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", ".jshintrc"),
                         os.path.join(options.PROJECT_ROOT, ".jshintrc"),
                         options.REPLACEMENTS)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "static", "main.organizer.js"),
                         os.path.join(main_static, options.MAIN_APP_NAME, "js", "main.organizer.js"),
                         options.REPLACEMENTS)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "static", "style.css"),
                         os.path.join(main_static, options.MAIN_APP_NAME, "css", "style.css"),
                         options.REPLACEMENTS)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "templates", "base.html"),
                         os.path.join(main_templates, "base.html"),
                         options.REPLACEMENTS)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "templates", "index.html"),
                         os.path.join(main_templates, options.MAIN_APP_NAME, "index.html"),
                         options.REPLACEMENTS)

        add_sdc_to_main_urls(sdc_settings.get_main_url_path())