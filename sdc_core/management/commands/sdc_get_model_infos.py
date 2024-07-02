import json
import os

from django.core.management.base import BaseCommand
from django.apps import apps
from django.template.loader import get_template

from sdc_core.management.commands.init_add import options


class Command(BaseCommand):
    help = 'This function returns all infos to all models'

    def add_arguments(self, parser):
        pass

    def _get_class_line_number(self, file_path, class_name):
        line_number = None

        with open(file_path, 'r') as file:
            for i, line in enumerate(file, start=1):
                # Check if the line contains the class definition
                if f"class {class_name}(" in line:
                    return i

        return line_number

    def _separate_file_class(self, class_path):
        if class_path is None: return None
        class_path = class_path.replace('.', os.path.sep)
        class_path = os.path.join(options.PROJECT_ROOT, class_path)
        file_path = os.path.dirname(class_path) + '.py'
        class_name = os.path.basename(class_path)
        return {
            'file': file_path,
            'class': class_name,
            'line': self._get_class_line_number(file_path, class_name)
        }

    def _parse_model_to_info_json(self, model):
        mi = {
            'name': model.__name__,
            'app': model.__module__.split('.')[0],
            'model_file': os.path.join(options.PROJECT_ROOT, model.__module__.replace('.', os.path.sep) + '.py'),
            'model_file_line': self._get_class_line_number(
                os.path.join(options.PROJECT_ROOT, model.__module__.replace('.', os.path.sep) + '.py'), model.__name__),
            'create_form': self._separate_file_class(model.SdcMeta.create_form),
            'edit_form': self._separate_file_class(model.SdcMeta.edit_form)

        }

        if model.SdcMeta.html_detail_template:
            try:
                mi['html_detail_template'] = get_template(model.SdcMeta.html_detail_template).origin.name
            except:
                pass

        if model.SdcMeta.html_list_template:
            try:
                mi['html_list_template'] = get_template(model.SdcMeta.html_list_template).origin.name
            except:
                pass

        if model.SdcMeta.html_form_template:
            try:
                mi['html_form_template'] = get_template(model.SdcMeta.html_form_template).origin.name
            except:
                pass


        return mi

    def handle(self, *args, **ops):
        all_models = {'sdc_models': [self._parse_model_to_info_json(model) for model in apps.get_models() if
                              hasattr(model, '__is_sdc_model__')]}

        self.stdout.write(json.dumps(all_models, indent=1))
