"""
The SDC package 'sdc_extentions' houses a form called 'AbstractSearchForm' to simplify search implementations.
"""

from django import forms
from django.utils.translation import gettext_lazy as _


class AbstractSearchForm(forms.Form):
    """
    The AbstractSearchForm facilitates the development of a user interface for searching
    entries of a Django model type from the database. This form is closely  linked to
    the :func:`sdc_core.sdc_extentions.search.handle_search_form` handler. A form class
    that extends this class is automatically created when you use the sdc management
    command 'sdc_new_model'.

    The following class properties can be used to customize the search form:

    :cvar CHOICES: specifies the property according to which the search results are to be sorted.
    The value is a tuple of tuples of human-readable name, property name.
    :cvar DEFAULT_CHOICES: is the name of the property to which the search results are to be sorted if non is selected.
    :cvar SEARCH_FIELDS: is a list or a tuple of names of the properties that are included in the actual search
    :cvar PLACEHOLDER: is the placeholder text in the search input field.

    """

    CHOICES: tuple[tuple[str,str]] = ()
    SEARCH_FIELDS: list[str] = []
    DEFAULT_CHOICES: str = ""
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