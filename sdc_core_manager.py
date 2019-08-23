import os
import re

from utils import copy_and_prepare
import options

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
                     {})

def add_sdc_to_main_urls(main_urls_path):
    fin = open(main_urls_path, "rt")
    text = ""
    is_done = False

    for line in fin:
        if "urlpatterns = [" in line:
            line = re.sub(r'urlpatterns = \[', "urlpatterns = [\npath('', include('scd_core.urls')),\n # scd view below\n", line)
            is_done = True
        text += line

    fin.close()
    if not is_done:
        print(options.CMD_COLORS.as_warning("Do not forgett to add:"))
        print(options.CMD_COLORS.as_important("urlpatterns += [path('', include('scd_core.urls')),\n # scd view below\n]"))
        print(options.CMD_COLORS.as_warning("to: %s " % main_urls_path))

    fout = open(main_urls_path, "w+")
    fout.write(text)


    fout.close()

