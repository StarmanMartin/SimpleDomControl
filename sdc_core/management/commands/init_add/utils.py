import errno
import os
import re


def makedirs_if_not_exist(directory):
    try:
        os.makedirs(directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def copy_and_prepare(src, des, map_val):
    fin = open(src, "rt", encoding='utf-8')

    makedirs_if_not_exist(os.path.dirname(des))
    fout = open(des, "wt", encoding='utf-8')

    for line in fin:
        for key in map_val:
            line = line.replace(key, map_val[key])
        fout.write(line)

    fin.close()
    fout.close()


def prepare_as_string(src, map_val):
    fin = open(src, "rt", encoding='utf-8')
    fout = ""
    for line in fin:
        for key in map_val:
            line = line.replace(key, map_val[key])
        fout += line

    fin.close()
    return fout


def copy(src, dest, map_val):
    if os.path.isdir(src):
        for root, dirs, files in os.walk(src):
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')
            rel_path = os.path.relpath(root, src)
            for file in files:
                copy_and_prepare(os.path.join(root, file),
                                 os.path.join(dest, rel_path, file),
                                 map_val)

    elif os.path.exists(src):
        copy_and_prepare(src, dest,
                         map_val)



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
