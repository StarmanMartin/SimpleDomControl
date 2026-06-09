import jwt
import datetime

from django.conf import settings

from functools import wraps

from django.http import JsonResponse
from django.contrib.auth import get_user_model

User = get_user_model()


def generate_jwt(user):
    payload = {
        "user_id": user.id,
        "username": user.username,
        "iat": user.last_login,
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(
            seconds=settings.JWT['exp_delta_seconds']
        ),
        "type": "auth"
    }

    token = jwt.encode(
        payload,
        settings.JWT['secret'],
        algorithm=settings.JWT['algorithm'],
    )

    payload = {
        "user_id": user.id,
        "username": user.username,
        "iat": user.last_login,
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(
            seconds=settings.JWT['exp_delta_seconds'] * 20
        ),
        "iat": datetime.datetime.now(datetime.UTC),
        "type": "refresh"
    }

    recover_token = jwt.encode(
        payload,
        settings.JWT['secret'],
        algorithm=settings.JWT['algorithm'],
    )

    return token, recover_token


def verify_jwt(token, type):

        payload = jwt.decode(
            token,
            settings.JWT['secret'],
            algorithms=[settings.JWT['algorithm']],
        )
        if payload is None or payload.get('type') != type:
            raise jwt.InvalidTokenError

        user = User.objects.get(id=payload["user_id"])

        if type == 'refresh' and abs(payload['iat'] - user.last_login.timestamp()) > 10:
            raise jwt.InvalidTokenError

        return payload, user


def verify_refresh_jwt(token):
    return verify_jwt(token, 'refresh')


def verify_auth_jwt(token):
    return verify_jwt(token, 'auth')

def get_auth_token_from_request(request):
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return None, JsonResponse(
            {"error": "Missing Authorization header"},
            status=401,
        )

    try:
        prefix, token = auth_header.split(" ")

        if prefix.lower() != "bearer":
            raise ValueError()

    except ValueError:
        return None, JsonResponse(
            {"error": "Invalid Authorization header"},
            status=401,
        )
    return token, None

def jwt_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        token, err = get_auth_token_from_request(request)
        if err is not None:
            return err
        try:
            payload, user = verify_auth_jwt(token)
        except (jwt.InvalidTokenError, jwt.ExpiredSignatureError):
            return JsonResponse(
                {"error": "Invalid token"},
                status=401,
            )
        except User.DoesNotExist:
            return JsonResponse(
                {"error": "User not found"},
                status=401,
            )

        request.user = user

        return view_func(request, *args, **kwargs)

    return wrapped
