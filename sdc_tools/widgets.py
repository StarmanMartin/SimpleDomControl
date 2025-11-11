# widgets.py
import json

from django import forms
from django.db.models import QuerySet
from django.db.models.base import ModelBase


class SearchableSelect(forms.Select):
    template_name = "widgets/searchable_select.html"

    class Media:
        pass

    def __init__(self, attrs=None, choices=(), multiple=False, template_name=None):
        """
        SearchableSelect is a searchable selection widget. It allows you to use models or a list of objects.
        If choices is an instance of ModelBase or QuerySet and the model is an SdcModel, you can
        add a new template: <app>/templates/<app>/models/<filename>.html. Don't forget to add the template
        with the key “html_select_template” to your model's SdcMeta class:

        >>> class ModelName(SdcModel):
        >>>         class _SdcMeta:
        >>>             edit_form = "<app>.forms.<ModelName>ChangeForm"
        >>>             create_form = "<app>.forms.<ModelName>CreationForm"
        >>>             html_list_template = "<app>/models/<app>/<ModelName>_list.html"
        >>>             html_detail_template = "<app>/models/<app>/<ModelName>_details.html"
        >>>             html_select_template = "<app>/models/<app>/<ModelName>_select.html"

        You can also use additionl template. If you set the parameter 'template_name' to a template path then
        all choices will be passed as choices to the template.

        For each option the template (in both: the Sdc template or the additionl template) shoud have a div with the following attributs:

        <div data-value="{{ instance.pk }}" data-search="{{ instance.name }},{{ instance.city }}" class="option-container">
        1. data-value: the selectable value
        2. datra-search: all searchable values seperated by ','
        3. class: option-container

        """
        base_attrs = {"class": "searchable-select"}
        self.ids = None
        self.model_name = None
        if attrs:
            base_attrs.update(attrs)
        if not template_name:
            if isinstance(choices, ModelBase):
                self.model_name = choices.__name__
            elif isinstance(choices, QuerySet):
                self.model_name = choices.model.__name__
                self.ids = list(choices.values_list("id", flat=True))

        self.allow_multiple_selected = multiple
        self.selectable_choices = choices
        self.option_template_name = template_name
        super().__init__(attrs=base_attrs, choices=())

    def format_value(self, value):
        """Ensure we always return a list"""
        res = super().format_value(value)
        if value is None:
            return []
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return [value]
        return res

    def value_from_datadict(self, data, files, name):
        """
        Called during form submission to extract and preprocess the value.
        """
        if not self.allow_multiple_selected:
            res = super().value_from_datadict(data, files, name)
            return res
        raw_value = data.get(name)
        if not raw_value:
            return []
        try:
            if isinstance(raw_value, list) and all(isinstance(x, int) for x in raw_value):
                return raw_value
            if isinstance(raw_value, list) and all(isinstance(x, str) for x in raw_value):
                return raw_value
            if isinstance(raw_value, int):
                return [raw_value]
            return json.loads(raw_value)
        except json.JSONDecodeError:
            # Transform "a,b,c" → ["a", "b", "c"]
            return [v.strip() for v in raw_value[1:-1].split(",") if v.strip()]

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # you can add extra context if needed
        context['widget']['multiple'] = self.allow_multiple_selected
        context['widget']['selectable_choices'] = self.selectable_choices
        context['widget']['option_template_name'] = self.option_template_name
        context['widget']['ids'] = self.ids
        return context | {"model_name": self.model_name}
