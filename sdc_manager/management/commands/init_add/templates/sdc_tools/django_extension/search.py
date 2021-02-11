from django.db.models import Q
from django.views import View


def generate_q_key_value_request(key, val):
    map_val = {key + '__icontains': val}
    return Q(**map_val)


def handle_search_form(query_set, search_form, filter_dict=None, range=0):
    if not search_form.is_valid():
        data = {}
    else:
        data = search_form.cleaned_data

    key_word = data.get('search', None)
    does_order = len(search_form.CHOICES) > 0
    if(does_order):
        order_by = data.get('order_by', search_form.DEFAULT_CHOICES)

    if filter_dict is not None:
        query_set = query_set.filter(**filter_dict)
    else:
        pass#query_set = query_set.all()

    if key_word is not None:
        q_list = None
        for key in search_form.SEARCH_FIELDS:
            if q_list is None:
                q_list = generate_q_key_value_request(key, key_word)
            else:
                q_list = q_list | generate_q_key_value_request(key, key_word)
        query_set = query_set.filter(q_list)

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
