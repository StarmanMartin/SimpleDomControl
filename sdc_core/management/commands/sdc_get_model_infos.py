import inspect
import json
import os

from django.core.management.base import BaseCommand
from django.apps import apps
from django.template.loader import get_template

from sdc_core.management.commands.init_add import options
from sdc_core.sdc_extentions.import_manager import import_function


class Command(BaseCommand):
    help = 'This function returns all infos to all models'

    def add_arguments(self, parser):
        pass

    def _get_class_line_number(self, class_or_function):
        return inspect.getsourcelines(class_or_function)[1]

    def _separate_file_class(self, class_path):
        if class_path is None: return None
        try:
            model = import_function(class_path)
        except ImportError or NameError as e:
            return None
        file_path = inspect.getfile(model)
        return {
            'file': file_path,
            'class': model.__name__,
            'line': self._get_class_line_number(model)
        }

    def _parse_model_to_info_json(self, model):
        mi = {
            'name': model.__name__,
            'app': model.__module__.split('.')[0],
            'model_file': inspect.getfile(model),
            'model_file_line': self._get_class_line_number(model),
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
