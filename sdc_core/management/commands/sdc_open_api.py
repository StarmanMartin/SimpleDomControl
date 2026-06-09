import copy

from django import forms
from django.forms.models import ModelChoiceIterator
from django.utils.module_loading import import_string
from django.core.management.base import BaseCommand

import yaml

from django.db import models

from sdc_core.sdc_extentions.models import all_models

TYPE_MAPPING = {
    models.AutoField: {"type": "integer"},
    models.BigAutoField: {"type": "integer"},
    models.IntegerField: {"type": "integer"},
    models.BigIntegerField: {"type": "integer"},
    models.FloatField: {"type": "number", "format": "float"},
    models.DecimalField: {"type": "number", "format": "double"},
    models.BooleanField: {"type": "boolean"},
    models.CharField: {"type": "string"},
    models.TextField: {"type": "string"},
    models.EmailField: {"type": "string", "format": "email"},
    models.URLField: {"type": "string", "format": "uri"},
    models.UUIDField: {"type": "string", "format": "uuid"},
    models.DateField: {"type": "string", "format": "date"},
    models.DateTimeField: ("string", "date-time"),
    models.TimeField: {"type": "string", "format": "time"},
    models.JSONField: {"type": "object"},
    models.FileField: {"type": "object"},
    models.ImageField: {"type": "object"},
    forms.CharField: {"type": "string"},
    forms.EmailField: {"type": "string", "format": "email"},
    forms.URLField: {"type": "string", "format": "uri"},
    forms.IntegerField: {"type": "integer"},
    forms.ModelChoiceField: {"type": "integer"},
    forms.FloatField: {"type": "number"},
    forms.DecimalField: {"type": "number"},
    forms.BooleanField: {"type": "boolean"},
    forms.DateField: {"type": "string", "format": "date"},
    forms.DateTimeField: ("string", "date-time"),
    forms.TimeField: {"type": "string", "format": "time"},
    forms.UUIDField: {"type": "string", "format": "uuid"},
    forms.JSONField: {"type": "object"},
    forms.FileField: {"type": "string", "format": "binary"},
    forms.ImageField: {"type": "string", "format": "binary"},
    forms.Field: {"type": "string"},
}

FILE_FIELDS = [forms.FileField, forms.ImageField, models.FileField, models.ImageField]

def is_file_field(field):
    return any(isinstance(field, FileField) for FileField in FILE_FIELDS)


def form_field_to_schema(field):
    for field_type, schema_pattern in TYPE_MAPPING.items():
        if isinstance(field, field_type):
            schema = copy.deepcopy(schema_pattern)

            if getattr(field, "max_length", None):
                schema["maxLength"] = field.max_length

            if getattr(field, "min_length", None):
                schema["minLength"] = field.min_length

            if field.help_text:
                schema["description"] = str(field.help_text)

            if getattr(field, "choices", None):
                values = []
                if isinstance(field.choices, ModelChoiceIterator):
                    schema["description"] = f"A {field.choices.queryset.model.__name__} id. {schema.get("description", "")}"

                else:
                    for value, label in field.choices:
                        if value not in ("", None):
                            values.append(value)

                if values:
                    schema["enum"] = values

            return schema, is_file_field(field)

    return {"type": "string"},  is_file_field(field)


def generate_form_schema(form_class, partial=False):
    form = form_class()

    properties = {}
    required = []
    is_file = False

    for name, field in form.fields.items():
        properties[name], _is_file = form_field_to_schema(field)
        is_file |= _is_file

        if field.required and not partial:
            required.append(name)

    schema = {
        "type": "object",
        "properties": properties,
    }

    if required:
        schema["required"] = required

    return schema, "multipart/form-data" if is_file else "application/json"


def field_to_schema(field):
    for django_type, schema_pattern in TYPE_MAPPING.items():
        if isinstance(field, django_type):
            schema = copy.deepcopy(schema_pattern)

            if hasattr(field, "max_length") and field.max_length:
                schema["maxLength"] = field.max_length

            return schema

    if isinstance(field, models.ForeignKey):
        return {
            "type": "integer"
        }

    return {
        "type": "string"
    }


def generate_schema(model):
    properties = {}
    required = []

    for field in model._meta.fields:

        # skip reverse relations
        if field.auto_created and not field.concrete:
            continue

        properties[field.name] = field_to_schema(field)

        if (
                not field.null
                and not field.blank
                and not field.auto_created
                and not isinstance(field, models.AutoField)
        ):
            required.append(field.name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def generate_patch_schema(model):
    properties = {}

    for field in model._meta.fields:

        if field.auto_created and not field.concrete:
            continue

        properties[field.name] = field_to_schema(field)

    return {
        "type": "object",
        "properties": properties,
    }


class Command(BaseCommand):
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
                "description": "Invalid credentials"
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
                        "summary": "Refresh JWT token",
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

                        "responses": copy.deepcopy(login_response)
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
            model_name_lower = model_name.lower()
            self._add_model(openapi, model_name, model, model_name_lower)

        with open("openapi.generated.yaml", "w") as f:
            yaml.dump(
                openapi,
                f,
                sort_keys=False,
                default_flow_style=False,
            )

        print("Generated openapi.generated.yaml")

    def _add_model(self, openapi, model_name, model, model_name_lower):
        # schemas
        openapi["components"]["schemas"][model_name] = generate_schema(model)
        edit_form = import_string(model.SdcMeta.edit_form)
        create_form = import_string(model.SdcMeta.create_form)
        openapi["components"]["schemas"][f"{model_name}Create"], content_type_create = generate_form_schema(create_form)
        openapi["components"]["schemas"][f"{model_name}Edit"], content_type_edit = generate_form_schema(edit_form)

        openapi["components"]["schemas"][f"{model_name}Patch"], content_type_path = generate_form_schema(edit_form, True)

        response_content = {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "data": {
                            "$ref": f"#/components/schemas/{model_name}"
                        }
                    }
                }
            }
        }

        # paths
        openapi["paths"][f"/sdc_api/{model_name_lower}/"] = {
            "get": {
                "summary": f"Get list of {model_name}",

                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "success": {"type": "boolean"},
                                        "data": {
                                            "type": "array",
                                            "items": {
                                                "$ref": (
                                                    f"#/components/schemas/{model_name}"
                                                )
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "post": {
                "summary": f"Create {model_name}",
                "requestBody": {
                    "required": True,
                    "content": {
                        content_type_create: {
                            "schema": {
                                "$ref": (
                                    f"#/components/schemas/{model_name}Create"
                                )
                            }
                        }
                    },
                },
                "responses": {
                    "201": {
                        "description": "Created",
                        "content": copy.deepcopy(response_content)
                    }
                },
            }
        }

        openapi["paths"][f"/sdc_api/{model_name_lower}/{{id}}/"] = {
            "get": {
                "summary": f"Get instance {model_name}",
                "parameters": [
                    {
                        "in": "path",
                        "name": "id",
                        "required": True,
                        "schema": {
                            "type": "integer"
                        },
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": copy.deepcopy(response_content)
                    }
                }
            },
            "put": {
                "summary": f"Replace {model_name}",
                "parameters": [
                    {
                        "in": "path",
                        "name": "id",
                        "required": True,
                        "schema": {
                            "type": "integer"
                        },
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        content_type_edit: {
                            "schema": {
                                "$ref": (
                                    f"#/components/schemas/{model_name}Edit"
                                )
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Updated",
                        "content": copy.deepcopy(response_content)
                    }
                },
            },

            "patch": {
                "summary": f"Partial update {model_name}",
                "parameters": [
                    {
                        "in": "path",
                        "name": "id",
                        "required": True,
                        "schema": {
                            "type": "integer"
                        },
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        content_type_path: {
                            "schema": {
                                "$ref": (
                                    f"#/components/schemas/"
                                    f"{model_name}Patch"
                                )
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Patched",
                        "content": copy.deepcopy(response_content)
                    }
                },
            },
        }
