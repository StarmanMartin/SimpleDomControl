from django import template

register = template.Library()


@register.filter(name='indexfilter')
def indexfilter(list_instance, i):
    return list_instance[int(i)]


@register.filter(name='in_list')
def in_list(i, list_instance):
    return i in list_instance
