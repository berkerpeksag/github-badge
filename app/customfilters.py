from math import log
from google.appengine.ext import webapp

register = webapp.template.create_template_register()

# Constants
QUANTAS = ('k', 'M', 'G', 'T', 'P')

@register.filter
def shortnum(value, precision=3):
    value = float(value)
    if value >= 1000:
        order = int(log(value, 1000))
        mult = 10 ** (order * 3)
        num = value / mult
        quanta = QUANTAS[order - 1]
    else:
        num = value
        quanta = ''
    fmt = "%%.%dg%%s" % precision
    return fmt % (num, quanta)


@register.filter
def truncatechars(value, maxlen):
    if len(value) > maxlen:
        return value[:maxlen - 3] + '...'
    else:
        return value
