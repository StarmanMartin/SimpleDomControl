from __future__ import annotations

import logging

from datetime import timedelta
from typing import Optional

from django.template.loader import render_to_string

from django.utils import timezone
from django.utils.crypto import salted_hmac
import jwt
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sdc_core.sdc_extentions.models import SdcModel

logger = logging.getLogger(__name__)

# Lifetime of the e-mail confirmation / password-reset tokens.
TOKEN_TTL = timedelta(days=3)


def reset_token_fingerprint(user: SdcModel) -> str:
    """
    Single-use binding for password-reset tokens. Derived from the current
    password hash, so once the password is changed the token no longer matches
    and cannot be replayed.
    """
    return salted_hmac('sdc.reset', f'{user.pk}:{user.password}').hexdigest()[:16]


def confirm_token_fingerprint(user: SdcModel) -> str:
    """
    Single-use binding for e-mail confirmation tokens. Changes once the e-mail is
    confirmed or the address changes, invalidating any previously issued token.
    """
    return salted_hmac(
        'sdc.confirm', f'{user.pk}:{user.email}:{user.email_confirmed}'
    ).hexdigest()[:16]


def get_url_from_sdcmodel(element: SdcModel):
    scope = element.scope
    if scope is None:
        return None
    host = scope.get('headers', [])

    # Extract host from headers
    for header_name, header_value in host:
        if header_name == b'origin':
            return header_value.decode('utf-8')
    return None

def _resolve_home_url(user: SdcModel, home_url: Optional[str]) -> Optional[str]:
    """
    Base URL for links in e-mails: the given ``home_url``, else the origin of the
    current WebSocket request, else ``settings.HOME_URL``. Returns ``None`` (and
    logs an error) if none is available, so the caller can skip the e-mail instead
    of failing after the user has been saved.
    """
    home_url = home_url or get_url_from_sdcmodel(user) or getattr(settings, 'HOME_URL', None)
    if not home_url:
        logger.error("Cannot send e-mail to user %s: set settings.HOME_URL to the base URL of the site "
                     "(e.g. https://example.com).", user.pk)
        return None
    return home_url.rstrip('/')


def send_confirm_email(user: SdcModel, home_url: Optional[str] = None):
    email_template_name = 'email/confirm.html'
    now = timezone.now()
    encoded_jwt = jwt.encode({
        "user": user.id,
        "type": 'confirm',
        "fp": confirm_token_fingerprint(user),
        "iat": int(now.timestamp()),               # issued at
        "exp": int((now + TOKEN_TTL).timestamp()),  # native expiry
    }, settings.JWT['secret'], algorithm=settings.JWT['algorithm'])

    home_url = _resolve_home_url(user, home_url)
    if home_url is None:
        return

    context = {'jwt': encoded_jwt, 'user': user, 'url': f'{home_url}/~sdc-confirm-email~&1.token={encoded_jwt}'}

    html_content = render_to_string(email_template_name, context=context)

    msg = EmailMessage(_('Confirmation'), html_content, from_email=settings.DEFAULT_FROM_EMAIL, to=[user.email])
    msg.content_subtype = "html"
    msg.send(fail_silently=True)


def send_email_reset_email(user: SdcModel, home_url: Optional[str] = None):
    email_template_name = 'email/reset_password.html'
    now = timezone.now()
    encoded_jwt = jwt.encode({
        "user": user.id,
        "type": 'reset',
        "fp": reset_token_fingerprint(user),
        "iat": int(now.timestamp()),               # issued at
        "exp": int((now + TOKEN_TTL).timestamp()),  # native expiry
    }, settings.JWT['secret'], algorithm=settings.JWT['algorithm'])

    home_url = _resolve_home_url(user, home_url)
    if home_url is None:
        return

    context = {'jwt': encoded_jwt, 'user': user, 'url': f'{home_url}/~sdc-reset-password~&1.token={encoded_jwt}'}

    html_content = render_to_string(email_template_name, context=context)

    msg = EmailMessage(_('Reset Password'), html_content, from_email=settings.DEFAULT_FROM_EMAIL, to=[user.email])
    msg.content_subtype = "html"  # Main content is now text/html
    msg.send(fail_silently=True)
