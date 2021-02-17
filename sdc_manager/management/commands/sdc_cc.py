import os
import sys

from django.core.management.base import BaseCommand

from sdc_manager.management.commands.init_add import options, settings_manager
from sdc_manager.management.commands.init_add.add_controller_manager import AddControllerManager


class Command(BaseCommand):
    help = 'This function creates a new sdc controller and adds the django url parts'


    def add_arguments(self, parser):
        pass

    def handle(self, *args, **ops):
        manage_py_file_path = sys.argv[1] if len(sys.argv) > 2 else 'manage.py'

        sdc_settings = settings_manager.SettingsManager(manage_py_file_path)

        if not sdc_settings.get_setting_vals().TEMPLATES[0]['APP_DIRS']:
            print(options.CMD_COLORS.as_error("simpleDomControl only works if TEMPLATES -> APP_DIRS is ture"))
            exit(1)

        all_apps = sdc_settings.get_apps()

        text = "Enter number to select an django App:"
        for idx in range(1, len(all_apps)):
            text += "\n%d -> %s" % (idx, all_apps[idx])

        idx = 1
        try:
            idx = int(input(text + "\nEnter number: [%d]" % (len(all_apps) - 1)) or (len(all_apps) - 1))
        except Exception as ex:
            print(ex)
            print(options.CMD_COLORS.as_error("Input has to be a number between 1 and %d" % (len(all_apps) - 1)))
            exit(1)

        app_name = all_apps[idx]

        text = "Enter the name of the new controller (use snake_case):"
        controller_name = str(input(text))
        add_sdc_manager = AddControllerManager(app_name, controller_name)
        if len(controller_name) == 0:
            print(options.CMD_COLORS.as_error("Controller name must not be empty!"))
            exit(1)
        elif not add_sdc_manager.check_if_url_is_unique():
            print(options.CMD_COLORS.as_error("%s already exists. Controller name has to be unique!" % controller_name))
            exit(1)


        consumers_path = os.path.join(options.PROJECT_ROOT, options.MAIN_APP_NAME, "consumers.py")
        add_sdc_manager.add_url_to_url_pattern(sdc_settings.get_main_url_path(), consumers_path)
        add_sdc_manager.add_view_class_to_sdc_views()
        add_sdc_manager.prepare_files()
        add_sdc_manager.add_to_organizer()