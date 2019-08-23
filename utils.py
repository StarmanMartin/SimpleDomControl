import errno
import os
import shutil
import re


def makedirs_if_not_exist(directory):
    try:
        os.makedirs(directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def copy_and_prepare(src, des, map_val):
    fin = open(src, "rt")

    makedirs_if_not_exist(os.path.dirname(des))
    fout = open(des, "wt")

    for line in fin:
        for key in map_val:
            line = line.replace(key, map_val[key])
        fout.write(line)

    fin.close()
    fout.close()


def copy(src, dest):
    try:
        shutil.copytree(src, dest)
    except OSError as e:
        # If the error was caused because the source wasn't a directory
        if e.errno == errno.ENOTDIR:
            shutil.copy(src, dest)
        else:
            print('Directory not copied. Error: %s' % e)


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
