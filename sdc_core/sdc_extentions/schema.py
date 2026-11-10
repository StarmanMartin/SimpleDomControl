"""
JSON schemas of SdcModels and their forms, shared by the OpenAPI description (``sdc_open_api``) and other API
descriptions of the SDC models.
"""
import copy

from django import forms
from django.db import models
from django.forms.models import ModelChoiceIterator

from sdc_core.sdc_extentions.models import filter_model_fields


# Looked up along the class hierarchy of a field (most specific class first), so e.g.
# DateTimeField wins over DateField and EmailField over CharField.
TYPE_MAPPING = {
    models.AutoField: {"type": "integer"},
    models.BigAutoField: {"type": "integer"},
    models.SmallAutoField: {"type": "integer"},
    models.IntegerField: {"type": "integer"},
    models.BigIntegerField: {"type": "integer"},
    models.SmallIntegerField: {"type": "integer"},
    models.FloatField: {"type": "number", "format": "float"},
    models.DecimalField: {"type": "string", "format": "decimal"},
    models.BooleanField: {"type": "boolean"},
    models.CharField: {"type": "string"},
    models.TextField: {"type": "string"},
    models.SlugField: {"type": "string"},
    models.EmailField: {"type": "string", "format": "email"},
    models.URLField: {"type": "string", "format": "uri"},
    models.UUIDField: {"type": "string", "format": "uuid"},
    models.DateField: {"type": "string", "format": "date"},
    models.DateTimeField: {"type": "string", "format": "date-time"},
    models.TimeField: {"type": "string", "format": "time"},
    models.JSONField: {},
    models.FileField: {
        "type": "object",
        "nullable": True,
        "properties": {"name": {"type": "string"}, "url": {"type": "string"}},
    },
    models.ForeignKey: {"type": "integer", "nullable": True},
    models.OneToOneField: {"type": "integer", "nullable": True},
    models.ManyToManyField: {"type": "array", "items": {"type": "integer"}},
    forms.CharField: {"type": "string"},
    forms.EmailField: {"type": "string", "format": "email"},
    forms.URLField: {"type": "string", "format": "uri"},
    forms.SlugField: {"type": "string"},
    forms.IntegerField: {"type": "integer"},
    forms.FloatField: {"type": "number"},
    forms.DecimalField: {"type": "number"},
    forms.BooleanField: {"type": "boolean"},
    forms.DateField: {"type": "string", "format": "date"},
    forms.DateTimeField: {"type": "string", "format": "date-time"},
    forms.TimeField: {"type": "string", "format": "time"},
    forms.UUIDField: {"type": "string", "format": "uuid"},
    forms.JSONField: {},
    forms.ModelChoiceField: {"type": "integer"},
    forms.ModelMultipleChoiceField: {"type": "array", "items": {"type": "integer"}},
    forms.MultipleChoiceField: {"type": "array", "items": {"type": "string"}},
    forms.FileField: {"type": "string", "format": "binary"},
    forms.Field: {"type": "string"},
}

FILE_FIELDS = (forms.FileField, models.FileField)


def plain_text(value):
    """A plain ``str`` (lazy translations and SafeString would be dumped as Python objects)."""
    return str(value).encode().decode()


def schema_for(field):
    for cls in type(field).__mro__:
        if cls in TYPE_MAPPING:
            return copy.deepcopy(TYPE_MAPPING[cls])
    return {"type": "string"}


def is_file_field(field):
    return isinstance(field, FILE_FIELDS)


def form_field_to_schema(field):
    schema = schema_for(field)

    if getattr(field, "max_length", None):
        schema["maxLength"] = field.max_length
    if getattr(field, "min_length", None):
        schema["minLength"] = field.min_length
    if field.help_text:
        schema["description"] = plain_text(field.help_text)

    choices = getattr(field, "choices", None)
    if choices:
        if isinstance(choices, ModelChoiceIterator):
            model_name = choices.queryset.model.__name__
            schema["description"] = plain_text(f"A {model_name} id. {schema.get('description', '')}".strip())
        elif not isinstance(field, forms.MultipleChoiceField):
            values = [value for value, _label in choices if value not in ("", None)]
            if values:
                schema["enum"] = values

    return schema, is_file_field(field)


def generate_form_schema(form_class, partial=False):
    form = form_class()

    properties = {}
    required = []
    has_files = False

    for name, field in form.fields.items():
        properties[name], is_file = form_field_to_schema(field)
        has_files |= is_file

        if field.required and not partial:
            required.append(name)

    schema = {
        "type": "object",
        "properties": properties,
    }

    if required:
        schema["required"] = required

    return schema, has_files


def generate_fields_schema(model):
    """Schema of the ``fields`` object of a serialized instance (without the pk)."""
    all_fields = {}
    for field in list(model._meta.concrete_fields) + list(model._meta.many_to_many):
        if field.primary_key:
            continue
        all_fields[field.name] = field

    properties = {}
    for name, field in filter_model_fields(model, all_fields).items():
        schema = schema_for(field)
        if getattr(field, "max_length", None) and schema.get("type") == "string":
            schema["maxLength"] = field.max_length
        if field.help_text:
            schema["description"] = plain_text(field.help_text)
        if getattr(field, "null", False) and schema:
            schema["nullable"] = True
        properties[name] = schema

    return {"type": "object", "properties": properties}


def generate_instance_schema(model_name):
    """Schema of one serialized instance: ``{"model": ..., "pk": ..., "fields": {...}}``."""
    return {
        "type": "object",
        "required": ["model", "pk", "fields"],
        "properties": {
            "model": {"type": "string", "description": "app_label.modelname"},
            "pk": {"type": "integer"},
            "fields": {"$ref": f"#/components/schemas/{model_name}Fields"},
        },
    }


def generate_schema(model):
    """Backwards-compatible alias: the schema of the ``fields`` object."""
    return generate_fields_schema(model)
