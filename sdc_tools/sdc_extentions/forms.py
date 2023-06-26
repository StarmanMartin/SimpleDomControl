from django import forms
from django.utils.translation import gettext_lazy as _

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