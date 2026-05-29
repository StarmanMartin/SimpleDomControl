import json

from django.contrib.auth import authenticate
from django.http import Http404, JsonResponse, HttpResponseForbidden, HttpResponseNotFound, QueryDict
from django.utils.module_loading import import_string
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from sdc_core.consumers import ALL_MODELS
from sdc_core.jwt_utils import jwt_required, generate_jwt
from sdc_core.sdc_extentions.models import SDCSerializer


@csrf_exempt
def get_api_token(request):
    if request.method != "POST":
        return JsonResponse(
            {"error": "POST required"},
            status=405,
        )

    try:
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

        token = generate_jwt(user)

        return JsonResponse({
            "access_token": token,
            "token_type": "bearer",
        })

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON"},
            status=400,
        )

    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
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
            qs = request.GET or {}
            is_single_result = False
        if not model_class.is_authorised(request.user, 'load', qs):
            return HttpResponseForbidden()
        model_qs = model_class.get_queryset(request.user, 'load', qs)
        if is_single_result:
            try:
                model_obj = model_qs.get(**qs)
            except model_class.ObjectDoesNotExist:
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
        except model_class.ObjectDoesNotExist:
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
        except model_class.ObjectDoesNotExist:
            return HttpResponseNotFound()

        Form = import_string(model_class.SdcMeta.edit_form)
        data = QueryDict(request.body.decode(), mutable=True)
        for f in Form.Meta.fields:
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
        pass
