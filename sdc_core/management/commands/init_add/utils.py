import os
import re
import shutil
from typing import Callable


def copy_and_prepare(src, des, map_val, overwrite_handler: Callable[[str], bool] = None):
    try:
        with open(src, "r", encoding='utf-8') as fin:
            os.makedirs(os.path.dirname(des), exist_ok=True)
            if os.path.exists(des) and (overwrite_handler is None or not overwrite_handler(f"Would you like to overwrite {des}?")):
                return
            with open(des, "w+", encoding='utf-8') as fout:
                for line in fin:
                    for key in map_val:
                        line = line.replace(key, map_val[key])
                    fout.write(line)
    except UnicodeDecodeError:
        shutil.copy(src, des)

def prepare_as_string(src, map_val):
    with open(src, "rt", encoding='utf-8') as fin:
        out = ""
        for line in fin:
            for key in map_val:
                line = line.replace(key, map_val[key])
            out += line
    return out


def copy(src, dest, map_val, overwrite_handler: Callable[[str], bool] = None):
    if os.path.isdir(src):
        for root, dirs, files in os.walk(src):
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')
            rel_path = os.path.relpath(root, src)
            for file in files:
                copy_and_prepare(os.path.join(root, file),
                                 os.path.join(dest, rel_path, file),
                                 map_val, overwrite_handler)

    elif os.path.exists(src):
        copy_and_prepare(src, dest,
                         map_val, overwrite_handler)


def convert_to_snake_case(name):
    s1 = re.sub(' ', r'', name)
    s2 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s1)
    s3 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s2).lower()
    return re.sub('__+', r'_', s3)


def convert_to_camel_case(name):
    snake_str = re.sub(' ', r'', name).lower()
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def convert_to_title_camel_case(name):
    snake_str = re.sub(' ', r'', name).lower()
    components = snake_str.split('_')
    return ''.join(x.title() for x in components)


def convert_to_tag_name(name):
    s1 = re.sub(' ', r'', name)
    s2 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', s1)
    return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s2).lower()
