import os
import re
import sys

from django.core.management.base import BaseCommand

from sdc_manager.management.commands.init_add import options, settings_manager
from sdc_manager.management.commands.init_add.add_controller_manager import AddControllerManager


def empty_src_organizer():
    org_file_path = os.path.join(options.PROJECT_ROOT, options.MAIN_APP_NAME, "static", options.MAIN_APP_NAME, "js",
                                 "main.organizer.js")
    empty_src_list(org_file_path)


def empty_src_index():
    org_file_path = os.path.join(options.PROJECT_ROOT, options.MAIN_APP_NAME, "templates", options.MAIN_APP_NAME,
                                 "index.html")
    empty_src_list(org_file_path)


def empty_src_list(file_path):
    fin = open(file_path, 'rt')
    data = ""
    write = True
    for line in fin:
        if 'controller-src-section-end' in line:
            write = True
        if write:
            data += line
        if 'controller-src-section-start' in line:
            write = False


    fin.close()
    fout = open(file_path, 'wt')
    fout.write(data)
    fout.close()


class Command(BaseCommand):
    help = 'This function inits SDC in your django Project'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **ops):
        manage_py_file_path = sys.argv[1] if len(sys.argv) > 2 else 'manage.py'
        settings = settings_manager.SettingsManager(manage_py_file_path)
        all_apps = settings.get_apps()
        empty_src_index()
        empty_src_organizer()
        for app_name in all_apps[1:]:
            sdc_js_dir = os.path.join(options.PROJECT_ROOT, app_name, "static", app_name, "js", "sdc")
            if os.path.exists(sdc_js_dir):
                for file in os.listdir(sdc_js_dir):
                    if file.endswith(".js"):
                        controller_name_sc = file.replace(".js", "")
                        acm = AddControllerManager(app_name, controller_name_sc)
                        acm.add_to_organizer()
