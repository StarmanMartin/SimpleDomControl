import os
import re
import shutil
import sys

from django.core.management.base import BaseCommand
from sdc_manager.management.commands.init_add.utils import convert_to_tag_name, copy

from sdc_manager.management.commands.init_add import options, settings_manager
from sdc_manager.management.commands.init_add.add_controller_manager import AddControllerManager
from sdc_manager.management.commands.sdc_link_html import make_link


def copy_css_file(src, dest, controller_tag_name):
    def handler(text):
        return "[%s] {\n%s\n}" % (controller_tag_name, text)

    copy_and_filter(src, dest, final_handler=handler)


def copy_js_controller(src, dest):
    isAfterShow = {'val': False}

    def handler(line: str):
        if line.strip(' ').startswith('import') and '../../../' not in line:
            line = re.sub(r"(['\"])(\.\.?/)(?![#;\s])", r"\1\2../", line)
            line = re.sub(r"(['\"])\./\.", r"\1.", line)
        if '._cssUrls' in line:
            line = "\t\t// _cssUrls is deprecated and will be ignored in the new version!\n%s" % line
        if re.search(r"\s*afterShow\s*\([^)]*\)\s*\{", line):
            isAfterShow['val'] = True
            line = "\t\t// afterShow is deprecated and will be ignored in the new version!\n \t\t// If you use afterShow you can call the function in onRefresh\n%s" % line
        if "super.afterShow" in line:
            line = "\t\t// super.afterShow is not available anymore in the new version!\n \t\t//%s" % line
        if isAfterShow['val'] and re.search(r"\s*onRefresh\s*\([^)]*\)\s*\{", line):
            line += "\t\tthis.afterShow();\n"

        return line

    copy_and_filter(src, dest, filter_handler=handler)
    print("Controller updated: %s" % dest)


def copy_and_filter(src, dest, filter_handler=None, final_handler=None):
    fin = open(src, 'r')
    text = ''
    for line in fin:
        if filter_handler is not None:
            text += filter_handler(line)
        else:
            text += line
    if final_handler is not None:
        text = final_handler(text)
    fin.close()
    fout = open(dest, 'w+')
    fout.write(text)
    fout.close()


class Command(BaseCommand):
    help = 'This function updates all from older version of SDC to the current one'
    controller_import_src = {}

    def update_imports(self):

        def update_file(file):

            file_obj = {'val': os.path.dirname(file)}
            def handler(line :str):
                if re.search('^\s*import', line):
                    from_sep_string = line.split('from')
                    from_string = from_sep_string[-1]
                    res = re.search(r"([\"'])(?:(?=(\\?))\2.)*?\1", from_string)
                    if res is None:
                        return line
                    import_str = res.group()
                    for key, val in self.controller_import_src.items():
                        if re.search("%s['\"]$" % key, import_str):
                            rel_val = os.path.relpath(val, file_obj['val'])
                            if not rel_val.startswith('.'):
                                rel_val = './' + rel_val
                            if len(from_sep_string) == 2:
                                line = "%s from '%s';\n" % (from_sep_string[0], rel_val)
                            else:
                                line = re.sub(r"([\"'])(?:(?=(\\?))\2.)*?\1", '"%s"' % rel_val, line)


                return line
            copy_and_filter(file, file, filter_handler=handler)

        src_root_dir = os.path.join(options.PROJECT_ROOT, "Assets/src")
        for root, dirs, files in os.walk(src_root_dir):
            for file in files:
                if file.endswith('.js'):
                    update_file(os.path.join(root, file))

    def add_arguments(self, parser):
        parser.add_argument('-nd', '--not_delete_old', type=bool, help='If set the old files will not be deleted!')

    def handle(self, *args, **ops):
        raise NotImplementedError()
        manage_py_file_path = sys.argv[0] if len(sys.argv) > 0 else 'manage.py'
        settings = settings_manager.SettingsManager(manage_py_file_path)
        all_apps = settings.get_apps()
        for app_name in all_apps[1:]:
            sdc_js_outer_dir = os.path.join(options.PROJECT_ROOT, "static", app_name, "js")
            new_sdc_app_dir = os.path.join(options.PROJECT_ROOT, "Assets/src", app_name, "controller")
            if os.path.exists(sdc_js_outer_dir):
                sdc_css_dir = os.path.join(options.PROJECT_ROOT, "static", app_name, "css/sdc")
                sdc_js_dir = os.path.join(sdc_js_outer_dir, 'sdc')
                for file in os.listdir(sdc_js_dir):
                    old_js_file = os.path.join(sdc_js_dir, file)
                    if os.path.isdir(old_js_file):
                        shutil.copytree(str(old_js_file), os.path.join(new_sdc_app_dir, str(file)))
                    else:
                        controller_name_sc = str(file).removesuffix('.js')
                        new_sdc_controller_dir = str(os.path.join(new_sdc_app_dir, controller_name_sc))
                        if not os.path.exists(new_sdc_controller_dir):
                            os.makedirs(new_sdc_controller_dir)
                        self.controller_import_src[str(file)] = os.path.join(new_sdc_app_dir, controller_name_sc, str(file))
                        new_sdc_controller_file = os.path.join(new_sdc_controller_dir, str(file))
                        copy_js_controller(old_js_file, new_sdc_controller_file)
                        if ops.get('not_delete_old') is None:
                            os.remove(old_js_file)
                        sdc_css_file = os.path.join(sdc_css_dir, controller_name_sc + '.css')
                        include_css = os.path.exists(sdc_css_file)
                        if include_css:
                            copy_css_file(sdc_css_file,
                                          os.path.join(new_sdc_controller_dir, controller_name_sc + '.scss'),
                                          convert_to_tag_name(controller_name_sc))
                            if ops.get('not_delete_old') is None:
                                os.remove(sdc_css_file)
                        add_sdc_manager = AddControllerManager(app_name, controller_name_sc)
                        add_sdc_manager.add_to_organizer(include_css)
                        make_link(app_name, controller_name_sc)
                for outer_file in os.listdir(sdc_js_outer_dir):
                    outer_file_path = os.path.join(new_sdc_app_dir, '..', str(outer_file))
                    if outer_file != 'sdc' and not os.path.exists(outer_file_path):
                        shutil.copytree(str(os.path.join(sdc_js_outer_dir, outer_file)), outer_file_path)
        self.update_imports()
        print(
            "willShow and _cssUrls is deprecated. PLease make sure thapytestst you update that these deprecated methods "
            "are handled correctly.")

        if not os.path.exists(os.path.join(options.PROJECT_ROOT, 'Assets/webpack.config')):
            shutil.copytree(os.path.join(options.SCRIPT_ROOT, "template_files/Assets/webpack.config"),
                            os.path.join(options.PROJECT_ROOT, 'Assets/webpack.config'))
        for file in ['gulpfile.js', 'package.json', '.babelrc']:
            if not os.path.exists(os.path.join(options.PROJECT_ROOT, 'Assets', file)):
                copy(os.path.join(options.SCRIPT_ROOT, "template_files/Assets", file),
                     os.path.join(options.PROJECT_ROOT, 'Assets', file), options.REPLACEMENTS)

