import os
import sys

from django.core.management.base import BaseCommand

from sdc_core.management.commands.init_add import options, settings_manager
from django.apps import apps

from sdc_core.management.commands.init_add.settings_manager import get_app_path


def relative_symlink(src, dst):
    try:
        os.unlink(dst)
    except:
        pass
    dir = os.path.dirname(dst)
    Src = os.path.relpath(src, dir)
    Dst = os.path.join(dir, os.path.basename(src))
    os.makedirs(dir, exist_ok=True)
    return os.symlink(Src, Dst)

def make_app_links(app_name):
    app_root = get_app_path(app_name)
    sdc_controller_link_dir = os.path.join(options.PROJECT_ROOT, "Assets/src", app_name)
    sdc_controller_dir = os.path.join(app_root, "Assets/src", app_name)
    if os.path.exists(sdc_controller_link_dir):
        os.remove(sdc_controller_link_dir)
    relative_symlink(sdc_controller_dir, sdc_controller_link_dir)

    sdc_test_link_dir = os.path.join(options.PROJECT_ROOT, "Assets/tests")#, f"{app_name}.test.js")
    sdc_test_file_dir = os.path.join(app_root, "Assets/tests")#, f"{app_name}.test.js")
    for file in  os.listdir(sdc_test_file_dir):
        if file.endswith('.test.js'):
            relative_symlink(os.path.join(sdc_test_file_dir, file), os.path.join(sdc_test_link_dir, file))


def make_link(app_name, controller_name):
    make_app_links(app_name)
    app_root = get_app_path(app_name)

    sdc_controller_dir = os.path.join(app_root, "Assets/src", app_name, 'controller')
    if os.path.exists(sdc_controller_dir):
        sdc_c_dir = os.path.join(sdc_controller_dir, controller_name)
        sdc_c_js = os.path.join(sdc_c_dir, "%s.js" % controller_name)
        if os.path.isdir(sdc_c_dir) and os.path.isfile(sdc_c_js):
            sdc_c_html = os.path.join(app_root, "templates", app_name, 'sdc',
                                      "%s.html" % controller_name)
            if os.path.isfile(sdc_c_html):
                sdc_link_path = os.path.join(sdc_c_dir, "%s.html" % controller_name)
                if os.path.exists(sdc_link_path):
                    os.remove(sdc_link_path)
                relative_symlink(sdc_c_html, sdc_link_path)


def make_model_link(app_name, model_name):
    sdc_dst_dir = os.path.join(get_app_path(app_name), "Assets/src", app_name, "models", model_name)
    sdc_src_dir = os.path.join(options.PROJECT_ROOT, app_name, "templates", app_name, 'models', model_name)
    if not os.path.exists(sdc_dst_dir):
        os.makedirs(sdc_dst_dir)
    if os.path.exists(sdc_src_dir):
        for file in os.listdir(sdc_src_dir):
            sdc_src_file = os.path.join(sdc_src_dir, file)
            sdc_dst_file = os.path.join(sdc_dst_dir, file)
            if os.path.isdir(sdc_dst_dir) and os.path.isfile(sdc_src_file):
                relative_symlink(sdc_src_file, sdc_dst_file)


class Command(BaseCommand):
    help = 'This function links all templates into the controller directory'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **ops):
        manage_py_file_path = sys.argv[0] if len(sys.argv) > 0 else 'manage.py'
        settings = settings_manager.SettingsManager(manage_py_file_path)
        all_apps = settings.get_sdc_apps()
        for app_name in all_apps:
            sdc_controller_list_dir = os.path.join(get_app_path(app_name), "Assets/src", app_name, "controller")
            if os.path.exists(sdc_controller_list_dir):
                for file in os.listdir(sdc_controller_list_dir):
                    make_link(app_name, file)
            for model in apps.get_app_config(app_name).get_models():
                make_model_link(app_name, model.__name__)
