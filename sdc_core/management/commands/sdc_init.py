import os
import sys

from django.core.management.base import BaseCommand, CommandError

from sdc_core.management.commands.init_add import options, settings_manager
from sdc_core.management.commands.init_add.sdc_core_manager import add_sdc_to_main_urls, copy_apps
from sdc_core.management.commands.init_add.utils import makedirs_if_not_exist, copy, copy_and_prepare, \
    prepare_as_string
from sdc_core.management.commands.sdc_update_links import make_app_links


class Command(BaseCommand):
    help = 'This function inits SDC in your django Project'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **ops):
        manage_py_file_path = sys.argv[0] if len(sys.argv) > 0 else 'manage.py'

        sdc_settings = settings_manager.SettingsManager(manage_py_file_path)
        sdc_settings.check_settings()

        sdc_settings.find_and_set_project_name()
        sdc_settings.find_and_set_whitespace_sep()

        project_app_root = os.path.join(options.PROJECT_ROOT, options.PROJECT)
        main_static = os.path.join(options.PROJECT_ROOT, "Assets")
        main_templates = os.path.join(options.PROJECT_ROOT, "templates")

        if 'sdc_tools' in sdc_settings.get_setting_vals().INSTALLED_APPS:
            raise CommandError("SimpleDomControl has initialized already!", 2)


        sdc_settings.update_settings(prepare_as_string(os.path.join(options.SCRIPT_ROOT, "template_files", "settings_extension.py.txt"), options.REPLACEMENTS))

        makedirs_if_not_exist(main_templates)
        copy_apps()
        copy(os.path.join(options.SCRIPT_ROOT, "template_files", "Assets"), main_static, options.REPLACEMENTS)
        copy(os.path.join(options.SCRIPT_ROOT, "template_files", "templates"), main_templates, options.REPLACEMENTS)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "template_files", "routing.py.txt"),
                         os.path.join(project_app_root, "routing.py"),
                         options.REPLACEMENTS)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "template_files", "package.json"),
                         os.path.join(options.PROJECT_ROOT, "package.json"),
                         options.REPLACEMENTS)

        asgi_file = os.path.join(project_app_root, "asgi.py")
        if os.path.exists(asgi_file):
            os.remove(asgi_file)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "template_files", "asgi.py.txt"),
                         asgi_file,
                         options.REPLACEMENTS)

        add_sdc_to_main_urls(sdc_settings.get_main_url_path())
        make_app_links('sdc_tools')
        make_app_links('sdc_user')
