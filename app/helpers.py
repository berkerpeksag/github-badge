# coding: utf-8

import base64
import datetime
import threading


def data_uri(data):
    return 'data:image/png;base64,' + base64.b64encode(data)


def daterange(start_date=None, end_date=None, date_range=None):
    if date_range:
        start_date = min(date_range)
        end_date = max(date_range)
    for n in xrange((end_date - start_date).days):
        yield start_date + datetime.timedelta(n)


def wait_for_threads(threads):
    for t in threads:
        t.start()

    for t in threads:
        if t.is_alive():
            t.join()


def parallel_foreach(func, iterable):
    threads = [threading.Thread(target=func, args=(item,))
               for item in iterable]
    wait_for_threads(threads)
