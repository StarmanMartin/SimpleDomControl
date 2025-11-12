import io
import json
import sys
import re

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from sdc_core.management.commands.init_add import settings_manager
from sdc_core.management.commands.init_add.add_controller_manager import AddControllerManager
from sdc_core.management.commands.init_add.utils import convert_snake_case_to_tag_name
from sdc_core.management.commands.sdc_update_links import make_link
from sdc_core.management.commands.utils import cli_select, multi_cli_select


class Command(BaseCommand):
    help = 'This function creates a new sdc controller and adds the django url parts'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        manage_py_file_path = sys.argv[0] if len(sys.argv) > 0 else 'manage.py'
        self.sdc_settings = settings_manager.SettingsManager(manage_py_file_path)

    def add_arguments(self, parser):
        all_apps = self.sdc_settings.get_apps()
        parser.add_argument('-c', '--controller_name', type=str, help='The name of the new controller as snake_case')
        parser.add_argument('-a', '--app_name', type=str, help='The name of the django app: [%s]' % ', '.join(all_apps))
        parser.add_argument('-m', '--mixin_apps', nargs='?', const=True, default=None, type=str, help=f'Comma-separated list of django app names (empty to avoid user interaction): (e.g. sdc_auto_submit,sdc_update_on_change)] ')

    def check_snake_name(self, name):
        x = re.search("[A-Z]", name)
        if x:
            raise CommandError('Lower case letters only.', 8)
        x = re.search("[^0-9a-z_]", name)
        if x:
            raise CommandError("No special characters. Only lowercase letters, numbers and '_'", 9)
        x = re.search("^[a-z]", name)
        if not x:
            raise CommandError("Only lowercase letters at first symbol", 10)

        return True

    def handle(self, *args, **ops):

        self.sdc_settings.check_settings()

        self.sdc_settings.find_and_set_project_name()
        all_apps = self.sdc_settings.get_apps()
        app_name = ops.get('app_name')
        if app_name is None or not app_name in all_apps:
            app_name = cli_select("Select an django App:", all_apps)

        controller_name = ops.get('controller_name')
        if controller_name is None:
            text = "Enter the name of the new controller (use snake_case):"
            controller_name = str(input(text))

        if not self.check_snake_name(controller_name):
            exit(1)
        mixin_apps = ops.get('mixin_apps')
        print(mixin_apps)
        if mixin_apps is True:
            mixin_apps = []
        else:
            buffer = io.StringIO()
            call_command('sdc_get_controller_infos', stdout=buffer)
            res = buffer.getvalue()
            options = [c['tag_name'] for app_name, apps in json.loads(res)['sdc_controller'].items() for c in apps]
            if mixin_apps is None:
                mixin_apps = multi_cli_select(f"Select mixins {controller_name}", options)
            else:
                mixin_apps = [convert_snake_case_to_tag_name(mixin.strip()) for mixin in mixin_apps.split(',')]
                mixin_apps = [app for app in mixin_apps if app in options]

        add_sdc_core = AddControllerManager(app_name, controller_name, mixin_apps)
        if len(controller_name) == 0:
            raise CommandError("Controller name must not be empty!", 5)
        elif not add_sdc_core.check_if_url_is_unique():
            raise CommandError("%s already exists. Controller name has to be unique!" % controller_name, 6)


        add_sdc_core.add_url_to_url_pattern(self.sdc_settings.get_main_url_path())
        add_sdc_core.add_view_class_to_sdc_views()
        add_sdc_core.prepare_files()
        add_sdc_core.add_to_organizer()
        add_sdc_core.add_js_test()
        make_link(app_name, controller_name)