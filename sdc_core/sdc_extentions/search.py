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

    key_word = data.get('search') or ''
    order_by = None
    if len(search_form.CHOICES) > 0:
        # An empty selection falls back to the default ordering.
        order_by = data.get('order_by') or search_form.DEFAULT_CHOICES or None
    does_order = order_by is not None

    if filter_dict is not None:
        query_set = query_set.filter(**filter_dict)
    else:
        pass#query_set = query_set.all()
    query_set_count = 0
    q_list = Q()
    for single_word in key_word.split(' '):
        if single_word != '':
            q_group = Q()
            for key in search_form.SEARCH_FIELDS:
                q_group |= _generate_q_key_value_request(key, single_word)
            q_list &= q_group
    if q_list != Q():
        query_set = query_set.filter(q_list).distinct()
        query_set_count = query_set.count()
    elif search_form.NO_RESULTS_ON_EMPTY_SEARCH:
        query_set = query_set.none()
    else:
        query_set_count = query_set.count()


    if(does_order):
        query_set = query_set.order_by(order_by)

    context = {
        'total_count': query_set_count,
        'search_form': search_form
    }

    if range > 0:
        from_idx = data.get('range_start') or 0
        if from_idx >= query_set_count:
            from_idx = max(query_set_count - 2, 0)

        to_idx = min(from_idx + range, query_set_count)
        query_set = query_set[from_idx:to_idx]
        context['range'] = [from_idx + 1, to_idx]
        context['range_size'] = range

    context['instances'] = query_set
    return context
