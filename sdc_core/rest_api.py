import json

import jwt
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.http import Http404, JsonResponse, HttpResponseForbidden, HttpResponseNotFound, QueryDict
from django.utils.module_loading import import_string
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model

from sdc_core.consumers import ALL_MODELS
from sdc_core.jwt_utils import jwt_required, generate_jwt, get_auth_token_from_request, \
    verify_refresh_jwt
from sdc_core.sdc_extentions.models import SDCSerializer, sanitize_filter_query

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
            return HttpResponseNotFound("Cannot create with id")
        model_class = self.get_element(model)
        if not model_class.is_authorised(request.user, 'create', {}):
            return HttpResponseForbidden()
        Form = import_string(model_class.SdcMeta.create_form)
        form = Form(
            instance=None,
            data=request.POST,
            files=request.FILES
        )
        if not form.is_valid():
            return JsonResponse({
                "success": False,
                "errors": form.errors,
            }, status=400)

        form.save()
        return JsonResponse({
            "success": True,
            "data": form.cleaned_data,
        })

    def put(self, request, model, id):
        if id is None:
            return HttpResponseNotFound("Cannot update without id")
        qs = {'pk': id}
        model_class = self.get_element(model)
        if not model_class.is_authorised(request.user, 'save', {}):
            return HttpResponseForbidden()
        model_qs = model_class.get_queryset(request.user, 'save', qs)
        try:
            model_obj = model_qs.get(**qs)
        except model_class.DoesNotExist:
            return HttpResponseNotFound()

        Form = import_string(model_class.SdcMeta.edit_form)
        data = QueryDict(request.body.decode())
        form = Form(
            instance=model_obj,
            data=data,
            files=request.FILES
        )
        if not form.is_valid():
            return JsonResponse({
                "success": False,
                "errors": form.errors,
            }, status=400)

        form.save()
        return JsonResponse({
            "success": True,
            "data": form.cleaned_data,
        })

    def patch(self, request, model, id):

        if id is None:
            return HttpResponseNotFound("Cannot update without id")
        qs = {'pk': id}
        model_class = self.get_element(model)
        if not model_class.is_authorised(request.user, 'save', {}):
            return HttpResponseForbidden()
        model_qs = model_class.get_queryset(request.user, 'save', qs)
        try:
            model_obj = model_qs.get(**qs)
        except model_class.DoesNotExist:
            return HttpResponseNotFound()

        Form = import_string(model_class.SdcMeta.edit_form)

        data = QueryDict(request.body.decode(), mutable=True)

        form = Form(
            instance=model_obj,
            data=data,
            files=request.FILES
        )

        for f in form.fields.keys():
            if f not in data and hasattr(model_obj, f):
                data.update({f: getattr(model_obj, f)})

        form = Form(
            instance=model_obj,
            data=data,
            files=request.FILES
        )

        if not form.is_valid():
            return JsonResponse({
                "success": False,
                "errors": form.errors,
            }, status=400)

        form.save()
        return JsonResponse({
            "success": True,
            "data": form.cleaned_data,
        })

    def delete(self, request, model, id):
        # Not implemented. Return an explicit response so the endpoint does not
        # raise a 500 ("view didn't return an HttpResponse"). See ISSUES.md §2 —
        # full implementation needs is_authorised('delete') + get_queryset gating.
        return JsonResponse(
            {"success": False, "error": "Delete is not supported"},
            status=501,
        )
