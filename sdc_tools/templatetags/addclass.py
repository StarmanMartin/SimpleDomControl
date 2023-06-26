import datetime

from django import template
import random

register = template.Library()

@register.filter(name='addclass')
def addclass(field, css):
    return field.as_widget(attrs={"class":css})

@register.filter(name='addformclass')
def addformclass(field):
    if field.widget_type == 'checkbox':
        return field.as_widget(attrs={"class":'form-control form-check-input timer-change'})
    if field.widget_type == 'select':
        return field.as_widget(attrs={"class":'form-control form-select timer-change'})
    return field.as_widget(attrs={"class":'form-control timer-change'})

@register.simple_tag(name='random_tag')
def random_tag(a):
    now = datetime.datetime.now()
    b = '%f' % now.timestamp()
    for i in range(a):
        b = "%s%d" % (b,random.randint(0, 9))
    return b