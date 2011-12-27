# coding: utf-8

import datetime
import threading


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


def parallel_foreach(func, iterable):
    threads = [threading.Thread(target=func, args=(item,))
               for item in iterable]
    wait_for_threads(threads)
