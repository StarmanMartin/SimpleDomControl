import os
import re
import subprocess

from sdc_manager.management.commands import check_if_sdc_exists, get_url_of_a_sdc
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

    def check_if_url_is_unique(self):
        return not check_if_sdc_exists.Command.check_controller_name(self.controller_name_sc)

    def get_template_url(self):
        if self._template_url is not None:
            return self._template_url
        cmd = 'python manage.py get_url_of_a_sdc %s' % self.controller_name_sc
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, cwd=options.PROJECT_ROOT)
        out = p.communicate()[0]
        out = re.sub(r'\\n', r'', str(out))
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

    def add_url_to_url_pattern(self, main_urls_path):
        urls_path = os.path.join(options.PROJECT_ROOT, self.app_name, "sdc_urls.py")

        if not os.path.exists(urls_path):
            copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "sdc_urls.py"),
                             os.path.join(options.PROJECT_ROOT, self.app_name, "sdc_urls.py"),
                             self.reps)

            copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "sdc_views.py"),
                             os.path.join(options.PROJECT_ROOT, self.app_name, "sdc_views.py"),
                             self.reps)

            self._add_new_sdc_to_main_urls(main_urls_path)

        self._add_sdc_views_to_main_urls(os.path.join(options.PROJECT_ROOT, self.app_name, "sdc_urls.py"))

    def _add_new_sdc_to_main_urls(self, main_urls_path):
        return self._add_to_urls(main_urls_path, "sdc_view/%s/" % self.app_name,
                                 "include('%s.sdc_urls')" % self.app_name)

    def _add_sdc_views_to_main_urls(self, main_urls_path):
        return self._add_to_urls(main_urls_path, self.controller_name_sc,
                                 "sdc_views.%s.as_view(), name='scd_view_%s'" % (
                                     self.controller_name_tcc, self.controller_name_sc))

    def add_view_class_to_sdc_views(self):
        fin = open(os.path.join(options.PROJECT_ROOT, self.app_name, "sdc_views.py"), "at")
        fin.write(
            "\n\nclass %s(View):\n%stemplate_name='%s/sdc/%s.html'\n" % (
                self.controller_name_tcc, options.SEP, self.app_name, self.controller_name_sc))
        fin.close()
        fin = open(os.path.join(options.PROJECT_ROOT, self.app_name, "sdc_views.py"), "at")

        fin.write(
            "\n%sdef get(self, request%s, *args, **kwargs):\n%sreturn render(request, self.template_name)" % (
                options.SEP, self.get_params_as_string(), options.SEP * 2))
        fin.close()

    def prepare_files(self):
        main_static = os.path.join(options.PROJECT_ROOT, self.app_name, "static")
        main_templates = os.path.join(options.PROJECT_ROOT, self.app_name, "templates", self.app_name)
        self.reps['§TEMPLATEURL§'] = self.get_template_url()
        self.reps['§TAGNAME§'] = self.prepare_tag_name()

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "controller", "template_controller.js.txt"),
                         os.path.join(main_static, self.app_name, "js", "sdc",
                                      self.controller_name_sc + ".js"),
                         self.reps)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "controller", "templade_view.html"),
                         os.path.join(main_templates, "sdc",
                                      self.controller_name_sc + ".html"),
                         self.reps)

        copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "controller", "template_css.css"),
                         os.path.join(main_static, self.app_name, "css", "sdc",
                                      self.controller_name_sc + ".css"),
                         self.reps)

    def add_to_organizer(self):
        org_file_path = os.path.join(options.PROJECT_ROOT, options.MAIN_APP_NAME, "static", options.MAIN_APP_NAME, "js",
                                     "main.organizer.js")
        line = '"/static/%s/js/sdc/%s.js"\n' % (self.app_name, self.controller_name_sc)
        return self._add_js_to_src(org_file_path, line, ',' + options.SEP)

    def add_to_index(self):
        org_file_path = os.path.join(options.PROJECT_ROOT, options.MAIN_APP_NAME, "templates", options.MAIN_APP_NAME,
                                     "index.html")
        line = '<script src="/static/%s/js/sdc/%s.js" type="text/javascript"></script>\n' % (
            self.app_name, self.controller_name_sc)
        return self._add_js_to_src(org_file_path, line, '')

    @staticmethod
    def _add_js_to_src(org_file_path, new_line, sep):
        fin = open(org_file_path, "rt")
        text = ""
        is_done = False
        is_first = False
        for line in fin:
            if not is_done and "controller-src-section-start" in line:
                is_first = True
            elif not is_done and "controller-src-section-end" in line:
                line = '%s%s' % (new_line, line)
                if not is_first:
                    line = "%s%s" % (sep, line)
                is_done = True
            else:
                is_first = False
            text += line

        fin.close()

        fout = open(org_file_path, "w+")
        fout.write(text)
        fout.close()

    @staticmethod
    def _add_to_urls(main_urls_path, url_path, handler):
        fin = open(main_urls_path, "rt")
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

        fout = open(main_urls_path, "w+")
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
