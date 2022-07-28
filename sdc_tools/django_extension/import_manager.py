import importlib


def import_function(string_path):
    if string_path is not None:
        p, m = string_path.rsplit('.', 1)
        mod = importlib.import_module(p)
        met = getattr(mod, m)
        return met


    return None

def import_functions(func_map):
    if func_map == None:
        return
    for key in func_map:
        yield key, import_function(func_map[key])