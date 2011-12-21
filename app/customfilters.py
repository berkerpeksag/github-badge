import re

from math import log

# Constants
QUANTAS = ('k', 'M', 'G', 'T', 'P')


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


def smarttruncate(value, length=80, suffix='...',
                  pattern=r'^(.{%d,}?[a-zA-Z0-9])[^a-zA-Z0-9].*'):
    pattern = pattern % (length-1)
    return re.sub(pattern, r'\1' + suffix, value)
