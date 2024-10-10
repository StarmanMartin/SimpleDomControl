from django.db.models import Q, QuerySet
from sdc_core.sdc_extentions.forms import AbstractSearchForm

def _generate_q_key_value_request(key, val):
    map_val = {key + '__icontains': val}
    return Q(**map_val)


def handle_search_form(query_set: QuerySet, search_form: AbstractSearchForm, filter_dict: dict=None, range: int=0):
    """
    This handler function takes a :class:`sdc_core.sdc_extentions.forms.AbstractSearchForm`

    :param query_set:
    :param search_form:
    :param filter_dict:
    :param range:
    :return:
    """
    if not search_form.is_valid():
        data = {}
    else:
        data = search_form.cleaned_data

    key_word = data.get('search', None)
    does_order = len(search_form.CHOICES) > 0
    order_by = None
    if(does_order):
        order_by = data.get('order_by', search_form.DEFAULT_CHOICES)

    if filter_dict is not None:
        query_set = query_set.filter(**filter_dict)
    else:
        pass#query_set = query_set.all()
    query_set_count = 0
    if key_word is not None and key_word != '':
        q_list = None
        for key in search_form.SEARCH_FIELDS:
            if q_list is None:
                q_list = _generate_q_key_value_request(key, key_word)
            else:
                q_list = q_list | _generate_q_key_value_request(key, key_word)
        query_set = query_set.filter(q_list).distinct()
        query_set_count = query_set.count()
    elif(search_form.NO_RESULTS_ON_EMPTY_SEARCH):
        query_set = []
    else:
        query_set_count = query_set.count()


    if(does_order):
        query_set = query_set.order_by(order_by)

    context = {
        'total_count': query_set_count,
        'search_form': search_form
    }

    if range > 0:
        from_idx = data.get('range_start', 0)
        if from_idx >= query_set_count:
            from_idx = max(query_set_count - 2, 0)

        to_idx = min(from_idx + range, query_set_count)
        query_set = query_set[from_idx:to_idx]
        context['range'] = [from_idx + 1, to_idx]
        context['range_size'] = range

    context['instances'] = query_set
    return context
