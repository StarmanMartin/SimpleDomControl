from django.core import mail
from django.test import TestCase

from sdc_user.models import SdcUser


class EmailConfirmationTest(TestCase):
    def setUp(self):
        self.user = SdcUser.objects.create_user('alice', 'alice@example.com', 'pw-12345678')
        SdcUser.objects.filter(pk=self.user.pk).update(email_confirmed=True)
        self.user = SdcUser.objects.get(pk=self.user.pk)
        mail.outbox.clear()

    def test_changed_email_is_unconfirmed(self):
        self.user.email = 'new@example.com'
        self.user.save()
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_confirmed)
        self.assertEqual([m.to for m in mail.outbox], [['new@example.com']])

    def test_changed_email_with_update_fields(self):
        self.user.email = 'new@example.com'
        self.user.save(update_fields=['email'])
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_confirmed)

    def test_other_changes_keep_confirmation(self):
        self.user.first_name = 'Alice'
        self.user.save()
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_confirmed)
        self.assertEqual(mail.outbox, [])
