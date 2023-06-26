import os
import re
import sys

from django.core.management.base import BaseCommand

from sdc_manager.management.commands.init_add import options, settings_manager
from sdc_manager.management.commands.init_add.add_controller_manager import AddControllerManager
from django.apps import apps

def relative_symlink(src, dst):
    dir = os.path.dirname(dst)
    Src = os.path.relpath(src, dir)
    Dst = os.path.join(dir, os.path.basename(src))
    return os.symlink(Src, Dst)
def make_link(app_name, controller_name):
    sdc_controller_list_dir = os.path.join(options.PROJECT_ROOT, "Assets/src", app_name, "controller")
    if os.path.exists(sdc_controller_list_dir):
        sdc_c_dir = os.path.join(sdc_controller_list_dir, controller_name)
        sdc_c_js = os.path.join(sdc_c_dir, "%s.js" % controller_name)
        if os.path.isdir(sdc_c_dir) and os.path.isfile(sdc_c_js):
            sdc_c_html = os.path.join(options.PROJECT_ROOT, app_name, "templates", app_name, 'sdc', "%s.html" % controller_name)
            if os.path.isfile(sdc_c_html):
                sdc_link_path = os.path.join(sdc_c_dir, "%s.html" % controller_name)
                if os.path.exists(sdc_link_path):
                    os.remove(sdc_link_path)
                relative_symlink(sdc_c_html, sdc_link_path)
def make_model_link(app_name, model_name):
    sdc_dst_dir = os.path.join(options.PROJECT_ROOT, "Assets/src", app_name, "models", model_name)
    sdc_src_dir = os.path.join(options.PROJECT_ROOT, app_name, "templates", app_name, 'models', model_name)
    if not os.path.exists(sdc_dst_dir):
        os.makedirs(sdc_dst_dir)
    if os.path.exists(sdc_src_dir):
        for file in os.listdir(sdc_src_dir):
            sdc_src_file = os.path.join(sdc_src_dir, file)
            sdc_dst_file = os.path.join(sdc_dst_dir, file)
            if os.path.isdir(sdc_dst_dir) and os.path.isfile(sdc_src_file):
                if os.path.exists(sdc_dst_file):
                    os.remove(sdc_dst_file)
                relative_symlink(sdc_src_file, sdc_dst_file)

class Command(BaseCommand):
    help = 'This function links all templates into the controller directory'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **ops):
        manage_py_file_path = sys.argv[0] if len(sys.argv) > 0 else 'manage.py'
        settings = settings_manager.SettingsManager(manage_py_file_path)
        all_apps = settings.get_apps()
        for app_name in all_apps[1:]:
            sdc_controller_list_dir = os.path.join(options.PROJECT_ROOT, "Assets/src", app_name, "controller")
            if os.path.exists(sdc_controller_list_dir):
                for file in os.listdir(sdc_controller_list_dir):
                    make_link(app_name, file)
            for model in apps.get_app_config(app_name).get_models():
                make_model_link(app_name, model.__name__ )
