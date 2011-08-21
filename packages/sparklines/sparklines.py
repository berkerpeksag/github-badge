# coding: utf-8
"""sparkline.py

A module for generating sparklines.

"""

__author__ = "Joe Gregorio<joe@bitworking.org>"
__copyright__ = "Copyright 2005, Joe Gregorio"
__contributors__ = ('Alan Powell', 'Burak Yiğit Kaya<ben@byk.im>')
__license__ = "MIT"
__all__ = ('discrete', 'impulse', 'smooth')

import rgb

from .pngcanvas import PNGCanvas


def discrete(results, args={}, longlines=False):
    """The source data is a list of values between
      0 and 100 (or 'limits' if given). Values greater than 95 
      (or 'upper' if given) are displayed in red, otherwise 
      they are displayed in green"""
    width = int(args.get('width', '2'))
    height = int(args.get('height', '14'))
    upper = int(args.get('upper', '50'))
    below_color = args.get('below-color', 'gray')
    above_color = args.get('above-color', 'red')
    gap = 4
    if longlines:
        gap = 0
    im = PNGCanvas(len(results)*width-1, height)
    im.color = rgb.colors['white']
    im.filledRectangle(0, 0, im.width-1, im.height-1)

    (dmin, dmax) = [int(x) for x in args.get('limits', '0,100').split(',')]
    if dmax < dmin:
        dmax = dmin
    zero = im.height - 1
    if dmin < 0 and dmax > 0:
        zero = im.height - (0 - dmin) / (float(dmax - dmin + 1) / (height - gap))
    for (r, i) in zip(results, range(0, len(results)*width, width)):
        color = (r >= upper) and above_color or below_color
        if r < 0:
            y_coord = im.height - (r - dmin) / (float(dmax - dmin + 1) / (height - gap))
        else:
            y_coord = im.height - (r - dmin) / (float(dmax - dmin + 1) / (height - gap))
        im.color = rgb.colors[color]
        if longlines:
            im.rectangle(i, zero, i+width-2, y_coord)
        else:
            im.rectangle(i, y_coord - gap, i+width-2, y_coord)
    return im.dump()

def impulse(data, args={}):
    return discrete(data, args, True)

def smooth(results, args={}):
    step = int(args.get('step', '2'))
    height = int(args.get('height', '20'))
    (dmin, dmax) = [int(x) for x in args.get('limits', '0,100').split(',')]
    im = PNGCanvas((len(results) - 1) * step + 4, height)
    im.color = rgb.colors['white']
    im.filledRectangle(0, 0, im.width - 1, im.height - 1)
    coords = zip(range(1, len(results) * step + 1, step), 
                 [height - 3 - (y - dmin) / (float(dmax - dmin + 1) / (height - 4))
                   for y in results])

    im.color = rgb.colors['gray']
    lastx, lasty = coords[0]
    for x0, y0, in coords:
        im.line(lastx, lasty, x0, y0)
        lastx, lasty = x0, y0
    min_color = rgb.colors[args.get('min-color', 'green')]
    max_color = rgb.colors[args.get('max-color', 'red')]
    last_color = rgb.colors[args.get('last-color', 'blue')]
    has_min = args.get('min-m', 'false')
    has_max = args.get('max-m', 'false')
    has_last = args.get('last-m', 'false')
    if has_min == 'true':
        min_pt = coords[results.index(min(results))]
        im.color = min_color
        im.rectangle(min_pt[0] - 1, min_pt[1] - 1, min_pt[0] + 1, min_pt[1] + 1)
    if has_max == 'true':
        im.color = max_color
        max_pt = coords[results.index(max(results))]
        im.rectangle(max_pt[0] - 1, max_pt[1] - 1, max_pt[0] + 1, max_pt[1] + 1)
    if has_last == 'true':
        im.color = last_color
        end = coords[-1]
        im.rectangle(end[0] - 1, end[1] - 1, end[0] + 1, end[1] + 1)
    return im.dump()
