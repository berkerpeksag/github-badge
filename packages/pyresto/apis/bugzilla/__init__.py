#!/usr/bin/env python
# coding: utf-8

import imp
import os.path
import sys
import types


__version__ = '0.2'
__author__ = ('Berker Peksag <berker.peksag@gmail.com>',
              'Burak Yigit Kaya <ben@byk.im>')

__models_file__ = os.path.join(os.path.dirname(__file__), 'models.py')
__models_code__ = compile(open(__models_file__).read(),
                          __models_file__, 'exec')

__services__ = dict(
    mozilla='https://api-dev.bugzilla.mozilla.org/latest/',
    mozilla_test='https://api-dev.bugzilla.mozilla.org/test/latest/',
    mozilla11='https://api-dev.bugzilla.mozilla.org/1.1/',
    mozilla11_test='https://api-dev.bugzilla.mozilla.org/test/1.1/'
)

__all__ = ('Service',) + tuple(__services__.iterkeys())


class Service(types.ModuleType):
    def __init__(self, name, url):
        self.name = name
        self.module_name = '{0}.{1}'.format(__name__, self.name)
        self.url = url
        self.__namespace = None

    @property
    def namespace(self):
        if self.__namespace is None:
            # All these "namespacing tricks" are from (from slides 43+)
            # https://speakerdeck.com/u/antocuni/p/python-white-magic?slide=87
            self.__namespace = imp.new_module(self.module_name)
            self.__namespace.__service_url__ = self.url
            exec __models_code__ in self.__namespace.__dict__
            sys.modules[self.module_name] = self.__namespace

        return self.__namespace

    def __getattr__(self, item):
        return getattr(self.namespace, item)


# Create services
_globals = globals()
for name, url in __services__.iteritems():
    _globals[name] = Service(name, url)
