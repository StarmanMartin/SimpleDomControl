import copy

from django import forms
from django.core.management.base import BaseCommand
from django.db import models
from django.forms.models import ModelChoiceIterator

import yaml

from sdc_core.sdc_extentions.models import all_models, filter_model_fields, resolve_form

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

ID_PARAMETER = {
    "in": "path",
    "name": "id",
    "required": True,
    "schema": {"type": "integer"},
}

FILTER_PARAMETER = {
    "in": "query",
    "name": "filter",
    "description": "Django field lookups on the exposed fields, e.g. ?title=Dune or ?age__gte=18.",
    "required": False,
    "style": "form",
    "explode": True,
    "schema": {"type": "object", "additionalProperties": {"type": "string"}},
}

ERROR_RESPONSES = {
    "401": {"description": "Missing, invalid or expired token"},
    "403": {"description": "Not authorised"},
    "404": {"description": "Not found"},
}

VALIDATION_ERROR_RESPONSE = {
    "description": "Validation errors",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "errors": {
                        "type": "object",
                        "additionalProperties": {"type": "array", "items": {"type": "string"}},
                    },
                },
            }
        }
    },
}


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


def request_content(schema_name, has_files):
    ref = {"schema": {"$ref": f"#/components/schemas/{schema_name}"}}
    if has_files:
        return {"multipart/form-data": copy.deepcopy(ref)}
    return {
        "application/json": copy.deepcopy(ref),
        "application/x-www-form-urlencoded": copy.deepcopy(ref),
        "multipart/form-data": copy.deepcopy(ref),
    }


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


class Command(BaseCommand):
    help = "Writes openapi.generated.yaml, an OpenAPI 3 description of the SDC REST API (sdc_api/...)."

    def handle(self, *args, **opts):
        login_response = {
            "200": {
                "description": "JWT tokens",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "access_token": {
                                    "type": "string"
                                },
                                "refresh_token": {
                                    "type": "string"
                                },
                                "token_type": {
                                    "type": "string"
                                },
                            },
                        }
                    }
                },
            },

            "401": {
                "description": "Invalid credentials or token"
            },
        }

        openapi = {
            "openapi": "3.0.3",
            "info": {
                "title": "Auto Generated API",
                "version": "1.0.0",
            },
            "paths": {
                "/sdc_api/login/": {
                    "get": {
                        "summary": "Refresh JWT token (send the refresh token as Bearer token)",
                        "responses": copy.deepcopy(login_response)
                    },
                    "post": {
                        "summary": "Login and receive JWT token",

                        "security": [],

                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": [
                                            "username",
                                            "password"
                                        ],
                                        "properties": {
                                            "username": {
                                                "type": "string"
                                            },
                                            "password": {
                                                "type": "string",
                                                "format": "password"
                                            },
                                        },
                                    }
                                }
                            },
                        },

                        "responses": copy.deepcopy(login_response) | {
                            "400": {"description": "Missing credentials or invalid JSON"}
                        }
                    }

                },
            },
            "components": {
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                    }
                },
                "schemas": {
                }
            },
            "security": [
                {
                    "BearerAuth": []
                }
            ]
        }

        for model_name, model in all_models().items():
            self._add_model(openapi, model_name, model, model_name.lower())

        with open("openapi.generated.yaml", "w") as f:
            yaml.safe_dump(
                openapi,
                f,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
            )

        self.stdout.write("Generated openapi.generated.yaml")

    @staticmethod
    def _form(model, key):
        form_attr = getattr(model.SdcMeta, key, None)
        if form_attr is None:
            return None
        return resolve_form(form_attr)

    def _add_model(self, openapi, model_name, model, model_name_lower):
        schemas = openapi["components"]["schemas"]
        schemas[model_name] = generate_instance_schema(model_name)
        schemas[f"{model_name}Fields"] = generate_fields_schema(model)

        instance_response = {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "data": {"$ref": f"#/components/schemas/{model_name}"},
                    },
                }
            }
        }
        list_response = {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "data": {"type": "array", "items": {"$ref": f"#/components/schemas/{model_name}"}},
                    },
                }
            }
        }

        list_path = {
            "get": {
                "summary": f"Get list of {model_name}",
                "parameters": [copy.deepcopy(FILTER_PARAMETER)],
                "responses": {
                    "200": {"description": "Successful response", "content": list_response},
                    **copy.deepcopy(ERROR_RESPONSES),
                },
            },
        }
        instance_path = {
            "get": {
                "summary": f"Get instance {model_name}",
                "parameters": [copy.deepcopy(ID_PARAMETER)],
                "responses": {
                    "200": {"description": "Successful response", "content": copy.deepcopy(instance_response)},
                    **copy.deepcopy(ERROR_RESPONSES),
                },
            },
            "delete": {
                "summary": f"Delete {model_name}",
                "parameters": [copy.deepcopy(ID_PARAMETER)],
                "responses": {
                    "200": {
                        "description": "Deleted",
                        "content": {
                            "application/json": {
                                "schema": {"type": "object", "properties": {"success": {"type": "boolean"}}}
                            }
                        },
                    },
                    **copy.deepcopy(ERROR_RESPONSES),
                },
            },
        }

        create_form = self._form(model, "create_form")
        if create_form is not None:
            schemas[f"{model_name}Create"], has_files = generate_form_schema(create_form)
            list_path["post"] = {
                "summary": f"Create {model_name}",
                "requestBody": {"required": True, "content": request_content(f"{model_name}Create", has_files)},
                "responses": {
                    "200": {"description": "Created", "content": copy.deepcopy(instance_response)},
                    "400": copy.deepcopy(VALIDATION_ERROR_RESPONSE),
                    **copy.deepcopy(ERROR_RESPONSES),
                },
            }

        edit_form = self._form(model, "edit_form")
        if edit_form is not None:
            schemas[f"{model_name}Edit"], has_files = generate_form_schema(edit_form)
            schemas[f"{model_name}Patch"], _ = generate_form_schema(edit_form, partial=True)
            for method, schema_name, summary, description in (
                    ("put", f"{model_name}Edit", f"Replace {model_name}", "Updated"),
                    ("patch", f"{model_name}Patch", f"Partial update {model_name}", "Patched"),
            ):
                instance_path[method] = {
                    "summary": summary,
                    "parameters": [copy.deepcopy(ID_PARAMETER)],
                    "requestBody": {"required": True, "content": request_content(schema_name, has_files)},
                    "responses": {
                        "200": {"description": description, "content": copy.deepcopy(instance_response)},
                        "400": copy.deepcopy(VALIDATION_ERROR_RESPONSE),
                        **copy.deepcopy(ERROR_RESPONSES),
                    },
                }

        openapi["paths"][f"/sdc_api/{model_name_lower}/"] = list_path
        openapi["paths"][f"/sdc_api/{model_name_lower}/{{id}}/"] = instance_path
