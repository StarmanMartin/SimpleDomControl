# widgets.py
from django.forms import Widget


class ReadOnlyPassword(Widget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.template_name = "widgets/read_only_password_hash.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['user'] = self.user
        return context