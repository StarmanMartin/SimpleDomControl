from __future__ import annotations

from typing import Optional

from django.template.loader import render_to_string

from django.utils import timezone
import jwt
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sdc_core.sdc_extentions.models import SdcModel


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

def send_confirm_email(user: SdcModel, home_url: Optional[str] = None):
    email_template_name = 'email/confirm.html'
    encoded_jwt = jwt.encode({
        "user": user.id,
        "iat": int(timezone.now().timestamp())    # issued at
    }, settings.JWT['secret'], algorithm=settings.JWT['algorithm'])

    if home_url is None:
        home_url = get_url_from_sdcmodel(user)
    if home_url is None:
        home_url = settings.HOME_URL

    context = {'jwt': encoded_jwt, 'user': user, 'url': f'{home_url}/~sdc-confirm-email~&1.token={encoded_jwt}'}

    html_content = render_to_string(email_template_name, context=context)

    msg = EmailMessage(_('Confirmation'), html_content, from_email=settings.DEFAULT_FROM_EMAIL, to=[user.email])
    msg.content_subtype = "html"  # Main content is now text/html
    msg.send(fail_silently=False)

def send_email_reet_email(user: SdcModel, home_url: Optional[str] = None):
    email_template_name = 'email/reset_password.html'
    encoded_jwt = jwt.encode({
        "user": user.id,
        "type": 'reset',
        "iat": int(timezone.now().timestamp())    # issued at
    }, settings.JWT['secret'], algorithm=settings.JWT['algorithm'])

    if home_url is None:
        home_url = get_url_from_sdcmodel(user)
    if home_url is None:
        home_url = settings.HOME_URL

    context = {'jwt': encoded_jwt, 'user': user, 'url': f'{home_url}/~sdc-reset-password~&1.token={encoded_jwt}'}

    html_content = render_to_string(email_template_name, context=context)

    msg = EmailMessage(_('Reset Password'), html_content, from_email=settings.DEFAULT_FROM_EMAIL, to=[user.email])
    msg.content_subtype = "html"  # Main content is now text/html
    msg.send(fail_silently=False)
