"""Collects the docstrings of all SDC models for the skill file and writes missing ones into the source."""
import ast
import inspect
import os
import textwrap

from django.apps import apps

from sdc_core.sdc_extentions.models import filter_model_fields


def _class_node(source_file, model):
    """The ``ClassDef`` of ``model`` in its source file (closest to the line inspect reports)."""
    with open(source_file) as f:
        tree = ast.parse(f.read())
    try:
        line = inspect.getsourcelines(model)[1]
    except (OSError, TypeError):
        line = 0
    candidates = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == model.__name__]
    return min(candidates, key=lambda n: abs(n.lineno - line), default=None)


def model_doc(model):
    """
    The docstring written in the model class itself. ``model.__doc__`` cannot be used: Django sets an
    auto-generated ``Name(field, ...)`` docstring and subclasses inherit the one of ``SdcModel``.
    """
    try:
        node = _class_node(inspect.getfile(model), model)
    except (OSError, TypeError, SyntaxError):
        return None
    return ast.get_docstring(node) if node else None


def model_fields(model):
    """
    Fields the client can read and write (``SdcMeta.fields`` / ``exclude`` applied):
    ``[{'name', 'type', 'related'}]``; ``related`` is the target model name of relations.
    """
    fields = {f.name: f for f in [*model._meta.concrete_fields, *model._meta.many_to_many]}
    try:
        fields = filter_model_fields(model, fields)
    except Exception:  # noqa: BLE001 - an invalid SdcMeta must not stop the documentation (nor list excluded fields)
        return []
    return [{'name': name, 'type': f.get_internal_type(),
             'related': f.related_model.__name__ if f.is_relation and f.related_model else None}
            for name, f in fields.items()]


def sdc_models():
    """``[{'model', 'name', 'app', 'file', 'doc', 'fields'}]`` for every SDC model, sorted by app and name."""
    result = []
    for model in apps.get_models():
        if not hasattr(model, '__is_sdc_model__'):
            continue
        try:
            file = inspect.getfile(model)
        except TypeError:
            file = None
        result.append({'model': model, 'name': model.__name__, 'app': model._meta.app_label, 'file': file,
                       'doc': model_doc(model), 'fields': model_fields(model)})
    return sorted(result, key=lambda m: (m['app'], m['name']))


def is_editable(file, project_root):
    """Only model files of the project itself are edited, never installed packages."""
    if not file or not os.access(file, os.W_OK):
        return False
    file = os.path.realpath(file)
    return (file.startswith(os.path.realpath(project_root) + os.sep)
            and 'site-packages' not in file.split(os.sep))


def add_class_docstring(model, doc):
    """
    Inserts ``doc`` as docstring directly below the class header of ``model`` in its source file.

    :return: ``True`` if the file was changed
    """
    file = inspect.getfile(model)
    node = _class_node(file, model)
    if node is None or not node.body or ast.get_docstring(node) is not None:
        return False
    with open(file) as f:
        lines = f.read().splitlines(keepends=True)
    first = node.body[0]
    # Comments/decorators of the first statement belong below the docstring
    lineno = min([first.lineno] + [d.lineno for d in getattr(first, 'decorator_list', [])])
    first_line = lines[lineno - 1]
    if first_line[:first.col_offset].strip():
        return False  # one-line class (``class A(B): pass``)
    indent = first_line[:len(first_line) - len(first_line.lstrip())]
    doc = textwrap.dedent(doc).strip().replace('\\', '\\\\').replace('"""', '\\"\\"\\"')
    block = [f'{indent}"""\n'] + [f'{indent}{l}\n'.rstrip(' \t\n') + '\n' for l in doc.splitlines()] + [
        f'{indent}"""\n']
    # Insert above comment lines directly preceding the first statement
    insert_at = lineno - 1
    while insert_at > node.lineno and lines[insert_at - 1].strip().startswith('#'):
        insert_at -= 1
    lines[insert_at:insert_at] = block
    with open(file, 'w') as f:
        f.write(''.join(lines))
    return True
