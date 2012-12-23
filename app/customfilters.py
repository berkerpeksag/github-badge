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


def smarttruncate(value, length=80, suffix='...', pattern=r'\w+'):
    value_length = len(value)
    if value_length > length:
        last_span = (0, value_length)
        for m in re.finditer(pattern, value):
            span = m.span()
            if span[1] > length:
                break
            else:
                last_span = span
        cutoff = last_span[1]
        if  cutoff > length:
            cutoff = length - len(suffix)
        return value[:cutoff] + suffix
    return value
