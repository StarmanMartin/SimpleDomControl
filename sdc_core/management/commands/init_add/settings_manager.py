import importlib
import re
import os

import regex
from django.core.management import CommandError

from sdc_core.management.commands.init_add import options
from django.conf import settings

def get_app_path(app_name):
    try:
        app_module = importlib.import_module(app_name)
        return os.path.dirname(app_module.__file__)
    except:
        raise CommandError(f"{app_name} is not an installed app")


class SettingsManager:

    def __init__(self, manage_py_file: str):
        self.manage_py_file_path = os.path.join(options.PROJECT_ROOT, manage_py_file)
        self.settings_file_path = None
        self.setting_vals = None

    def get_settings_file_path(self):
        if self.settings_file_path is not None:
            return self.settings_file_path

        settings_file_path = os.environ.get('DJANGO_SETTINGS_MODULE').replace(".", "/") + ".py"
        self.settings_file_path = os.path.join(options.PROJECT_ROOT, settings_file_path)
        return self.settings_file_path

    def find_and_set_whitespace_sep(self):
        manage_py_file = open(self.manage_py_file_path, "r", encoding='utf-8')
        regexp = re.compile(r'DJANGO_SETTINGS_MODULE')

        for line in manage_py_file.readlines():
            if regexp.search(line):
                options.SEP = re.search(r'[^o]+', line).group(0)

    def get_setting_vals(self):
        return settings

    def check_settings(self):
        if not self.get_setting_vals().TEMPLATES[0]['APP_DIRS']:
            print(options.CMD_COLORS.as_error("SDC only works if TEMPLATES -> APP_DIRS is ture"))
            exit(1)
        temp_dir = self.get_setting_vals().BASE_DIR / 'templates'
        if not temp_dir in self.get_setting_vals().TEMPLATES[0]['DIRS']:
            print(options.CMD_COLORS.as_error("SDC only works if '%s' is in  TEMPLATES -> DIRS" % temp_dir))
            exit(1)

    def update_settings(self, settings_extension):
        settings_path = self.get_settings_file_path()
        settings_dir = os.path.dirname(settings_path)
        base_settingd_path = os.path.join(settings_dir, 'base_settings.py')
        if not os.path.exists(base_settingd_path):
            os.rename(settings_path, base_settingd_path)

        with open(self.get_settings_file_path(), "w+", encoding='utf-8') as fout:
            fout.write(settings_extension)

    def get_apps(self):
        self.find_and_set_project_name()
        app_list = [options.MAIN_APP_NAME]
        for app_name in self.get_setting_vals().INSTALLED_APPS:
            if os.path.exists(os.path.join(options.PROJECT_ROOT, app_name)) and app_name not in app_list:
                app_list.append(app_name)

        return app_list

    def get_sdc_apps(self):
        self.find_and_set_project_name()
        app_list = []
        for app_name in self.get_setting_vals().INSTALLED_APPS:
            if os.path.exists(os.path.join(get_app_path(app_name), 'sdc_views.py')):
                app_list.append(app_name)

        return app_list





    def get_main_url_path(self):
        return os.path.join(options.PROJECT_ROOT, self.get_setting_vals().ROOT_URLCONF.replace(".", "/") + ".py")

    def find_and_set_project_name(self):
        options.setPROJECT(self.get_setting_vals().ROOT_URLCONF.split(".")[0])

    @classmethod
    def balanced_pattern_factory(cls, prefix: str,  icon_start: str = r"\{", icon_end: str = r"\}") -> regex.regex:
        return regex.compile(fr'{prefix}({icon_start}(?:[^{icon_start}{icon_end}]+|(?1))*{icon_end})')
