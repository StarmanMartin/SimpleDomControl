import os
import sys
import re

from django.core.management.base import BaseCommand

from sdc_core.management.commands.init_add import options, settings_manager
from sdc_core.management.commands.init_add.add_controller_manager import AddControllerManager
from sdc_core.management.commands.sdc_link_html import make_link


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


    def check_snake_name(self, name):
        x = re.search("[A-Z]", name)
        if x:
            print(options.CMD_COLORS.as_error("Lower case letters only."))
            return False
        x = re.search("[^0-9a-z_]", name)
        if x:
            print(options.CMD_COLORS.as_error("No special characters. Only lowercase letters, numbers and '_'"))
            return False
        x = re.search("^[a-z]", name)
        if not x:
            print(options.CMD_COLORS.as_error("Only lowercase letters at first symbol"))
            return False

        return True

    def handle(self, *args, **ops):

        self.sdc_settings.check_settings()

        self.sdc_settings.find_and_set_project_name()
        all_apps = self.sdc_settings.get_apps()

        text = "Enter number to select an django App:"
        for idx in range(1, len(all_apps)):
            text += "\n%d -> %s" % (idx, all_apps[idx])
        app_name = ops.get('app_name')
        if app_name is None or not app_name in all_apps:
            idx = 1
            try:
                idx = int(input(text + "\nEnter number: [%d]" % (len(all_apps) - 1)) or (len(all_apps) - 1))
            except Exception as ex:
                print(ex)
                print(options.CMD_COLORS.as_error("Input has to be a number between 1 and %d" % (len(all_apps) - 1)))
                exit(1)

            app_name = all_apps[idx]
        controller_name = ops.get('controller_name')
        if controller_name is None:
            text = "Enter the name of the new controller (use snake_case):"
            controller_name = str(input(text))

        if not self.check_snake_name(controller_name):
            exit(1)

        add_sdc_core = AddControllerManager(app_name, controller_name)
        if len(controller_name) == 0:
            print(options.CMD_COLORS.as_error("Controller name must not be empty!"))
            exit(1)
        elif not add_sdc_core.check_if_url_is_unique():
            print(options.CMD_COLORS.as_error("%s already exists. Controller name has to be unique!" % controller_name))
            exit(1)


        add_sdc_core.add_url_to_url_pattern(self.sdc_settings.get_main_url_path())
        add_sdc_core.add_view_class_to_sdc_views()
        add_sdc_core.prepare_files()
        add_sdc_core.add_to_organizer()
        make_link(app_name, controller_name)