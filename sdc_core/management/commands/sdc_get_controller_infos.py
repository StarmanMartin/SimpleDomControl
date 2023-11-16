import importlib
import json
import os
import sys

from django.core.management.base import BaseCommand, CommandError

from sdc_core.management.commands.init_add import options, settings_manager
from sdc_core.management.commands.init_add.add_controller_manager import AddControllerManager
from sdc_core.management.commands.init_add.utils import convert_to_camel_case


class Command(BaseCommand):
    help = 'This function returns all infos to all models'
    src_path = ''

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        manage_py_file_path = sys.argv[0] if len(sys.argv) > 0 else 'manage.py'
        self.sdc_settings = settings_manager.SettingsManager(manage_py_file_path).get_setting_vals()

    def add_arguments(self, parser):
        pass

    def _get_class_line_number(self, file_path, class_name):
        line_number = None
        class_name = list(class_name)
        class_name[0] = class_name[0].capitalize()
        class_name = ''.join(class_name)
        with open(file_path, 'r') as file:
            for i, line in enumerate(file, start=1):
                # Check if the line contains the class definition
                if f"class {class_name}(" in line:
                    return i

        return line_number

    def _parse_controller_to_info_json(self, app_name, controller_name):
        controller_asset_dir = os.path.join(self.src_path, app_name, 'controller', controller_name)
        app = importlib.import_module(app_name)
        app_path = os.path.dirname(app.__file__)
        app_view_path = os.path.join(app_path, 'sdc_views.py')
        app_asset_path = os.path.join(app_path, 'Assets/src', app_name, 'controller')
        app_template_path = os.path.join(app_path, 'templates', app_name, 'sdc')

        view_class_name = convert_to_camel_case(controller_name)

        info =  {
            'name': controller_name,
            'controller_asset_dir': app_asset_path,
            'sdc_view_file': app_view_path,
            'sdc_view_file_number': self._get_class_line_number(app_view_path, view_class_name),
            'url': AddControllerManager.get_url(controller_name),
        }

        for extention in ['js', 'scss']:
            file = os.path.join(app_asset_path, controller_name, controller_name + '.' + extention)
            if os.path.isfile(file):
                info[extention] = file

        file = os.path.join(app_template_path, controller_name + '.html')
        if os.path.isfile(file):
            info['html'] = file

        return info

    def handle(self, *args, **ops):
        self.src_path = os.path.join(options.PROJECT_ROOT, 'Assets', 'src')
        controller_results = {'sdc_controller': {}}
        if(not os.path.exists(self.src_path)):
            raise CommandError('SDC not installed: Assets/src not found', 3)

        for app_name in os.listdir(self.src_path):
            app_asset_dir = os.path.join(self.src_path, app_name, 'controller')
            if os.path.isdir(app_asset_dir) and app_name in self.sdc_settings.INSTALLED_APPS:
                app_controllers = []
                controller_results['sdc_controller'][app_name] = (app_controllers)
                for controller_name in os.listdir(app_asset_dir):
                    controller_asset_dir = os.path.join(app_asset_dir, controller_name)
                    if os.path.isdir(controller_asset_dir):
                        info_json = self._parse_controller_to_info_json(app_name, controller_name)
                        if info_json is not None:
                            app_controllers.append(info_json)




        self.stdout.write(json.dumps(controller_results, indent=1))
