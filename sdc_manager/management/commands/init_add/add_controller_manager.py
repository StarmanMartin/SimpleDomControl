import os
import re
import subprocess

from django.urls import get_resolver

from sdc_manager.management.commands.init_add import options
from sdc_manager.management.commands.init_add.utils import convert_to_snake_case, copy_and_prepare, \
    convert_to_camel_case, \
    convert_to_title_camel_case, convert_to_tag_name


class AddControllerManager:
    def __init__(self, app_name: str, controller_name: str):
        self.app_name = app_name
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

    @staticmethod
    def check_controller_name(c_name_sc):
        url_name = "scd_view_" + c_name_sc

        for i in get_resolver().reverse_dict.keys():
            if str(i).endswith(url_name):
                return True

        return False

    @staticmethod
    def get_url(c_name_sc):
        url_name = "scd_view_" + c_name_sc

        for i in get_resolver().reverse_dict.keys():
            if str(i).endswith(url_name):
                url_to_sdc = "/" + get_resolver().reverse_dict[i][0][0][0]
                return url_to_sdc
        return ''

    def check_if_url_is_unique(self):
        return not self.check_controller_name(self.controller_name_sc)

    def get_template_url(self):
        if self._template_url is not None:
            return self._template_url
        cmd = 'python manage.py get_url_of_a_sdc %s' % self.controller_name_sc
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, cwd=options.PROJECT_ROOT)
        out = str(p.communicate()[0], encoding="utf-8")
        out = re.sub(r'\\r?\\n', r'', out)
        out = re.sub(r'\r?\n', r'', out)
        self._template_url = re.sub(r'^b\'([^\']*)\'$', r'\1', out)
        return self._template_url

    def get_template_url_sync(self):
        if self._template_url is not None:
            return self._template_url
        out = self.get_url(self.controller_name_sc)
        self._template_url = re.sub(r'^b\'([^\']*)\'$', r'\1', out)
        return self._template_url

    def get_url_params(self):
        url = self.get_template_url()
        return re.findall(r'%\(([^)]+)\)\w', url)

    def get_params_as_string(self):
        params_list = self.get_url_params()
        if len(params_list) > 0:
            return ', ' + ', '.join(params_list)
        return ''

    def add_url_to_url_pattern(self, main_urls_path, consumers_path):
        urls_path = os.path.join(options.PROJECT_ROOT, self.app_name, "sdc_urls.py")

        if not os.path.exists(urls_path):
            copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "sdc_urls.py"),
                             os.path.join(options.PROJECT_ROOT, self.app_name, "sdc_urls.py"),
                             self.reps)

            copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "sdc_views.py"),
                             os.path.join(options.PROJECT_ROOT, self.app_name, "sdc_views.py"),
                             self.reps)

            self._add_new_sdc_to_main_urls(main_urls_path)
            self._add_new_sdc_to_routing(consumers_path)

        self._add_sdc_views_to_main_urls(os.path.join(options.PROJECT_ROOT, self.app_name, "sdc_urls.py"))

    def _add_new_sdc_to_routing(self, consumers_path):
        new_line = "from {0} import sdc_views as {0}".format(self.app_name)
        with open(consumers_path, 'r', encoding='utf-8') as original: data = original.read()
        with open(consumers_path, 'w', encoding='utf-8') as modified: modified.write("%s\n%s" % (new_line, data))

    def _add_new_sdc_to_main_urls(self, main_urls_path):
        return self._add_to_urls(main_urls_path, "sdc_view/%s/" % self.app_name,
                                 "include('%s.sdc_urls')" % self.app_name)

    def _add_sdc_views_to_main_urls(self, main_urls_path):
        return self._add_to_urls(main_urls_path, self.controller_name_sc,
                                 "sdc_views.%s.as_view(), name='scd_view_%s'" % (
                                     self.controller_name_tcc, self.controller_name_sc))

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
            options.PROJECT_ROOT, "static", self.app_name)
        main_templates = os.path.join(options.PROJECT_ROOT, self.app_name, "templates", self.app_name)
        self.reps['§TEMPLATEURL§'] = self.get_template_url()
        self.reps['§TAGNAME§'] = self.prepare_tag_name()

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "controller", "template_controller.js.txt"),
                         os.path.join(main_static, "js", "sdc",
                                      self.controller_name_sc + ".js"),
                         self.reps)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "controller", "templade_view.html"),
                         os.path.join(main_templates, "sdc",
                                      self.controller_name_sc + ".html"),
                         self.reps)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "controller", "template_css.css"),
                         os.path.join(main_static, "css", "sdc",
                                      self.controller_name_sc + ".css"),
                         self.reps)

    def add_to_organizer(self):
        org_file_path = os.path.join(options.PROJECT_ROOT, "static", self.app_name, "js",
                                     "%s.organizer.js" % self.app_name)

        if not os.path.exists(org_file_path):
            org_file_path_root = os.path.join(options.PROJECT_ROOT, "static",
                                         "main.organizer.js")
            line = 'import {} from "./%s/js/%s.organizer.js"\n' % (self.app_name, self.app_name)

            self._add_js_to_src(org_file_path_root, line)

        line = 'import {} from "./sdc/%s.js"\n' % (self.controller_name_sc)
        return self._add_js_to_src(org_file_path, line)

    @staticmethod
    def _add_js_to_src(org_file_path, new_line):
        text = new_line
        if not os.path.exists(org_file_path):
            fin = open(org_file_path, 'x', encoding='utf-8')
        else:
            fin = open(org_file_path, 'r', encoding='utf-8')

            for line in fin:
                text += line

        fin.close()

        fout = open(org_file_path, "w+", encoding='utf-8')
        fout.write(text)
        fout.close()

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
