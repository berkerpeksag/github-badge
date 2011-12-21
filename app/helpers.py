# coding: utf-8

import datetime


def daterange(start_date=None, end_date=None, range=None):
    if range:
        start_date = min(range)
        end_date = max(range)
    for n in xrange((end_date - start_date).days):
        yield start_date + datetime.timedelta(n)


def wait_for_threads(threads):
    for t in threads:
        t.start()

    for t in threads:
        if t.is_alive():
            t.join()
