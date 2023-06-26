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
        apps = [a for a in apps if a != 'sdc_manager']
        apps.insert(0, 'daphne')
        apps.append('channels')
        apps.append('sdc_tools')

        new_val = "VERSION=0.0\n\nINSTALLED_APPS = [\n%s'%s',\n%s#'sdc_user'\n]" % (
        options.SEP, ("',\n%s'" % options.SEP).join(
            apps), options.SEP)
        sep = str(options.SEP)
        pre_add = '\n'.join(["if not DEBUG:",
               sep + "ALLOWED_HOSTS = os.environ.get('ALLOWED_HOST').split(',')",
               sep + "PORT = os.environ.get('PORT') or ''",
               sep + "PORT = PORT.strip(':')",
               sep + "if PORT == '80':",
               (sep * 2) + "PORT = ''",
               sep + "else:",
               (sep * 2) + "PORT = ':%s' % PORT",
               sep + "CSRF_TRUSTED_ORIGINS = ['http://%s%s' % (x, PORT) for x in os.environ.get('ALLOWED_HOST').split(',')] + ['https://%s%s' % (x, PORT) for x in os.environ.get('ALLOWED_HOST').split(',')]",
               "else:",
               sep + "ALLOWED_HOSTS = ['*']"])
        new_val =  "%s\n\n%s\n\nif DEBUG:\n%sINSTALLED_APPS += ['sdc_manager']" % (pre_add, new_val, sep)
        new_val += "\n\nINTERNAL_IPS = (\n%s'127.0.0.1',\n)\n" % (options.SEP)
        new_val += "\n\n# AUTH_USER_MODEL = 'sdc_user.CustomUser'"

        fin = open(self.get_settings_file_path(), "rt", encoding='utf-8')

        data = fin.read()
        fin.close()
        data = re.sub(r'(from[^\n]*)', '\g<1>\nimport os', data)
        data = re.sub(r'(ALLOWED_HOSTS[^\n]*)', '# \g<1>', data)
        data = re.sub(r'INSTALLED_APPS\s*=\s*\[[^\]]+\]', new_val, data)

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

    def get_main_url_path(self):
        return os.path.join(options.PROJECT_ROOT, self.get_setting_vals().ROOT_URLCONF.replace(".", "/") + ".py")

    def find_and_set_project_name(self):
        options.setPROJECT(self.get_setting_vals().ROOT_URLCONF.split(".")[0])
        print(options.PROJECT)
