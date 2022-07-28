import errno
import os
import re
import shutil

from sdc_manager.management.commands.init_add.utils import copy_and_prepare
from sdc_manager.management.commands.init_add import options


def copy_user_and_tools():
    for tool in ['sdc_tools', 'sdc_user', 'sdc_examples']:
        src = os.path.join(options.SCRIPT_ROOT, "templates", 'apps', tool)
        dest = os.path.join(options.PROJECT_ROOT, tool)
        try:
            shutil.copytree(src, dest)
        except OSError as exc: # python >2.5
            if exc.errno == errno.ENOTDIR:
                shutil.copy(src, dest)
            else: raise

def add_sdc_core():
    import subprocess
    cmd = 'python manage.py startapp %s' % options.MAIN_APP_NAME
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, cwd=options.PROJECT_ROOT)
    out, err = p.communicate()


def clean_up():
    os.remove(os.path.join(options.PROJECT_ROOT, options.MAIN_APP_NAME, "tests.py"))
    os.remove(os.path.join(options.PROJECT_ROOT, options.MAIN_APP_NAME, "models.py"))
    os.remove(os.path.join(options.PROJECT_ROOT, options.MAIN_APP_NAME, "admin.py"))
    os.remove(os.path.join(options.PROJECT_ROOT, options.MAIN_APP_NAME, "views.py"))

    copy_and_prepare(os.path.join(options.SCRIPT_ROOT, "templates", "urls.py"),
                     os.path.join(options.PROJECT_ROOT, options.MAIN_APP_NAME, "urls.py"),
                     options.REPLACEMENTS)


def add_sdc_to_main_urls(main_urls_path):
    fin = open(main_urls_path, "rt", encoding='utf-8')
    text = ""
    is_done = False

    for line in fin:
        if 'from django.urls import path' in line:
            line = re.sub(r'path', 'path, re_path', line)

        if "urlpatterns = [" in line:
            new_apps = "%sre_path('sdc_view/sdc_tools/', include('sdc_tools.sdc_urls')),\n" % options.SEP
            new_apps += "%s# re_path('sdc_view/sdc_user/', include('sdc_user.sdc_urls')),\n" % options.SEP
            line = re.sub(r'urlpatterns = \[',
                          "urlpatterns = [\n%s%s# scd view below\n" % (new_apps,options.SEP), line)
            is_done = True
        text += line

    text += "\nurlpatterns += [path('', include('%s.urls'))]" % options.MAIN_APP_NAME

    fin.close()
    if not is_done:
        print(options.CMD_COLORS.as_warning("Do not forgett to add:"))
        print(options.CMD_COLORS.as_important(
            "urlpatterns += [\n%spath('', include('scd_core.urls')),\n # scd view below\n]" % options.SEP))
        print(options.CMD_COLORS.as_warning("to: %s " % main_urls_path))

    fout = open(main_urls_path, "w+", encoding='utf-8')
    fout.write(text)

    fout.close()
