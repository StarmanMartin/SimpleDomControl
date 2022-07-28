import datetime

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from sdc_tools.django_extension.import_manager import import_functions

if hasattr(settings, 'EMAIL_RES_HANDLER'):
    on_email_handler = dict(import_functions(settings.EMAIL_RES_HANDLER))
else:
    on_email_handler = {}


def run_email_task(link, request):
    # if self.is_done:
    #    return

    # C -> Confirm Email
    max_date = datetime.date.today() + datetime.timedelta(days=3)

    if link.is_done or link.is_confirmed_date > max_date:
        return on_email_handler[link.email_type]().timeout(request, link)

    link.is_done = True
    link.save()

    return on_email_handler[link.email_type]().handle(request, link)


class EmailHandler():
    def timeout(self, request, link):
        raise TimeoutError('Your link has expired.')

    def handle(self, request, link):
        pass


class ChangePasswordEmail(EmailHandler):

    def handle(self, request, link):
        request.session['reset_password'] = {
            'link': link.pk
        }
        return {'controller': 'user-password-reset'}


class ConfirmEmail(EmailHandler):
    def timeout(self, request, link):
        link.user.send_confirm_email(request)
        raise TimeoutError(_('Your link has expired. We have sent you a new email.'))

    def handle(self, request, link):
        link.user.is_email_confirmed = True
        link.user.save()
        return {'msg': _('Email confirmed'),
                'header': _('Thank you!!')}


on_email_handler['C'] = ConfirmEmail
on_email_handler['P'] = ChangePasswordEmail
