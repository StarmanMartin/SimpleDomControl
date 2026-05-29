import jwt
import datetime

from django.conf import settings

from functools import wraps

from django.http import JsonResponse
from django.contrib.auth import get_user_model


def generate_jwt(user):
    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(
            seconds=settings.JWT['exp_delta_seconds']
        ),
        "iat": datetime.datetime.now(datetime.UTC),
    }

    token = jwt.encode(
        payload,
        settings.JWT['secret'],
        algorithm=settings.JWT['algorithm'],
    )

    return token


def verify_jwt(token):
    try:
        payload = jwt.decode(
            token,
            settings.JWT['secret'],
            algorithms=[settings.JWT['algorithm']],
        )
        return payload

    except jwt.ExpiredSignatureError:
        return None

    except jwt.InvalidTokenError:
        return None

User = get_user_model()

def jwt_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return JsonResponse(
                {"error": "Missing Authorization header"},
                status=401,
            )

        try:
            prefix, token = auth_header.split(" ")

            if prefix.lower() != "bearer":
                raise ValueError()

        except ValueError:
            return JsonResponse(
                {"error": "Invalid Authorization header"},
                status=401,
            )

        payload = verify_jwt(token)

        if payload is None:
            return JsonResponse(
                {"error": "Invalid token"},
                status=401,
            )

        try:
            user = User.objects.get(id=payload["user_id"])
        except User.DoesNotExist:
            return JsonResponse(
                {"error": "User not found"},
                status=401,
            )

        request.user = user

        return view_func(request, *args, **kwargs)

    return wrapped