import os
import shutil
import subprocess
import sys

from pytests.utils import are_dir_trees_equal
from sdc_manager.management.commands.init_add import options
from sdc_manager.management.commands.init_add.utils import prepare_as_string ,copy



def test_copy():
    try:
        os.makedirs('./pytests/test_res')
    except:
        pass
    copy('./sdc_manager/template_files/Assets', './pytests/test_res/', options.REPLACEMENTS)
    assert os.path.exists('./pytests/test_res/src')
    assert os.path.exists('./pytests/test_res/src/index.style.scss')
    assert os.path.exists('./pytests/test_res/src/index.organizer.js')

    try:
        shutil.rmtree('./pytests/test_res')
    except:
        pass

def test_init():
    try:
        shutil.copytree('./pytests/test_django_project(DUMMY)', './pytests/test_django_project')
        subprocess.run([sys.executable, 'manage.py', 'sdc_init'], stdout=subprocess.PIPE, cwd=(os.path.join(os.getcwd(), './pytests/test_django_project')))
        dir1 = './pytests/test_django_project'
        dir2 = './pytests/expections/test_init/test_django_project'


        assert are_dir_trees_equal(dir1, dir2) == []
    except:
        assert False
        pass
    finally:
        shutil.rmtree('./pytests/test_django_project')