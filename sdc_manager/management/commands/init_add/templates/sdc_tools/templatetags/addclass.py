import datetime

from django import template
import random

register = template.Library()

@register.filter(name='addclass')
def addclass(field, css):
    return field.as_widget(attrs={"class":css})

@register.simple_tag(name='random_tag')
def random_tag(a):
    now = datetime.datetime.now()
    b = '%f' % now.timestamp()
    for i in range(a):
        b = "%s%d" % (b,random.randint(0, 9))
    return b