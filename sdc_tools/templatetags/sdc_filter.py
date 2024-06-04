import uuid

from django import template
import datetime
import random

register = template.Library()


@register.filter(name='addclass')
def addclass(field, css):
    return field.as_widget(attrs={"class": css})


@register.filter(name='addformclass')
def addformclass(field):
    if field.widget_type == 'checkbox':
        return field.as_widget(attrs={"class": 'form-control form-check-input timer-change'})
    if field.widget_type == 'select':
        return field.as_widget(attrs={"class": 'form-control form-select timer-change'})
    return field.as_widget(attrs={"class": 'form-control timer-change'})


@register.simple_tag(name='random_tag')
def random_tag(a):
    now = datetime.datetime.now()
    b = '%f' % now.timestamp()
    for i in range(a):
        b = "%s%d" % (b, random.randint(0, 9))
    return b


@register.simple_tag(name='get_list_id')
def get_list_id():
    return uuid.uuid4().__str__()


@register.filter
def to_class_name(value):
    return value.__class__.__name__


@register.filter(name='indexfilter')
def indexfilter(list_instance, i):
    return list_instance[int(i)]


@register.filter(name='in_list')
def in_list(i, list_instance):
    return i in list_instance
