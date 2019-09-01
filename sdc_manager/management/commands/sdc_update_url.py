import os
import re
import sys

from django.core.management.base import BaseCommand

from sdc_manager.management.commands.init_add import options, settings_manager
from sdc_manager.management.commands.init_add.add_controller_manager import AddControllerManager


def change_content_url(file_path, app_name, controller_name):
    fin = open(file_path, 'rt')
    data = ""
    app_controller = AddControllerManager(app_name, controller_name)
    new_url_line = '"%s"; //%s' % (app_controller.get_template_url(), app_controller.prepare_tag_name())
    regexp = re.compile(r'(\s+this.)contentUrl *= *.*')
    is_done = False
    for line in fin:
        match = regexp.match(line)
        if not is_done and match:
            line = regexp.sub(r'\1contentUrl = %s' % new_url_line, line)
            is_done = True

        data += line
    fin.close()
    fout = open(file_path, 'wt')
    fout.write(data)
    fout.close()


class Command(BaseCommand):
    help = 'This function updates all content urls of the SDC controller'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **ops):
        manage_py_file_path = sys.argv[1] if len(sys.argv) > 2 else 'manage.py'
        settings = settings_manager.SettingsManager(manage_py_file_path)
        all_apps = settings.get_apps()
        for app_name in all_apps[1:]:
            sdc_js_dir = os.path.join(options.PROJECT_ROOT, app_name, "static", app_name, "js", "sdc")
            if os.path.exists(sdc_js_dir):
                for file in os.listdir(sdc_js_dir):
                    if file.endswith(".js"):
                        controller_file = os.path.join(sdc_js_dir, file)
                        controller_name_sc = file.replace(".js", "")
                        change_content_url(controller_file, app_name, controller_name_sc)
