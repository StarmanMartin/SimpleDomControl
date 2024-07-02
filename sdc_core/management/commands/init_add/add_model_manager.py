import os
import re

from sdc_core.management.commands.init_add.utils import copy

from sdc_core.management.commands.init_add import options


class AddModelManager():
    def __init__(self, app_name: str, model_name: str):
        self.app_name = app_name
        self.model_name = model_name

        self.reps = {**options.REPLACEMENTS, **{'§model_name§': self.model_name,
                                                '§APPNAME§': self.app_name
                                                }}

    def add_model_form(self):
        form_path = os.path.join(options.PROJECT_ROOT, self.app_name, "forms.py")
        data = ''
        if (not os.path.exists(form_path)):
            f = open(form_path, 'w+')
            data = 'from django.forms.models import ModelForm'
        else:
            fin = open(form_path, 'r')
            data = fin.read()
            fin.close()
            f = open(form_path, 'w')

        form_def = "\n".join([
            '\n# Form Model {2}',
            '',
            'class {2}Form(ModelForm):',
            '{0}class Meta:',
            '{0}{0}model = {2}',
            '{0}{0}fields = "__all__"\n',
        ]).format(options.SEP, self.app_name, self.model_name)

        f.write(
            'from {0}.models import {1}\n{2}\n\n{3}'.format(self.app_name, self.model_name, data, form_def))

    def add_model(self):
        model_path = os.path.join(options.PROJECT_ROOT, self.app_name, "models.py")
        if (not os.path.exists(model_path)):
            f = open(model_path, 'w+')
            f.write('from django.db import models')
            f.close()

        self._check_if_sdcmodel_imported(model_path)
        f = open(model_path, 'a')

        search_form_def = "\n".join([]).format(options.SEP, self.app_name, self.model_name)

        class_def = "\n".join([
            'class {2}(models.Model, SdcModel):',
            '{0}class SearchForm(AbstractSearchForm):',
            '{0}{0}"""A default search form used in the list view. You can delete it if you dont need it"""',
            '{0}{0}CHOICES = (("id", "Id"),)',
            '{0}{0}PLACEHOLDER = ""',
            '{0}{0}DEFAULT_CHOICES = CHOICES[0][0]',
            '{0}{0}SEARCH_FIELDS = ("id",)',
            '',
            '{0}class _SdcMeta:',
            '{0}{0}"""Meta data information needed to manage all SDC operations."""',
            '{0}{0}edit_form = "{1}.forms.{2}Form"',
            '{0}{0}create_form = "{1}.forms.{2}Form"',
            '{0}{0}html_list_template = "{1}/models/{2}/{2}_list.html"',
            '{0}{0}html_detail_template = "{1}/models/{2}/{2}_details.html"',
            '',
            '{0}@classmethod\n{0}def render(cls, template_name, context=None, request=None, using=None):\n{0}{0}if template_name == cls.SdcMeta.html_list_template:\n{0}{0}{0}sf = cls.SearchForm(data=context.get("filter", {{}}))\n{0}{0}{0}context = context | handle_search_form(context["instances"], sf,  range=10)\n{0}{0}return render_to_string(template_name=template_name, context=context, request=request, using=using)',
            '',
            '{0}@classmethod\n{0}def is_authorised(cls, user, action, obj):\n{0}{0}return True',
            '',
            '{0}@classmethod\n{0}def get_queryset(cls, user, action, obj):\n{0}{0}return cls.objects.all()',
        ]).format(options.SEP, self.app_name, self.model_name)

        f.write('\n{0}\n\n{1}\n'.format(search_form_def, class_def))
        f.close()

    def add_model_template(self):
        model_path = os.path.join(options.PROJECT_ROOT, self.app_name, "templates", self.app_name, "models", self.model_name)
        if (not os.path.exists(model_path)):
            os.makedirs(model_path)
        files = (('detail.html', '{0}_details.html'.format(self.model_name)),
                 ('list.html', '{0}_list.html'.format(self.model_name)))
        for (src, dst) in files:
            dst_path = os.path.join(model_path, dst)
            src_path = os.path.join(options.SCRIPT_ROOT, 'template_files/models', src)
            if not os.path.exists(dst_path):
                copy(src_path, dst_path, self.reps)

    def _check_if_sdcmodel_imported(self, file_path):
        fin = open(file_path, 'rt')
        data = ""
        new_url_line = 'from sdc_core.sdc_extentions.models import SdcModel\nfrom sdc_core.sdc_extentions.forms import AbstractSearchForm\nfrom django.template.loader import render_to_string\nfrom sdc_core.sdc_extentions.search import handle_search_form'.format(
            self.reps['§PROJECT§'])
        regexp = re.compile(r'import SdcModel')
        for line in fin:
            match = regexp.search(line)
            data += line
            if match:
                return
        fin.close()
        with open(file_path, 'w') as modified:
            modified.write("%s\n%s" % (new_url_line, data))
            modified.close()
