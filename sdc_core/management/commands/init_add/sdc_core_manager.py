import errno
import os
import re
import shutil

from sdc_core.management.commands.init_add import options

def copy_apps():
    for tool in ['sdc_examples']:
        src = os.path.join(options.SCRIPT_ROOT, "template_files", 'apps', tool)
        dest = os.path.join(options.PROJECT_ROOT, tool)
        try:
            shutil.copytree(src, dest)
        except OSError as exc: # python >2.5
            if exc.errno == errno.ENOTDIR:
                shutil.copy(src, dest)
            else: raise

def add_sdc_to_main_urls(main_urls_path):
    fin = open(main_urls_path, "rt", encoding='utf-8')
    text = ""
    is_done = False

    for line in fin:
        if 'from django.urls import path' in line:
            line = re.sub(r'path', 'path, re_path, include\nfrom django.shortcuts import render\nfrom django.conf import settings\nfrom django.views.i18n import JavaScriptCatalog', line)

        if "urlpatterns = [" in line:
            new_apps = "%sre_path('sdc_view/sdc_tools/', include('sdc_tools.sdc_urls')),\n" % options.SEP
            new_apps += "%sre_path('sdc_view/sdc_user/', include('sdc_user.sdc_urls')),\n" % options.SEP
            line = re.sub(r'urlpatterns = \[',
                          "urlpatterns = [\n%s%s# scd view below\n" % (new_apps,options.SEP), line)
            is_done = True
        text += line

    f_urls = open(os.path.join(options.SCRIPT_ROOT, "template_files", "urls.py.txt"), "rt", encoding='utf-8')
    for line in f_urls:
        for key in options.REPLACEMENTS:
            line = line.replace(key, options.REPLACEMENTS[key])
        text += line

    f_urls.close()
    fin.close()
    if not is_done:
        print(options.CMD_COLORS.as_warning("Some thing went wrong: %s " % main_urls_path))

    fout = open(main_urls_path, "w+", encoding='utf-8')
    fout.write(text)

    fout.close()
