import os
import shutil
import subprocess

from pytests.utils import are_dir_trees_equal


def test_update_version(init_project_with_app):
    """
    :param init_project_with_app:
    :return:
    """

    """
    f = open(os.path.join(init_project_with_app, 'test_django_project/settings.py' ), 'r')
    text = ''
    for line in f:
        if "'sdc_user'" in line:
            line = re.sub(r'^(\s+)[^\s\n,]+', r"\1'sdc_user'", line)
        text += line
    f.close()
    f = open(os.path.join(init_project_with_app, 'test_django_project/settings.py' ), 'w')
    f.write(text)
    f.close()
    """
    shutil.rmtree(os.path.join(init_project_with_app, 'Assets/webpack.config'))
    os.remove(os.path.join(init_project_with_app, 'Assets/gulpfile.js'))
    os.remove(os.path.join(init_project_with_app, 'Assets/package.json'))
    os.remove(os.path.join(init_project_with_app, 'Assets/.babelrc'))
    subprocess.run(['python', 'manage.py', 'sdc_update_version'], stdout=subprocess.PIPE, cwd=init_project_with_app)
    dir1 = init_project_with_app
    dir2 = './pytests/expections/test_update_version/test_django_project'


    assert are_dir_trees_equal(dir1, dir2) == []