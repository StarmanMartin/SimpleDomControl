import os
import shutil
import subprocess
import sys

from pytests.utils import are_dir_trees_equal
from sdc_manager.management.commands.init_add import options
from sdc_manager.management.commands.init_add.utils import prepare_as_string ,copy


def test_prepare_as_string():
    assert prepare_as_string('./sdc_manager/template_files/Assets/package.json' ,options.REPLACEMENTS) == '{\n  "name": "Undefined",\n  "version": "1.0.0",\n  "description": "",\n  "private": true,\n  "scripts": {\n    "build": "gulp --mode=production\\n",\n    "develop": "gulp develop --mode=development\\n"\n  },\n  "keywords": [],\n  "author": "",\n  "license": "",\n  "devDependencies": {\n    "@babel/core": "^7.21.0",\n    "@babel/preset-env": "^7.20.2",\n    "babel-loader": "^9.1.2",\n    "css-loader": "^6.7.3",\n    "gulp": "^4.0.2",\n    "gulp-rename": "^2.0.0",\n    "gulp-sass": "^5.1.0",\n    "gulp-sourcemaps": "^3.0.0",\n    "gulp-uglify": "^3.0.2",\n    "jest": "^28.1.3",\n    "sass": "^1.58.3",\n    "sass-loader": "^13.2.0",\n    "style-loader": "^3.3.1",\n    "webpack": "^5.75.0",\n    "webpack-stream": "^7.0.0"\n  },\n  "dependencies": {\n    "bootstrap": "^5.2.3",\n    "jquery": "^3.6.3",\n    "lodash": "^4.17.21"\n  }\n}\n'

def test_copy():
    try:
        os.makedirs('./pytests/test_res')
    except:
        pass
    copy('./sdc_manager/template_files/Assets', './pytests/test_res/', options.REPLACEMENTS)
    assert os.path.exists('./pytests/test_res/src')
    assert os.path.exists('./pytests/test_res/src/index.style.scss')
    assert os.path.exists('./pytests/test_res/src/index.organizer.js')
    assert os.path.exists('./pytests/test_res/src/simpleDomControl/AbstractSDC.js')

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