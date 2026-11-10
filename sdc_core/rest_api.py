import json

import jwt
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseNotFound, QueryDict
from django.utils.datastructures import MultiValueDict
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model

from sdc_core.jwt_utils import jwt_required, generate_jwt, get_auth_token_from_request, \
    verify_refresh_jwt
from sdc_core.sdc_extentions import model_actions

User = get_user_model()


@csrf_exempt
def get_api_token(request):
    if request.method not in ["POST", "GET"]:
        return JsonResponse(
            {"error": "POST required"},
            status=405,
        )
    try:
        if request.method == "GET":
            token, err = get_auth_token_from_request(request)
            if err is not None:
                return err
            try:
                payload, user = verify_refresh_jwt(token)
            except jwt.ExpiredSignatureError:
                return JsonResponse(
                    {"error": "Expired token"},
                    status=401,
                )
            except jwt.InvalidTokenError:
                return JsonResponse(
                    {"error": "Invalid token"},
                    status=401,
                )
            except User.DoesNotExist:
                return JsonResponse(
                    {"error": "User not found"},
                    status=401,
                )

        else:
            data = json.loads(request.body)

            username = data.get("username")
            password = data.get("password")

            if not username or not password:
                return JsonResponse(
                    {"error": "Missing credentials"},
                    status=400,
                )

            user = authenticate(
                request,
                username=username,
                password=password,
            )

        if user is None:
            return JsonResponse(
                {"error": "Invalid credentials"},
                status=401,
            )


        update_last_login(None, user)

        token, refresh_token = generate_jwt(user)

        return JsonResponse({
            "access_token": token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        })

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON"},
            status=400,
        )

    except Exception as e:
        return JsonResponse(
            {"error": str(e) if settings.DEBUG else "Internal server error"},
            status=500,
        )


def _parse_body(request):
    """
    Returns ``(data, files)`` of a POST, PUT or PATCH request. Supported bodies:
    ``application/json`` (an object), ``application/x-www-form-urlencoded`` and
    ``multipart/form-data`` (with file uploads).
    """
    content_type = request.content_type or ''
    if content_type == 'application/json':
        body = json.loads(request.body or b'{}')
        if not isinstance(body, dict):
            raise ValueError("The JSON body must be an object")
        return body, MultiValueDict()
    if request.method == 'POST':
        return request.POST, request.FILES
    if content_type == 'multipart/form-data':
        return request.parse_file_upload(request.META, request)
    return QueryDict(request.body), MultiValueDict()


def _error(message, status):
    return JsonResponse({"success": False, "error": message}, status=status)


def _action_response(action):
    """
    Runs ``action`` (a call of ``model_actions``) and maps its result and errors to the responses of the API:
    ``{"success": true, "data": ...}``, 400 with the form errors, 403, and 404 for records the user cannot reach.
    An unknown model raises ``Http404``.
    """
    try:
        result = action()
    except PermissionDenied as e:
        return HttpResponseForbidden(str(e))
    except ObjectDoesNotExist:
        return HttpResponseNotFound()
    except model_actions.FormValidationError as e:
        return JsonResponse({"success": False, "errors": e.errors}, status=400)
    if result is None:
        return JsonResponse({"success": True})
    return JsonResponse({"success": True, "data": result})


@method_decorator(jwt_required, name="dispatch")
@method_decorator(csrf_exempt, name='dispatch')
class AdcApi(View):
    @staticmethod
    def get_element(model_name):
        return model_actions.get_model(model_name)

    def get(self, request, model, id=None):
        if id is not None:
            return _action_response(lambda: model_actions.get(request.user, model, id))
        return _action_response(lambda: model_actions.load(request.user, model, request.GET))

    def post(self, request, model, id=None):
        if id is not None:
            return _error("Create with POST on the list URL (without id)", 405)
        try:
            data, files = _parse_body(request)
        except ValueError as e:
            return _error(f"Invalid request body: {e}", 400)
        return _action_response(lambda: model_actions.create(request.user, model, data, files))

    def put(self, request, model, id=None):
        return self._update(request, model, id, partial=False)

    def patch(self, request, model, id=None):
        return self._update(request, model, id, partial=True)

    def _update(self, request, model, id, partial):
        if id is None:
            return _error("Update with PUT or PATCH on the object URL (with id)", 405)
        try:
            data, files = _parse_body(request)
        except ValueError as e:
            return _error(f"Invalid request body: {e}", 400)
        return _action_response(lambda: model_actions.update(request.user, model, id, data, files, partial=partial))

    def delete(self, request, model, id=None):
        if id is None:
            return _error("Delete with DELETE on the object URL (with id)", 405)
        return _action_response(lambda: model_actions.delete(request.user, model, id))
