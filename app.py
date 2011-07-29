# coding: utf-8

import os
import posixpath
import re
import sys
import urllib2

from django.utils import simplejson as json
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import models

sys.setrecursionlimit(10000) # SDK fix


class GitHub(object):
  api_base = 'https://api.github.com/users/%(_username)s%%s'
  _properties = dict(user=('',), repos=('/repos',))
  _cache = {}
  
  def __init__(self, user):
    self._username = user
    self.api_base = self.api_base % self.__dict__
  
  def __getattr__(self, name):
    if name not in self._properties:
      raise AttributeError
    
    if name not in self._cache:
      api_values = self._properties[name]
      self._cache[name] = json.loads(urllib2.urlopen(self.api_base % api_values).read())

      return self._cache[name]

  def __lang_stat_reducer(self, stats, lang):
    if lang:
      stats[lang] = stats.setdefault(lang, 0) + 1

    return stats

  @property
  def language_stats(self):
    return reduce(self.__lang_stat_reducer,
                   (repo['language'] for repo in self.repos), {}
                 )

  def get_favorite_languages(self, limit=0):
    lang_stats = self.language_stats
    fav_langs = sorted(lang_stats, key=lambda l: lang_stats[l], reverse=True)
    return ' '.join(fav_langs[:limit] if limit > 0 else fav_langs)


class Handler(webapp.RequestHandler):
  def render(self, file, values=None):
    if not values: values = {}
    path = posixpath.join(posixpath.dirname(__file__), 'templates/%s.html' % file)
    self.response.out.write(template.render(path, values))

  def write(self, string):
    self.response.out.write(string)


class MainHandler(Handler):
  def get(self):
    self.render('index')


class WidgetHandler(Handler):
  def get(self, username):
    GHInterface = GitHub(username)
    self.render('widget', {'user': GHInterface.user, 'languages': GHInterface.get_favorite_languages(5)})

  def post(self):
    self.write('Save')


application = webapp.WSGIApplication([
    ('/', MainHandler),
    ('/widget/(\w+)', WidgetHandler),
  ],
  debug = os.environ.get('SERVER_SOFTWARE', None).startswith('Devel')
)

def main():
  run_wsgi_app(application)

if __name__ == '__main__':
  main()
