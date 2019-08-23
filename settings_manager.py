import re
import os
import pathlib
import importlib
import sys
import options


class SettingsManager:

    def __init__(self, manage_py_file: str):
        self.manage_py_file_path = os.path.join(options.PROJECT_ROOT, manage_py_file)
        self.settings_file_path = None
        self.setting_vals = None

    def get_settings_file_path(self):
        if self.settings_file_path is not None:
            return self.settings_file_path

        manage_py_file = open(self.manage_py_file_path, "r")
        regexp = re.compile(r'DJANGO_SETTINGS_MODULE')

        for line in manage_py_file.readlines():
            if regexp.search(line):
                options.SEP = re.search(r'[^o]+', line).group(0)

                regexp = re.compile(r'DJANGO_SETTINGS_MODULE[^\w]+([^"\']+)')
                settings_file_path = regexp.search(line).group(1).replace(".", "/") + ".py"
                self.settings_file_path = os.path.join(options.PROJECT_ROOT, settings_file_path)
                return self.settings_file_path

    def get_setting_vals(self):
        if self.setting_vals is not None:
            return self.setting_vals

        sys.path.append(os.path.dirname(self.get_settings_file_path()))

        module_name = pathlib.Path(self.get_settings_file_path()).stem
        self.setting_vals = importlib.import_module(module_name)
        return self.setting_vals

    def override_installed_apps(self):
        new_val = "INSTALLED_APPS = [\n\'%s\',\n]" % ("\',\n%s\'" % options.SEP).join(
            self.get_setting_vals().INSTALLED_APPS)

        new_val += "\nINTERNAL_IPS = (\n%s'127.0.0.1',\n%s'192.168.1.23',\n)\n\n" % (options.SEP, options.SEP)

        fin = open(self.get_settings_file_path(), "rt")
        data = fin.read()
        fin.close()
        new_data = re.sub(r'INSTALLED_APPS\s*=\s*\[[^\]]+\]', new_val, data)
        fout = open(self.get_settings_file_path(), "wt")
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
