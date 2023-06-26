import random
import string

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class CaptchaField(forms.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['label'] = _('Confirm that you are not a bot.')
        super(CaptchaField, self).__init__(*args, **kwargs)
        self.widget = CaptchaInput()

    def validate(self, value):
        super(CaptchaField, self).validate(value)
        value = str.upper(value)
        vla_list = list(value)
        if len(vla_list) < 2:
            raise ValidationError(self.error_messages['required'], code='required')
        for val in vla_list:
            if val != vla_list[0]:
                raise ValidationError(self.error_messages['required'], code='required')

class CaptchaInput(forms.widgets.Input):
    template_name = 'elements/widgets/captcha.html'
    input_type = 'text'
    def get_context(self, name, value, attrs):
        value = random.choice(string.ascii_uppercase)
        context = super(CaptchaInput, self).get_context(name, value, attrs)
        return context

class AbstractSearchForm(forms.Form):
    CHOICES = ()
    SEARCH_FIELDS = ()
    DEFAULT_CHOICES = ""
    NO_RESULTS_ON_EMPTY_SEARCH = False
    PLACEHOLDER = _('Search')
    search = forms.CharField(label=_('Search'), required=False, max_length=100, initial='')
    order_by = forms.ChoiceField(widget=forms.Select, required=False, choices=CHOICES)
    range_start = forms.IntegerField(widget=forms.HiddenInput(), required=False, initial=0)
    _method = forms.CharField(widget=forms.HiddenInput(), required=True, initial='search')


    def __init__(self, data=None, *args, **kwargs):
        auto_id= self.__class__.__name__ + "_%s"
        if len(data) == 0:
            data = None
        super(AbstractSearchForm, self).__init__(data, auto_id=auto_id, *args, **kwargs)
        self.fields['search'].widget.attrs['placeholder'] = self.PLACEHOLDER
        if len(self.CHOICES) == 0:
            del self.fields["order_by"]
        else:
            self.fields['order_by'].choices = self.CHOICES
            self.fields['order_by'].initial = self.DEFAULT_CHOICES

