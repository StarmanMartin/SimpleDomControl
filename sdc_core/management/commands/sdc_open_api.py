import copy

from django.contrib.auth import get_user_model
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


def _form(model, key):
    form_attr = getattr(model.SdcMeta, key, None)
    if form_attr is None:
        return None
    return resolve_form(form_attr)


def _add_model(openapi, model_name, model, model_name_lower):
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
            "summary": f"Get list of {model_name}. Privilege: model:{model_name}:read.",
            "parameters": [copy.deepcopy(FILTER_PARAMETER)],
            "responses": {
                "200": {"description": "Successful response", "content": list_response},
                **copy.deepcopy(ERROR_RESPONSES),
            },
        },
    }
    instance_path = {
        "get": {
            "summary": f"Get instance {model_name}. Privilege: model:{model_name}:read.",
            "parameters": [copy.deepcopy(ID_PARAMETER)],
            "responses": {
                "200": {"description": "Successful response", "content": copy.deepcopy(instance_response)},
                **copy.deepcopy(ERROR_RESPONSES),
            },
        },
        "delete": {
            "summary": f"Delete {model_name}. Privilege: model:{model_name}:delete.",
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

    create_form = _form(model, "create_form")
    if create_form is not None:
        schemas[f"{model_name}Create"], has_files = generate_form_schema(create_form)
        list_path["post"] = {
            "summary": f"Create {model_name}. Privilege: model:{model_name}:write.",
            "requestBody": {"required": True, "content": request_content(f"{model_name}Create", has_files)},
            "responses": {
                "200": {"description": "Created", "content": copy.deepcopy(instance_response)},
                "400": copy.deepcopy(VALIDATION_ERROR_RESPONSE),
                **copy.deepcopy(ERROR_RESPONSES),
            },
        }

    edit_form = _form(model, "edit_form")
    if edit_form is not None:
        schemas[f"{model_name}Edit"], has_files = generate_form_schema(edit_form)
        schemas[f"{model_name}Patch"], _ = generate_form_schema(edit_form, partial=True)
        for method, schema_name, summary, description in (
                ("put", f"{model_name}Edit", f"Replace {model_name}", "Updated"),
                ("patch", f"{model_name}Patch", f"Partial update {model_name}", "Patched"),
        ):
            instance_path[method] = {
                "summary": f"{summary}. Privilege: model:{model_name}:write.",
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


TOKEN_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        "name": {"type": "string"},
        "kind": {"type": "string", "enum": ["personal", "login"]},
        "prefix": {"type": "string", "description": "First characters of the token, to recognize it"},
        "privileges": {"type": "array", "items": {"type": "string"}},
        "created_at": {"type": "string", "format": "date-time"},
        "expires_at": {"type": "string", "format": "date-time", "nullable": True},
        "last_used_at": {"type": "string", "format": "date-time", "nullable": True},
        "revoked_at": {"type": "string", "format": "date-time", "nullable": True},
        "created_by_token": {"type": "string", "format": "uuid", "nullable": True},
        "is_valid": {"type": "boolean"},
    },
}

PRIVILEGES_DESCRIPTION = (
    "Privileges of a token: model:<Model>:read, model:<Model>:write (create and change), model:<Model>:delete, "
    "model:*:<read|write|delete> for all models, account:read, account:write, account:tokens. A token never has "
    "more rights than its user."
)


def _token_response(description, extra=None):
    return {
        "description": description,
        "content": {"application/json": {"schema": {"type": "object", "properties": {
            "success": {"type": "boolean"},
            **(extra or {}),
            "data": {"$ref": "#/components/schemas/ApiToken"},
        }}}},
    }


def _privilege(text, privilege):
    return f"{text} Privilege: {privilege}."


def _auth_paths():
    login_response = {
        "200": {
            "description": "A login token",
            "content": {"application/json": {"schema": {"type": "object", "properties": {
                "access_token": {"type": "string"},
                "token_type": {"type": "string", "enum": ["bearer"]},
                "token_id": {"type": "string", "format": "uuid"},
                "expires_at": {"type": "string", "format": "date-time"},
                "privileges": {"type": "array", "items": {"type": "string"}},
            }}}},
        },
        "401": {"description": "Invalid credentials or token"},
    }
    token_id = {"in": "path", "name": "token_id", "required": True, "schema": {"type": "string", "format": "uuid"}}
    return {
        "/sdc_api/login/": {
            "get": {
                "summary": "Deprecated: exchange a refresh JWT of SDC <= 0.162 for a login token",
                "deprecated": True,
                "responses": copy.deepcopy(login_response) | {"410": {"description": "Not a JWT"}},
            },
            "post": {
                "summary": "Log in with username and password and receive a short-lived login token",
                "description": PRIVILEGES_DESCRIPTION + " Without privileges the token gets all of them.",
                "security": [],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {
                    "type": "object",
                    "required": ["username", "password"],
                    "properties": {
                        "username": {"type": "string"},
                        "password": {"type": "string", "format": "password"},
                        "name": {"type": "string"},
                        "privileges": {"type": "array", "items": {"type": "string"}},
                    },
                }}}},
                "responses": copy.deepcopy(login_response) | {
                    "400": {"description": "Missing credentials, invalid JSON or unknown privileges"}},
            },
        },
        "/sdc_api/tokens/": {
            "get": {
                "summary": _privilege("List the own API tokens (also revoked and expired ones).", "account:read"),
                "responses": {"200": {"description": "The tokens", "content": {"application/json": {"schema": {
                    "type": "object", "properties": {
                        "success": {"type": "boolean"},
                        "data": {"type": "array", "items": {"$ref": "#/components/schemas/ApiToken"}},
                    }}}}}, **copy.deepcopy(ERROR_RESPONSES)},
            },
            "post": {
                "summary": _privilege("Create an API token with at most the privileges of the calling token.",
                                      "account:tokens"),
                "description": PRIVILEGES_DESCRIPTION + " The token is returned only in this response.",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string"},
                        "privileges": {"type": "array", "items": {"type": "string"},
                                       "description": "Default: the privileges of the calling token"},
                        "expires_at": {"type": "string", "format": "date-time", "nullable": True,
                                       "description": "Default: the default lifetime; null: no expiry"},
                    },
                }}}},
                "responses": {
                    "201": _token_response("The new token", {"token": {"type": "string"}}),
                    "400": {"description": "Invalid name, privileges or expiry"},
                    **copy.deepcopy(ERROR_RESPONSES),
                },
            },
        },
        "/sdc_api/tokens/current/": {
            "get": {
                "summary": "The calling token",
                "responses": {"200": _token_response("The token"), **copy.deepcopy(ERROR_RESPONSES)},
            },
        },
        "/sdc_api/tokens/{token_id}/": {
            "get": {
                "summary": _privilege("One own API token.", "account:read"),
                "parameters": [copy.deepcopy(token_id)],
                "responses": {"200": _token_response("The token"), **copy.deepcopy(ERROR_RESPONSES)},
            },
            "delete": {
                "summary": _privilege("Revoke an own API token and the tokens created with it.", "account:tokens"),
                "parameters": [copy.deepcopy(token_id)],
                "responses": {"200": _token_response("The revoked token"), **copy.deepcopy(ERROR_RESPONSES)},
            },
        },
    }


def _account_path():
    user_model = get_user_model()
    if all_models().get(user_model.__name__) is not user_model:
        return {}
    name = user_model.__name__
    instance = {"application/json": {"schema": {"type": "object", "properties": {
        "success": {"type": "boolean"}, "data": {"$ref": f"#/components/schemas/{name}"}}}}}
    return {"/sdc_api/account/": {
        "get": {
            "summary": _privilege("The own user record.", "account:read"),
            "responses": {"200": {"description": "The user", "content": instance}, **copy.deepcopy(ERROR_RESPONSES)},
        },
        "patch": {
            "summary": _privilege("Change the own profile; password, e-mail and username cannot be changed with "
                                  "a token.", "account:write"),
            "requestBody": {"required": True, "content": {"application/json": {"schema": {
                "type": "object", "additionalProperties": True}}}},
            "responses": {
                "200": {"description": "Changed", "content": copy.deepcopy(instance)},
                "400": copy.deepcopy(VALIDATION_ERROR_RESPONSE),
                **copy.deepcopy(ERROR_RESPONSES),
            },
        },
    }}


def build_openapi():
    """The OpenAPI 3 description of the REST API (``sdc_core.api_urls``) as a dict."""
    openapi = {
        "openapi": "3.0.3",
        "info": {
            "title": "Auto Generated API",
            "version": "1.0.0",
            "description": "REST API of the SdcModels. Authenticate with an API token (Authorization: Bearer "
                           "sdc_...), created by the user in the web app or with POST /sdc_api/login/. "
                           + PRIVILEGES_DESCRIPTION,
        },
        "paths": _auth_paths(),
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "SDC API token",
                }
            },
            "schemas": {"ApiToken": copy.deepcopy(TOKEN_SCHEMA)},
        },
        "security": [
            {
                "BearerAuth": []
            }
        ],
    }
    for model_name, model in all_models().items():
        _add_model(openapi, model_name, model, model_name.lower())
    openapi["paths"].update(_account_path())
    return openapi


class Command(BaseCommand):
    help = "Writes openapi.generated.yaml, an OpenAPI 3 description of the SDC REST API (sdc_api/...)."

    def handle(self, *args, **opts):
        openapi = build_openapi()
        with open("openapi.generated.yaml", "w") as f:
            yaml.safe_dump(
                openapi,
                f,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
            )

        self.stdout.write("Generated openapi.generated.yaml")
