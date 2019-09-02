#!/usr/bin/env python

import os
import sys

from sdc_manager.management.commands.init_add.sdc_core_manager import add_sdc_core, clean_up, add_sdc_to_main_urls
from sdc_manager.management.commands.init_add.add_controller_manager import AddControllerManager
from sdc_manager.management.commands.init_add.utils import copy, copy_and_prepare, makedirs_if_not_exist
from sdc_manager.management.commands.init_add import options, settings_manager

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(
            options.CMD_COLORS.as_warning("Params are required: [manage.py (Optional)] [init|cc (create controller)]"))
        exit(2)

    manage_py_file_path = sys.argv[1] if len(sys.argv) > 2 else 'manage.py'

    if not os.path.exists(os.path.join(options.PROJECT_ROOT, manage_py_file_path)):
        print(options.CMD_COLORS.as_error(manage_py_file_path + "does not exist!! sorry"))
        exit(1)

    settings = settings_manager.SettingsManager(manage_py_file_path)

    if not os.path.exists(settings.get_settings_file_path()):
        print(options.CMD_COLORS.as_error(settings.get_settings_file_path() + " settings file does not exist!! sorry"))
        exit(1)

    if not settings.get_setting_vals().TEMPLATES[0]['APP_DIRS']:
        print(options.CMD_COLORS.as_error("simpleDomControl only works if TEMPLATES -> APP_DIRS is ture"))
        exit(1)

    all_apps = settings.get_apps()

    if sys.argv[-1] == "init":
        main_static = os.path.join(options.PROJECT_ROOT, options.MAIN_APP_NAME, "static")
        main_templates = os.path.join(options.PROJECT_ROOT, options.MAIN_APP_NAME, "templates")

        sdc_dir = os.path.join(main_static, "simpleDomControl")
        if os.path.exists(sdc_dir):
            print(options.CMD_COLORS.as_error("SimpleDomControl has init already!"))
            exit(2)

        add_sdc_core()
        clean_up()

        settings.get_setting_vals().INSTALLED_APPS.append(options.MAIN_APP_NAME)
        settings.update_settings()

        makedirs_if_not_exist(main_static)
        makedirs_if_not_exist(main_templates)
        copy(os.path.join(options.SCRIPT_ROOT, "templates", "static", "simpleDomControl"), sdc_dir)
        copy(os.path.join(options.SCRIPT_ROOT, "templates", "management"),
             os.path.join(options.PROJECT_ROOT, all_apps[0], "management"))

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", ".bowerrc"),
                         os.path.join(options.SCRIPT_ROOT, ".bowerrc"),
                         options.REPLACEMENTS)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "static", "main.organizer.js"),
                         os.path.join(main_static, all_apps[0], "js", "main.organizer.js"),
                         options.REPLACEMENTS)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "static", "style.css"),
                         os.path.join(main_static, all_apps[0], "css", "style.css"),
                         options.REPLACEMENTS)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "templates", "base.html"),
                         os.path.join(main_templates, "base.html"),
                         options.REPLACEMENTS)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "templates", "index.html"),
                         os.path.join(main_templates, all_apps[0], "index.html"),
                         options.REPLACEMENTS)

        add_sdc_to_main_urls(settings.get_main_url_path())
    elif sys.argv[-1] == "cc":
        text = "Enter number to select an django App:"
        for idx in range(1, len(all_apps)):
            text += "\n%d -> %s" % (idx, all_apps[idx])

        idx = 1
        try:
            idx = int(input(text + "\nEnter number: [%d]" % (len(all_apps) - 1)) or (len(all_apps) - 1))
        except Exception as ex:
            print(options.CMD_COLORS.as_error("Input has to be a number between 1 and %d" % (len(all_apps) - 1)))
            exit(1)

        app_name = all_apps[idx]

        text = "Enter the name of the new controller (use snake_case):"
        controller_name = str(input(text))
        add_sdc_manager = AddControllerManager(app_name, controller_name)
        if len(controller_name) == 0:
            print(options.CMD_COLORS.as_error("Controller name must not be empty!"))
            exit(1)
        elif not add_sdc_manager.check_if_url_is_unique():
            print(options.CMD_COLORS.as_error("%s already exists. Controller name has to be unique!" % controller_name))
            exit(1)

        add_sdc_manager.add_url_to_url_pattern(settings.get_main_url_path())
        add_sdc_manager.add_view_class_to_sdc_views()
        add_sdc_manager.prepare_files()
        add_sdc_manager.add_to_organizer()
        add_sdc_manager.add_to_index()
