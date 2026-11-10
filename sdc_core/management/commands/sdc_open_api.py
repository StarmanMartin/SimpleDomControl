import copy

from django.core.management.base import BaseCommand

import yaml

from sdc_core.sdc_extentions.models import all_models, resolve_form
from sdc_core.sdc_extentions.schema import generate_fields_schema, generate_form_schema, generate_instance_schema

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


def request_content(schema_name, has_files):
    ref = {"schema": {"$ref": f"#/components/schemas/{schema_name}"}}
    if has_files:
        return {"multipart/form-data": copy.deepcopy(ref)}
    return {
        "application/json": copy.deepcopy(ref),
        "application/x-www-form-urlencoded": copy.deepcopy(ref),
        "multipart/form-data": copy.deepcopy(ref),
    }


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
