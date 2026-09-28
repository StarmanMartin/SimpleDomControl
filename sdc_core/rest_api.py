import json

import jwt
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.forms.models import model_to_dict
from django.http import Http404, JsonResponse, HttpResponseForbidden, HttpResponseNotFound, QueryDict
from django.utils.datastructures import MultiValueDict
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model

from sdc_core.consumers import ALL_MODELS
from sdc_core.jwt_utils import jwt_required, generate_jwt, get_auth_token_from_request, \
    verify_refresh_jwt
from sdc_core.sdc_extentions.models import SDCSerializer, sanitize_filter_query, resolve_form

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


def _serialize_instance(instance):
    # Same format as GET on a single object; never echo the submitted form data
    # (it may contain passwords and non-JSON values such as model instances).
    return json.loads(SDCSerializer().serialize([instance]))[0]


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


def _patch_data(form_class, instance, data):
    """Form data for a partial update: the current values, overwritten by the submitted ones."""
    field_names = list(form_class(instance=instance).fields.keys())
    current = model_to_dict(instance, fields=field_names)
    if isinstance(data, QueryDict):
        merged = QueryDict(mutable=True)
        for key, value in current.items():
            values = value if isinstance(value, list) else [value]
            merged.setlist(key, ['' if v is None else v for v in values])
        for key in data.keys():
            merged.setlist(key, data.getlist(key))
        return merged
    return current | dict(data)


def _error(message, status):
    return JsonResponse({"success": False, "error": message}, status=status)


@method_decorator(jwt_required, name="dispatch")
@method_decorator(csrf_exempt, name='dispatch')
class AdcApi(View):
    @staticmethod
    def get_element(model_name):
        model = ALL_MODELS.get(model_name)
        if model is None:
            raise Http404(f"Model: {model_name} not found")
        return model

    def get(self, request, model, id=None):
        model_class = self.get_element(model)
        if id is not None:
            qs = {'pk': id}
            is_single_result = True
        else:
            try:
                qs = sanitize_filter_query(model_class, request.GET or {})
            except PermissionDenied as e:
                return HttpResponseForbidden(str(e))
            is_single_result = False
        if not model_class.is_authorised(request.user, 'load', qs):
            return HttpResponseForbidden()
        model_qs = model_class.get_queryset(request.user, 'load', qs)
        if is_single_result:
            try:
                model_obj = model_qs.get(**qs)
            except model_class.DoesNotExist:
                return HttpResponseNotFound()
            return JsonResponse({
                "success": True,
                "data": json.loads(SDCSerializer().serialize([model_obj]))[0]
            },
                status=200
            )
        data = json.loads(SDCSerializer().serialize(model_qs.filter(**qs)))
        return JsonResponse({
            "success": True,
            "data": data
        },
            status=200
        )

    def post(self, request, model, id=None):
        if id is not None:
            return _error("Create with POST on the list URL (without id)", 405)
        model_class = self.get_element(model)
        if not model_class.is_authorised(request.user, 'create', {}):
            return HttpResponseForbidden()
        try:
            data, files = _parse_body(request)
        except ValueError as e:
            return _error(f"Invalid request body: {e}", 400)
        Form = resolve_form(model_class.SdcMeta.create_form)
        form = Form(instance=None, data=data, files=files)
        if not form.is_valid():
            return JsonResponse({
                "success": False,
                "errors": form.errors,
            }, status=400)

        instance = form.save()
        return JsonResponse({
            "success": True,
            "data": _serialize_instance(instance),
        })

    def put(self, request, model, id=None):
        return self._update(request, model, id, partial=False)

    def patch(self, request, model, id=None):
        return self._update(request, model, id, partial=True)

    def _update(self, request, model, id, partial):
        if id is None:
            return _error("Update with PUT or PATCH on the object URL (with id)", 405)
        qs = {'pk': id}
        model_class = self.get_element(model)
        if not model_class.is_authorised(request.user, 'save', {}):
            return HttpResponseForbidden()
        model_qs = model_class.get_queryset(request.user, 'save', qs)
        try:
            model_obj = model_qs.get(**qs)
        except model_class.DoesNotExist:
            return HttpResponseNotFound()

        try:
            data, files = _parse_body(request)
        except ValueError as e:
            return _error(f"Invalid request body: {e}", 400)
        Form = resolve_form(model_class.SdcMeta.edit_form)
        if partial:
            data = _patch_data(Form, model_obj, data)
        form = Form(instance=model_obj, data=data, files=files)
        if not form.is_valid():
            return JsonResponse({
                "success": False,
                "errors": form.errors,
            }, status=400)

        instance = form.save()
        return JsonResponse({
            "success": True,
            "data": _serialize_instance(instance),
        })

    def delete(self, request, model, id=None):
        if id is None:
            return _error("Delete with DELETE on the object URL (with id)", 405)
        qs = {'pk': id}
        model_class = self.get_element(model)
        if not model_class.is_authorised(request.user, 'delete', qs):
            return HttpResponseForbidden()
        model_qs = model_class.get_queryset(request.user, 'delete', qs)
        try:
            model_obj = model_qs.get(**qs)
        except model_class.DoesNotExist:
            return HttpResponseNotFound()
        model_obj.delete()
        return JsonResponse({"success": True})
