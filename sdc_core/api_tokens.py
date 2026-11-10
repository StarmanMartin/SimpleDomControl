"""
API tokens (``sdc_core.models.ApiToken``) and their privileges, for the REST API (``sdc_api/``) and the MCP endpoint.

A token string looks like ``sdc_<random>``; only its SHA-256 hash is stored. Its privileges only narrow what its
user may do, they never add rights: every model action checks the token's privileges first and then the model's
own rules (``is_authorised`` / ``get_queryset``) for the user.

Privileges:

=========================  ==================================================================================
``model:<Name>:read``      read records of the SdcModel ``<Name>`` (action ``load``)
``model:<Name>:write``     create and change records (actions ``create``, ``save``)
``model:<Name>:delete``    delete records (action ``delete``)
``model:*:<privilege>``    the same for every SdcModel
``account:read``           read the own user record and the own token list
``account:write``          change the own profile (never password, e-mail or username)
``account:tokens``         create tokens (with at most the own privileges) and revoke own tokens
=========================  ==================================================================================

``write`` does not include ``read`` and ``delete`` does not include ``write``.

Settings (``SDC_API_TOKENS``, a dict; missing keys use ``DEFAULT_SETTINGS``):

- ``max_lifetime_days``: longest lifetime of a personal token (``None``: tokens may never expire)
- ``default_lifetime_days``: lifetime of a personal token created without an expiry (``None``: never expires)
- ``login_lifetime_seconds``: lifetime of the tokens of ``sdc_api/login/`` (username and password)
- ``accept_jwt``: still accept the JSON web tokens of SDC ≤ 0.162 (deprecated, answered with a ``Deprecation``
  header; will be removed)
"""
import datetime
import hashlib
import secrets
import warnings
from dataclasses import dataclass
from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone

from sdc_core.sdc_extentions.model_actions import FULL, MissingPrivilege
from sdc_core.sdc_extentions.models import all_models

TOKEN_PREFIX = 'sdc_'
# Characters of the token shown in lists (the prefix "sdc_" and 8 random characters)
SHOWN_PREFIX_LENGTH = 12
MODEL_PRIVILEGES = ('read', 'write', 'delete')
ACCOUNT_READ = 'account:read'
ACCOUNT_WRITE = 'account:write'
ACCOUNT_TOKENS = 'account:tokens'
ACCOUNT_PRIVILEGES = (ACCOUNT_READ, ACCOUNT_WRITE, ACCOUNT_TOKENS)
FULL_ACCESS = tuple(f'model:*:{p}' for p in MODEL_PRIVILEGES) + ACCOUNT_PRIVILEGES
PRESETS = {
    'read': ('model:*:read', ACCOUNT_READ),
    'read_write': ('model:*:read', 'model:*:write', ACCOUNT_READ),
    'full': FULL_ACCESS,
}
# Fields of the own user record that a token can never change (account:write)
ACCOUNT_PROTECTED_FIELDS = frozenset({'password', 'username', 'email', 'email_confirmed', 'is_active', 'is_staff',
                                      'is_superuser', 'groups', 'user_permissions', 'last_login', 'date_joined'})
DEFAULT_SETTINGS = {
    'max_lifetime_days': 365,
    'default_lifetime_days': 90,
    'login_lifetime_seconds': 3600,
    'accept_jwt': True,
}
# last_used_at is written at most once per interval and token
LAST_USED_INTERVAL = datetime.timedelta(minutes=1)


def token_settings():
    return DEFAULT_SETTINGS | (getattr(settings, 'SDC_API_TOKENS', None) or {})


class TokenError(ValueError):
    """A token cannot be created as requested; the message is meant for the user."""


# ------------------------------------------------------------------ privileges

def normalize_privileges(privileges):
    """
    The sorted, de-duplicated privileges with the model names spelled as the model classes; ``TokenError`` for
    unknown privileges or models.
    """
    if not isinstance(privileges, (list, tuple, set, frozenset)) or \
            not all(isinstance(p, str) for p in privileges):
        raise TokenError('privileges must be a list of strings')
    models = all_models()
    result = set()
    for privilege in privileges:
        privilege = privilege.strip()
        if privilege in ACCOUNT_PRIVILEGES:
            result.add(privilege)
            continue
        parts = privilege.split(':')
        if len(parts) != 3 or parts[0] != 'model' or parts[2] not in MODEL_PRIVILEGES:
            raise TokenError(f'Unknown privilege: {privilege}')
        if parts[1] != '*':
            model = models.get(parts[1])
            if model is None:
                raise TokenError(f'Unknown model in privilege: {privilege}')
            parts[1] = model.__name__
        result.add(':'.join(parts))
    return sorted(result)


class Grant:
    """What a token may do (its privileges); used by ``model_actions`` and the account and token endpoints."""
    is_full = False

    def __init__(self, privileges):
        self.privileges = frozenset(privileges)

    @staticmethod
    def _model_name(model_name):
        model = all_models().get(model_name)
        return model.__name__ if model is not None else model_name

    def allows(self, model_name, privilege):
        return f'model:*:{privilege}' in self.privileges or \
            f'model:{self._model_name(model_name)}:{privilege}' in self.privileges

    def allows_account(self, privilege):
        return privilege in self.privileges

    def models(self, privilege):
        """Names of the SdcModels with ``privilege``."""
        return {name for name in all_models().keys() if self.allows(name, privilege)}

    def covers(self, privileges):
        """True if every one of ``privileges`` (normalized) is also granted here."""
        for privilege in privileges:
            if privilege in ACCOUNT_PRIVILEGES:
                if privilege not in self.privileges:
                    return False
                continue
            _model, name, action = privilege.split(':')
            if f'model:*:{action}' not in self.privileges and privilege not in self.privileges:
                return False
        return True


def require_account(grant, privilege):
    """``MissingPrivilege`` unless ``grant`` has the account privilege."""
    if not grant.allows_account(privilege):
        raise MissingPrivilege(privilege)


# ------------------------------------------------------------------ tokens

def hash_token(secret):
    return hashlib.sha256(secret.encode()).hexdigest()


_DEFAULT = object()


def create_token(user, name, privileges, expires_at=_DEFAULT, kind=None, created_by_token=None):
    """
    Creates a token for ``user`` and returns ``(ApiToken, secret)``; the secret is not stored and cannot be shown
    again. ``expires_at``: a datetime, ``None`` for no expiry (only if ``max_lifetime_days`` is ``None``), or left
    out for the default lifetime. ``created_by_token``: the token that creates this one through the API; the new
    token gets at most its privileges and expires no later. Raises ``TokenError``.
    """
    from sdc_core.models import ApiToken
    kind = kind or ApiToken.KIND_PERSONAL
    name = (name or '').strip()
    if not name:
        raise TokenError('The token needs a name')
    if len(name) > ApiToken._meta.get_field('name').max_length:
        raise TokenError('The name of the token is too long')
    privileges = normalize_privileges(privileges)
    if not privileges:
        raise TokenError('The token needs at least one privilege')

    now = timezone.now()
    config = token_settings()
    if kind == ApiToken.KIND_LOGIN:
        expires_at = now + datetime.timedelta(seconds=config['login_lifetime_seconds'])
    elif expires_at is _DEFAULT:
        days = config['default_lifetime_days']
        expires_at = now + datetime.timedelta(days=days) if days else None
        # The default lifetime of a token created by a token ends with its creator
        parent_expiry = created_by_token.expires_at if created_by_token is not None else None
        if parent_expiry is not None and (expires_at is None or expires_at > parent_expiry):
            expires_at = parent_expiry
    if expires_at is not None and expires_at <= now:
        raise TokenError('The expiry date must be in the future')
    max_days = config['max_lifetime_days']
    if kind != ApiToken.KIND_LOGIN and max_days and \
            (expires_at is None or expires_at > now + datetime.timedelta(days=max_days)):
        raise TokenError(f'A token may be valid for at most {max_days} days')

    if created_by_token is not None:
        if not Grant(created_by_token.privileges).covers(privileges):
            raise TokenError('A token cannot create a token with more privileges than its own')
        parent_expiry = created_by_token.expires_at
        if parent_expiry is not None and (expires_at is None or expires_at > parent_expiry):
            raise TokenError('A token cannot create a token that expires after itself')

    secret = TOKEN_PREFIX + secrets.token_urlsafe(32)
    token = ApiToken.objects.create(user=user, name=name, kind=kind, prefix=secret[:SHOWN_PREFIX_LENGTH],
                                    secret_hash=hash_token(secret), privileges=privileges, expires_at=expires_at,
                                    created_by_token=created_by_token)
    return token, secret


def token_to_dict(token):
    """The public data of a token (never its secret or hash)."""
    return {
        'id': str(token.id),
        'name': token.name,
        'kind': token.kind,
        'prefix': token.prefix,
        'privileges': list(token.privileges),
        'created_at': token.created_at,
        'expires_at': token.expires_at,
        'last_used_at': token.last_used_at,
        'revoked_at': token.revoked_at,
        'created_by_token': str(token.created_by_token_id) if token.created_by_token_id else None,
        'is_valid': token.is_valid,
    }


# ------------------------------------------------------------------ authentication

class AuthenticationFailed(Exception):
    def __init__(self, message, header_present=True):
        super().__init__(message)
        self.message = message
        self.header_present = header_present


@dataclass
class Authenticated:
    user: object
    grant: object
    token: object = None
    deprecated_jwt: bool = False


def bearer_token(request):
    """The token of the ``Authorization: Bearer`` header; ``AuthenticationFailed`` if it is missing or malformed."""
    header = request.headers.get('Authorization')
    if not header:
        raise AuthenticationFailed('Missing Authorization header', header_present=False)
    try:
        scheme, token = header.split(' ')
        if scheme.lower() != 'bearer' or not token:
            raise ValueError()
    except ValueError:
        raise AuthenticationFailed('Invalid Authorization header')
    return token


def authenticate(request):
    """
    The user and grant of the request's bearer token (``Authenticated``); ``AuthenticationFailed`` if the token is
    missing, unknown, revoked or expired or its user is inactive. With ``accept_jwt`` a JSON web token of
    SDC ≤ 0.162 is still accepted (full rights of the user, ``deprecated_jwt``).
    """
    from sdc_core.models import ApiToken
    secret = bearer_token(request)
    if secret.startswith(TOKEN_PREFIX):
        token = ApiToken.objects.select_related('user').filter(secret_hash=hash_token(secret)).first()
        if token is None or not token.user.is_active:
            raise AuthenticationFailed('Invalid token')
        if token.is_revoked:
            raise AuthenticationFailed('Revoked token')
        if token.is_expired:
            raise AuthenticationFailed('Expired token')
        _touch(token, request)
        return Authenticated(token.user, Grant(token.privileges), token)
    if token_settings()['accept_jwt']:
        return _authenticate_jwt(secret)
    raise AuthenticationFailed('Invalid token')


def _touch(token, request):
    from sdc_core.models import ApiToken
    now = timezone.now()
    if token.last_used_at is None or now - token.last_used_at >= LAST_USED_INTERVAL:
        ip = request.META.get('REMOTE_ADDR') or None
        ApiToken.objects.filter(pk=token.pk).update(last_used_at=now, last_used_ip=ip)
        token.last_used_at, token.last_used_ip = now, ip


def _authenticate_jwt(secret):
    import jwt
    from django.contrib.auth import get_user_model
    from sdc_core.jwt_utils import verify_auth_jwt
    try:
        _payload, user = verify_auth_jwt(secret)
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed('Expired token')
    except jwt.InvalidTokenError:
        raise AuthenticationFailed('Invalid token')
    except get_user_model().DoesNotExist:
        raise AuthenticationFailed('User not found')
    warnings.warn('SDC API: JSON web tokens are deprecated; use API tokens (sdc_api/tokens/ or sdc_api/login/)',
                  DeprecationWarning, stacklevel=2)
    return Authenticated(user, FULL, None, deprecated_jwt=True)


def unauthorized_response(error):
    """401 for an ``AuthenticationFailed``, with the ``WWW-Authenticate`` header of RFC 6750."""
    response = JsonResponse({'error': error.message}, status=401)
    response['WWW-Authenticate'] = 'Bearer error="invalid_token"' if error.header_present else 'Bearer'
    return response


def insufficient_privilege_response(error):
    """403 for a ``MissingPrivilege``: names the privilege the token lacks."""
    response = JsonResponse({'success': False, 'error': str(error), 'privilege': error.privilege}, status=403)
    response['WWW-Authenticate'] = f'Bearer error="insufficient_scope", scope="{error.privilege}"'
    return response


def mark_deprecated(response):
    response['Deprecation'] = 'true'
    return response


def api_token_required(view_func):
    """
    View decorator: authenticates the bearer token and sets ``request.user``, ``request.api_grant`` and
    ``request.api_token`` (None for a deprecated JWT); 401 if that fails.
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        try:
            auth = authenticate(request)
        except AuthenticationFailed as e:
            return unauthorized_response(e)
        request.user, request.api_grant, request.api_token = auth.user, auth.grant, auth.token
        response = view_func(request, *args, **kwargs)
        return mark_deprecated(response) if auth.deprecated_jwt else response

    return wrapped
