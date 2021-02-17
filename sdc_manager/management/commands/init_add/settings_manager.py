import re
import os
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

    def update_settings(self, settings_extension):

        apps = self.get_setting_vals().INSTALLED_APPS
        apps = [a for a in apps if a != 'sdc_manager']

        apps.append('sdc_tools')

        new_val = "VERSION=0.0\n\nINSTALLED_APPS = [\n%s'%s',\n%s#'sdc_user'\n]" % (options.SEP, ("',\n%s'" % options.SEP).join(
            apps),options.SEP)

        new_val += "\n\nINTERNAL_IPS = (\n%s'127.0.0.1',\n%s'192.168.1.23',\n)\n" % (options.SEP, options.SEP)
        new_val += "\n\n# AUTH_USER_MODEL = 'sdc_user.CustomUser'"

        fin = open(self.get_settings_file_path(), "rt", encoding='utf-8')

        data = fin.read()
        fin.close()
        new_data = re.sub(r'INSTALLED_APPS\s*=\s*\[[^\]]+\]', new_val, data)

        new_data += settings_extension

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

    def find_and_set_project_name(self):
        options.setPROJECT(self.get_setting_vals().ROOT_URLCONF.split(".")[0])
        print(options.PROJECT)