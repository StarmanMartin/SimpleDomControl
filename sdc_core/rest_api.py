"""
The REST API of the SdcModels (``sdc_api/``), authenticated with API tokens (``sdc_core.api_tokens``):

- ``login/``: username and password → a short-lived login token
- ``tokens/``, ``tokens/current/``, ``tokens/<id>/``: list, create and revoke the own tokens
- ``account/``: the own user record
- ``<model>/`` and ``<model>/<id>/``: read, create, change and delete records

Routes: ``sdc_core.api_urls`` (``path('sdc_api/', include('sdc_core.api_urls'))``).
"""
import json

import jwt
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseNotFound, QueryDict
from django.utils.dateparse import parse_datetime
from django.utils.datastructures import MultiValueDict
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from sdc_core import api_tokens
from sdc_core.api_tokens import api_token_required
from sdc_core.sdc_extentions import model_actions

User = get_user_model()


def _login_response(token, secret):
    return JsonResponse({
        "access_token": secret,
        "token_type": "bearer",
        "token_id": str(token.id),
        "expires_at": token.expires_at,
        "privileges": token.privileges,
    })


def _refresh_with_jwt(request):
    """GET of the deprecated refresh flow: a refresh JWT of SDC ≤ 0.162 is exchanged for a login token."""
    from sdc_core.jwt_utils import verify_refresh_jwt
    try:
        secret = api_tokens.bearer_token(request)
    except api_tokens.AuthenticationFailed as e:
        return api_tokens.unauthorized_response(e)
    if secret.startswith(api_tokens.TOKEN_PREFIX) or not api_tokens.token_settings()['accept_jwt']:
        return JsonResponse({"error": "Tokens are not refreshed any more: log in again (POST) or use a personal "
                                      "API token"}, status=410)
    try:
        _payload, user = verify_refresh_jwt(secret)
    except jwt.ExpiredSignatureError:
        return JsonResponse({"error": "Expired token"}, status=401)
    except (jwt.InvalidTokenError, User.DoesNotExist):
        return JsonResponse({"error": "Invalid token"}, status=401)
    token, new_secret = api_tokens.create_token(user, 'Login (refreshed JWT)', api_tokens.FULL_ACCESS,
                                                kind='login')
    return api_tokens.mark_deprecated(_login_response(token, new_secret))


@csrf_exempt
def get_api_token(request):
    """
    ``POST {"username", "password", "name"?, "privileges"?}`` → a login token (``kind`` ``login``, valid for
    ``SDC_API_TOKENS['login_lifetime_seconds']``; all privileges of the user unless ``privileges`` narrows them).
    """
    if request.method == "GET":
        return _refresh_with_jwt(request)
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError()
    except ValueError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    try:
        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            return JsonResponse({"error": "Missing credentials"}, status=400)
        user = authenticate(request, username=username, password=password)
        if user is None:
            return JsonResponse({"error": "Invalid credentials"}, status=401)
        try:
            token, secret = api_tokens.create_token(user, data.get("name") or "Login",
                                                    data.get("privileges") or api_tokens.FULL_ACCESS,
                                                    kind='login')
        except api_tokens.TokenError as e:
            return JsonResponse({"error": str(e)}, status=400)
        update_last_login(None, user)
        return _login_response(token, secret)
    except Exception as e:
        return JsonResponse({"error": str(e) if settings.DEBUG else "Internal server error"}, status=500)


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
    ``{"success": true, "data": ...}``, 400 with the form errors, 403 (with the missing privilege of the token),
    and 404 for records the user cannot reach. An unknown model raises ``Http404``.
    """
    try:
        result = action()
    except model_actions.MissingPrivilege as e:
        return api_tokens.insufficient_privilege_response(e)
    except PermissionDenied as e:
        return HttpResponseForbidden(str(e))
    except ObjectDoesNotExist:
        return HttpResponseNotFound()
    except model_actions.FormValidationError as e:
        return JsonResponse({"success": False, "errors": e.errors}, status=400)
    if result is None:
        return JsonResponse({"success": True})
    return JsonResponse({"success": True, "data": result})


@method_decorator(api_token_required, name="dispatch")
@method_decorator(csrf_exempt, name='dispatch')
class AdcApi(View):
    @staticmethod
    def get_element(model_name):
        return model_actions.get_model(model_name)

    def get(self, request, model, id=None):
        grant = request.api_grant
        if id is not None:
            return _action_response(lambda: model_actions.get(request.user, model, id, grant=grant))
        return _action_response(lambda: model_actions.load(request.user, model, request.GET, grant=grant))

    def post(self, request, model, id=None):
        if id is not None:
            return _error("Create with POST on the list URL (without id)", 405)
        try:
            data, files = _parse_body(request)
        except ValueError as e:
            return _error(f"Invalid request body: {e}", 400)
        return _action_response(lambda: model_actions.create(request.user, model, data, files,
                                                             grant=request.api_grant))

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
        return _action_response(lambda: model_actions.update(request.user, model, id, data, files, partial=partial,
                                                             grant=request.api_grant))

    def delete(self, request, model, id=None):
        if id is None:
            return _error("Delete with DELETE on the object URL (with id)", 405)
        return _action_response(lambda: model_actions.delete(request.user, model, id, grant=request.api_grant))


# ------------------------------------------------------------------ tokens

def _own_tokens(request):
    from sdc_core.models import ApiToken
    return ApiToken.objects.filter(user=request.user)


def _parse_expiry(value):
    """``expires_at`` of a create request: missing → default lifetime, null → no expiry, else an ISO datetime."""
    if value is None:
        return None
    parsed = parse_datetime(value) if isinstance(value, str) else None
    if parsed is None:
        raise api_tokens.TokenError('expires_at must be an ISO 8601 date and time')
    if parsed.tzinfo is None:
        from django.utils import timezone
        parsed = timezone.make_aware(parsed)
    return parsed


@method_decorator(api_token_required, name="dispatch")
@method_decorator(csrf_exempt, name='dispatch')
class ApiTokensView(View):
    """``GET``: the user's tokens (``account:read``); ``POST {"name", "privileges", "expires_at"?}``: a new token
    (``account:tokens``; at most the privileges of the calling token)."""

    def get(self, request):
        return _action_response(lambda: self._list(request))

    @staticmethod
    def _list(request):
        api_tokens.require_account(request.api_grant, api_tokens.ACCOUNT_READ)
        return [api_tokens.token_to_dict(t) for t in _own_tokens(request)]

    def post(self, request):
        try:
            api_tokens.require_account(request.api_grant, api_tokens.ACCOUNT_TOKENS)
        except model_actions.MissingPrivilege as e:
            return api_tokens.insufficient_privilege_response(e)
        try:
            data = json.loads(request.body or b'{}')
            if not isinstance(data, dict):
                raise ValueError()
        except ValueError:
            return _error("The body must be a JSON object", 400)
        privileges = data.get('privileges')
        if privileges is None and request.api_token is not None:
            privileges = request.api_token.privileges
        try:
            expiry = {'expires_at': _parse_expiry(data['expires_at'])} if 'expires_at' in data else {}
            token, secret = api_tokens.create_token(request.user, data.get('name'), privileges or [],
                                                    created_by_token=request.api_token, **expiry)
        except api_tokens.TokenError as e:
            return _error(str(e), 400)
        return JsonResponse({"success": True, "token": secret, "data": api_tokens.token_to_dict(token)},
                            status=201)


@method_decorator(api_token_required, name="dispatch")
@method_decorator(csrf_exempt, name='dispatch')
class ApiTokenView(View):
    """``GET``: one own token (``account:read``); ``DELETE``: revoke it and the tokens it created
    (``account:tokens``)."""

    def get(self, request, token_id):
        def action():
            api_tokens.require_account(request.api_grant, api_tokens.ACCOUNT_READ)
            return api_tokens.token_to_dict(_own_tokens(request).get(pk=token_id))
        return _action_response(action)

    def delete(self, request, token_id):
        def action():
            api_tokens.require_account(request.api_grant, api_tokens.ACCOUNT_TOKENS)
            token = _own_tokens(request).get(pk=token_id)
            token.revoke(by=request.user)
            return api_tokens.token_to_dict(token)
        return _action_response(action)


@csrf_exempt
@api_token_required
def current_token(request):
    """``GET``: the calling token (no privilege needed)."""
    if request.method != 'GET':
        return _error("GET required", 405)
    if request.api_token is None:
        return _error("The request was not made with an API token", 404)
    return JsonResponse({"success": True, "data": api_tokens.token_to_dict(request.api_token)})


# ------------------------------------------------------------------ account

@method_decorator(api_token_required, name="dispatch")
@method_decorator(csrf_exempt, name='dispatch')
class AccountView(View):
    """``GET``: the own user record (``account:read``); ``PATCH``: change the own profile (``account:write``;
    never ``ACCOUNT_PROTECTED_FIELDS`` such as password, e-mail or username). The user model's own rules apply
    as well."""

    def get(self, request):
        def action():
            api_tokens.require_account(request.api_grant, api_tokens.ACCOUNT_READ)
            return model_actions.get(request.user, User.__name__, request.user.pk)
        return _action_response(action)

    def patch(self, request):
        try:
            data, files = _parse_body(request)
        except ValueError as e:
            return _error(f"Invalid request body: {e}", 400)

        def action():
            api_tokens.require_account(request.api_grant, api_tokens.ACCOUNT_WRITE)
            protected = sorted(set(data.keys()) & api_tokens.ACCOUNT_PROTECTED_FIELDS)
            if protected or files:
                raise PermissionDenied(f"These fields cannot be changed with an API token: "
                                       f"{', '.join(protected or files.keys())}")
            return model_actions.update(request.user, User.__name__, request.user.pk, data, partial=True)
        return _action_response(action)
