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

        apps = self.get_setting_vals().INSTALLED_APPS
        apps = [a for a in apps if a != 'sdc_core']
        apps.insert(0, 'daphne')
        apps.append('channels')
        apps.append('sdc_tools')
        apps.append('sdc_user')
        apps.append('sdc_core')
        sep = str(options.SEP)

        new_val = f"VERSION=0.0\n\nINSTALLED_APPS = [\n{sep}'%s'\n]" % (("',\n%s'" % sep).join(apps))
        pre_add = '\n'.join(["if not DEBUG:",
                             sep + "hosts = [urlparse(x)  for x in os.environ.get('ALLOWED_HOST').split(',')]",
                             sep + "ALLOWED_HOSTS = [host.hostname for host in hosts]",
                             sep + "CSRF_TRUSTED_ORIGINS = [urlunparse(x) for x in hosts]",
                             "else:",
                             sep + "ALLOWED_HOSTS = ['*']"])

        new_val = f"{pre_add}\n\n{new_val}"
        new_val += "\n\nINTERNAL_IPS = (\n%s'127.0.0.1',\n)\n" % (options.SEP)

        fin = open(self.get_settings_file_path(), "rt", encoding='utf-8')

        data = fin.read()
        fin.close()
        data = re.sub(r'(from[^\n]*)', r'\g<1>\nimport os\nfrom urllib.parse import urlparse, urlunparse', data)
        data = re.sub(r'(ALLOWED_HOSTS[^\n]*)', r'# \g<1>', data)
        data = re.sub(r'INSTALLED_APPS\s*=\s*\[[^\]]+\]', new_val, data)

        new_val = f"DATABASES_AVAILABLE = {{\n{sep}'jest': {{'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'test_db.sqlite3', }},"
        data = re.sub(r'DATABASES\s*=\s*\{', new_val, data)
        db_pattern = self.balanced_pattern_factory('DATABASES_AVAILABLE = ')
        db_settings = db_pattern.search(data).group()
        data = db_pattern.sub(db_settings + f"\n\ndatabase = os.environ.get('DJANGO_DATABASE', 'default')\n\nDATABASES = {{'default': DATABASES_AVAILABLE[database]}}", data)

        data += settings_extension

        fout = open(self.get_settings_file_path(), "wt", encoding='utf-8')
        fout.write(data)
        fout.close()

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
        print(options.PROJECT)

    @classmethod
    def balanced_pattern_factory(cls, prefix: str,  icon_start: str = r"\{", icon_end: str = r"\}") -> regex.regex:
        return regex.compile(fr'{prefix}({icon_start}(?:[^{icon_start}{icon_end}]+|(?1))*{icon_end})')
