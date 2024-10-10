import importlib


def import_function(string_path: str) -> any:
    """
    Imports a function or a property using a python import sting (path separated by dots)

    :param string_path: python import sting
    :return: callable function, property or None
    """

    if string_path is not None:
        p, m = string_path.rsplit('.', 1)
        mod = importlib.import_module(p)
        met = getattr(mod, m)
        return met

    return None
