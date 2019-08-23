import os
import re

import options
from utils import convert_to_snake_case, copy_and_prepare, convert_to_camel_case, \
    convert_to_title_camel_case


class AddControllerManager:
    def __init__(self, app_name: str, controller_name: str):
        self.app_name = app_name
        self.controller_name_sc = convert_to_snake_case(controller_name)
        self.controller_name_cc = convert_to_camel_case(controller_name)
        self.controller_name_tcc = convert_to_title_camel_case(controller_name)
        self.controller_name = controller_name

        self.reps = {**options.REPLACEMENTS, **{'§CONTROLLERNAMETITLE§': self.controller_name_tcc,
                                                '§CONTROLLERNAMECC§': self.controller_name_cc,
                                                '§CONTROLLERNAMESC§': self.controller_name_sc,
                                                '§APPNAME§': self.app_name,
                                                '§TEMPLATEURL§': self.get_template_url()
                                                }}

    def check_if_url_is_unique(self):
        import subprocess
        cmd = 'python manage.py check_if_sdc_exists %s' % self.controller_name_sc
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, cwd=options.PROJECT_ROOT)
        out = p.communicate()[0]
        return "FALSE" in str(out)

    def get_template_url(self):
        import subprocess
        cmd = 'python manage.py get_url_of_a_sdc %s' % self.controller_name_sc
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, cwd=options.PROJECT_ROOT)
        out = p.communicate()[0]
        out = re.sub(r'\\n', r'', str(out))
        return re.sub(r'^b\'([^\']*)\'$', r'\1', out)

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
            "\n\nclass %s(View):\n%stemplate_name='%s/sdc/%s.html'\n\n%sdef get(self, request):\n%sreturn render(request, self.template_name)" % (
                self.controller_name_tcc, options.SEP, self.app_name,
                self.controller_name_sc, options.SEP, options.SEP * 2))

    def prepare_files(self):
        main_static = os.path.join(options.PROJECT_ROOT, self.app_name, "static")
        main_templates = os.path.join(options.PROJECT_ROOT, self.app_name, "templates", self.app_name)

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
        return self._add_js_to_srcs(org_file_path, line, ',')

    def add_to_index(self):
        org_file_path = os.path.join(options.PROJECT_ROOT, options.MAIN_APP_NAME, "templates", options.MAIN_APP_NAME,
                                     "index.html")
        line = '<script src="/static/%s/js/sdc/%s.js" type="text/javascript"></script>\n' % (
            self.app_name, self.controller_name_sc)
        return self._add_js_to_srcs(org_file_path, line, '')

    @staticmethod
    def _add_js_to_srcs(org_file_path, new_line, sep):
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
