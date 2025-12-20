import os
import re
import subprocess
import sys
from typing import Optional

from django.urls import get_resolver

from sdc_core.management.commands.init_add import options
from sdc_core.management.commands.init_add.settings_manager import get_app_path
from sdc_core.management.commands.init_add.utils import convert_to_snake_case, copy_and_prepare, \
    convert_to_camel_case, \
    convert_to_title_camel_case, convert_to_tag_name, prepare_as_string


class AddControllerManager:
    def __init__(self, app_name: str, controller_name: str, mixins: Optional[list[str]] = None):
        if mixins is None:
            self.mixins = []
        self.app_name = app_name
        self.mixins = mixins
        self.controller_name_sc = convert_to_snake_case(controller_name)
        self.controller_name_cc = convert_to_camel_case(controller_name)
        self.controller_name_tcc = convert_to_title_camel_case(controller_name)
        self.controller_name = controller_name
        self._template_url = None

        self.reps = {**options.REPLACEMENTS, **{'§CONTROLLERNAMETITLE§': self.controller_name_tcc,
                                                '§CONTROLLERNAMECC§': self.controller_name_cc,
                                                '§CONTROLLERNAMESC§': self.controller_name_sc,
                                                '§APPNAME§': self.app_name
                                                }}

    @classmethod
    def check_controller_name(cls, app_name, c_name_sc):
        url_name = cls.get_url(app_name, c_name_sc)
        return url_name != ''

    @staticmethod
    def get_url(app_name, c_name_sc):
        url_name_old = "scd_view_" + c_name_sc
        url_name = f"scd_view_{app_name}_{c_name_sc}"
        old_url_to_sdc = ''
        for i in get_resolver().reverse_dict.keys():
            if str(i).endswith(url_name_old):
                old_url_to_sdc = "/" + get_resolver().reverse_dict[i][0][0][0]
            if str(i).endswith(url_name):
                url_to_sdc = "/" + get_resolver().reverse_dict[i][0][0][0]
                return url_to_sdc
        return old_url_to_sdc

    @classmethod
    def add_js_app_to_organizer(cls, app_name):
        org_file_path_root = os.path.join(options.PROJECT_ROOT, "Assets/src",
                                          "index.organizer.js")
        if  get_app_path(app_name).startswith(options.PROJECT_ROOT):
            line = 'import {} from "./%s/%s.organizer.js";\n' % (app_name, app_name)
        else:
            line = 'import {} from "#lib/%s/%s.organizer.js";\n' % (app_name, app_name)
        cls._add_js_to_src(org_file_path_root, line)

    @classmethod
    def add_css_app_to_organizer(cls, app_name):
        org_file_path_root = os.path.join(options.PROJECT_ROOT, "Assets/src",
                                          "index.style.scss")
        if  get_app_path(app_name).startswith(options.PROJECT_ROOT):
            line = f'@use "{app_name}/{app_name}.style";\n'
        else:
            line = f'@use "../libs/{app_name}/{app_name}.style";\n'
        cls._add_scss_to_src(org_file_path_root, line)

    def check_if_url_is_unique(self):
        return not self.check_controller_name(self.app_name, self.controller_name_sc)

    def get_template_url(self):
        if self._template_url is not None:
            return self._template_url
        cmd = f'{sys.executable} manage.py sdc_get_controller_url {self.app_name} {self.controller_name_sc}'
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, cwd=options.PROJECT_ROOT)
        out = str(p.communicate()[0], encoding="utf-8")
        out = re.sub(r'\\r?\\n.*$', r'', out)
        out = re.sub(r'\r?\n.*$', r'', out)
        self._template_url = re.sub(r'^b\'([^\']*)\'$', r'\g<1>', out)
        return self._template_url

    def get_template_url_sync(self):
        if self._template_url is not None:
            return self._template_url
        out = self.get_url(self.app_name, self.controller_name_sc)
        self._template_url = re.sub(r'^b\'([^\']*)\'$', r'\g<1>', out)
        return self._template_url

    def get_url_params(self):
        url = self.get_template_url()
        return re.findall(r'%\(([^)]+)\)\w', url)

    def get_params_as_string(self):
        params_list = self.get_url_params()
        if len(params_list) > 0:
            return ', ' + ', '.join(params_list)
        return ''

    def add_url_to_url_pattern(self, main_urls_path):
        urls_path = os.path.join(options.PROJECT_ROOT, self.app_name, "sdc_urls.py")

        if not os.path.exists(urls_path):
            copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "template_files", "sdc_urls.py.txt"),
                             os.path.join(options.PROJECT_ROOT, self.app_name, "sdc_urls.py"),
                             self.reps)

            copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "template_files", "sdc_views.py.txt"),
                             os.path.join(options.PROJECT_ROOT, self.app_name, "sdc_views.py"),
                             self.reps)

            copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "template_files", "js_test.js.txt"),
                             os.path.join(options.PROJECT_ROOT, self.app_name, 'Assets/tests',
                                          f"{self.app_name}.test.js"),
                             self.reps)

            self._add_new_sdc_to_main_urls(main_urls_path)

        self._add_sdc_views_to_main_urls(os.path.join(options.PROJECT_ROOT, self.app_name, "sdc_urls.py"))

    def _add_new_sdc_to_main_urls(self, main_urls_path):
        return self._add_to_urls(main_urls_path, "sdc_view/%s/" % self.app_name,
                                 "include('%s.sdc_urls')" % self.app_name)

    def _add_sdc_views_to_main_urls(self, main_urls_path):
        return self._add_to_urls(main_urls_path, self.controller_name_sc,
                                 f"sdc_views.{self.controller_name_tcc}.as_view(), name='scd_view_{self.app_name}_{self.controller_name_sc}'")

    def add_view_class_to_sdc_views(self):
        fin = open(os.path.join(options.PROJECT_ROOT, self.app_name, "sdc_views.py"), "at", encoding='utf-8')
        fin.write(
            "\n\nclass %s(SDCView):\n%stemplate_name='%s/sdc/%s.html'\n" % (
                self.controller_name_tcc, options.SEP, self.app_name, self.controller_name_sc))
        fin.close()
        fin = open(os.path.join(options.PROJECT_ROOT, self.app_name, "sdc_views.py"), "at", encoding='utf-8')

        fin.write(
            "\n%sdef get_content(self, request%s, *args, **kwargs):\n%sreturn render(request, self.template_name)" % (
                options.SEP, self.get_params_as_string(), options.SEP * 2))
        fin.close()

    def prepare_files(self):
        main_static = os.path.join(
            options.PROJECT_ROOT, self.app_name, "Assets/src", self.app_name, 'controller', self.controller_name_sc)
        main_templates = os.path.join(options.PROJECT_ROOT, self.app_name, "templates", self.app_name)
        self.reps['§TEMPLATEURL§'] = self.get_template_url()
        self.reps['§TAGNAME§'] = self.prepare_tag_name()
        self.reps['§TAG§'] = convert_to_tag_name(self.controller_name_cc)
        self.reps['§OVERWRITING§'] = 'true' if not self.check_if_url_is_unique() else 'false'
        if self.mixins:
            self.reps['§MIXIN§'] = '.addMixin("%s")' % '", "'.join(self.mixins)
        else:
            self.reps['§MIXIN§'] = ''
        copy_and_prepare(
            os.path.join(options.SCRIPT_ROOT, "template_files", "controller", "template_controller.js.txt"),
            os.path.join(str(main_static), self.controller_name_sc + ".js"),
            self.reps)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "template_files", "controller", "template_css.scss"),
                         os.path.join(str(main_static), self.controller_name_sc + ".scss"),
                         self.reps)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "template_files", "controller", "templade_view.html"),
                         os.path.join(main_templates, "sdc",
                                      self.controller_name_sc + ".html"),
                         self.reps)

    def add_to_organizer(self, add_css=True):
        org_js_file_path = os.path.join(options.PROJECT_ROOT, self.app_name, "Assets/src", self.app_name,
                                        "%s.organizer.js" % self.app_name)
        org_style_file_path = os.path.join(options.PROJECT_ROOT, self.app_name, "Assets/src", self.app_name,
                                           "%s.style.scss" % self.app_name)

        if not os.path.exists(org_js_file_path):
            self.add_js_app_to_organizer(self.app_name)

        if add_css:
            if not os.path.exists(org_style_file_path):
                self.add_css_app_to_organizer(self.app_name)

            line = '@use "controller/%s/%s";\n' % (self.controller_name_sc, self.controller_name_sc)
            self._add_scss_to_src(org_style_file_path, line)

        line = 'import {} from "./controller/%s/%s.js";\n' % (self.controller_name_sc, self.controller_name_sc)
        self._add_js_to_src(org_js_file_path, line)

    def add_js_test(self):
        text = prepare_as_string(
            os.path.join(options.SCRIPT_ROOT, "template_files", "controller", "template_test.js.text"), self.reps)
        fp = os.path.join(options.PROJECT_ROOT, self.app_name, 'Assets/tests', f"{self.app_name}.test.js")
        fout = open(fp, "a", encoding='utf-8')
        fout.write(text)
        fout.close()

    @staticmethod
    def _add_js_to_src(org_file_path, new_line: str):
        text = []
        new_line = new_line.strip('\n')
        if os.path.exists(org_file_path):
            with  open(org_file_path, 'r', encoding='utf-8') as fin:
                for line in fin:
                    text.append(line.strip('\n'))

        if new_line not in text:
            text.insert(0, new_line)
        with open(org_file_path, "w+", encoding='utf-8') as fout:
            fout.write('\n'.join(text))

    @staticmethod
    def _add_scss_to_src(org_file_path, new_line):
        add_idx = 0
        text = []
        new_line = new_line.strip('\n')
        if os.path.exists(org_file_path):
            with  open(org_file_path, 'r', encoding='utf-8') as fin:
                add_idx = -1
                for idx, line in enumerate(fin):
                    if not line.startswith('@use') and add_idx == -1:
                        add_idx = idx
                    text.append(line.strip('\n'))

        if new_line not in text:
            text.insert(add_idx, new_line)
        with open(org_file_path, "w+", encoding='utf-8') as fout:
            fout.write('\n'.join(text))

    @staticmethod
    def _add_to_urls(main_urls_path, url_path, handler):
        fin = open(main_urls_path, "r+", encoding='utf-8')
        text = ""
        is_done = False

        for line in fin:
            if not is_done and "# scd view below" in line:
                line += "%spath('%s', %s),\n" % (options.SEP, url_path.lower(), handler)
                is_done = True
            text += line

        fin.close()
        if not is_done:
            print(options.CMD_COLORS.as_warning("Do not forgett to add:"))
            print(options.CMD_COLORS.as_important(
                "%spath('%s', %s),\n # scd view below\n]" % (options.SEP, url_path.lower(), handler)))
            print(options.CMD_COLORS.as_warning("to: %s " % main_urls_path))

        fout = open(main_urls_path, "w+", encoding='utf-8')
        fout.write(text)
        fout.close()

    def prepare_tag_name(self):
        tag_name = convert_to_tag_name(self.controller_name_cc)
        param_list = []
        for x in self.get_url_params():
            param_list.append(convert_to_tag_name(x) + '=""')
        param_data_str = ""
        if len(param_list) > 0:
            param_data_str = " data-"
        param_data_str += param_data_str.join(param_list)
        return "<%s%s></%s>" % (tag_name, param_data_str, tag_name)
