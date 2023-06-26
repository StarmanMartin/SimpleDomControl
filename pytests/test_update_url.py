
import os
import re
import subprocess

from pytests.utils import are_dir_trees_equal


def test_update_url(init_project_with_app):
    subprocess.run(['python', 'manage.py', 'sdc_update_url'], stdout=subprocess.PIPE, cwd=init_project_with_app)
    dir1 = init_project_with_app
    dir2 = './pytests/expections/test_cc/test_django_project'


    assert are_dir_trees_equal(dir1, dir2) == []

def test_update_url_2(init_project_with_app):

    f = open(os.path.join(init_project_with_app, 'test_app_one/sdc_urls.py' ), 'r')
    text = ''
    for line in f:
        if 'test_sdc_one' in line:
            line = re.sub(r'path[^,]+', "path('test_sdc_one/<int:test>'", line)
        text += line
    f.close()
    f = open(os.path.join(init_project_with_app, 'test_app_one/sdc_urls.py' ), 'w')
    f.write(text)
    f.close()



    subprocess.run(['python', 'manage.py', 'sdc_update_url'], stdout=subprocess.PIPE, cwd=init_project_with_app)
    dir1 = init_project_with_app
    dir2 = './pytests/expections/test_update_url/test_django_project'


    assert are_dir_trees_equal(dir1, dir2) == []