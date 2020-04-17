import re
import os
import pathlib
import importlib
import sys
from sdc_manager.management.commands.init_add import options
from django.conf import settings


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

    def update_settings(self):
        new_val = "INSTALLED_APPS = [\n%s\'%s\',\n]" % (options.SEP, ("\',\n%s\'" % options.SEP).join(
            self.get_setting_vals().INSTALLED_APPS))

        new_val += "\n\nINTERNAL_IPS = (\n%s'127.0.0.1',\n%s'192.168.1.23',\n)\n" % (options.SEP, options.SEP)

        fin = open(self.get_settings_file_path(), "rt", encoding='utf-8')
        data = fin.read()
        fin.close()
        new_data = re.sub(r'INSTALLED_APPS\s*=\s*\[[^\]]+\]', new_val, data)
        fout = open(self.get_settings_file_path(), "wt", encoding='utf-8')
        fout.write(new_data)
        fout.close()

    def get_apps(self):
        app_list = [options.MAIN_APP_NAME]
        for app_name in self.get_setting_vals().INSTALLED_APPS:
            if os.path.exists(os.path.join(options.PROJECT_ROOT, app_name)) and app_name not in app_list:
                app_list.append(app_name)

        return app_list

    def get_main_url_path(self):
        return os.path.join(options.PROJECT_ROOT, self.get_setting_vals().ROOT_URLCONF.replace(".", "/") + ".py")
