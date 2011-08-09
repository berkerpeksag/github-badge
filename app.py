# coding: utf-8

import logging
import os
import operator
import posixpath
import re
import sys
import urllib2

from django.utils import simplejson as json
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from slimmer import slimmer

logging.getLogger().setLevel(logging.DEBUG)

sys.setrecursionlimit(10000) # SDK fix


class GitHub(object):
  api_base = 'https://api.github.com/users/%(_username)s%%s'
  _properties = {
                  'user': {
                    'params': ('',),
                    'default': dict(login='?',
                                    html_url='#',
                                    avatar_url='https://a248.e.akamai.net/assets.github.com/images/gravatars/gravatar-140.png',
                                    name='?',
                                    blog='#'
                                   ),
                  },
                  'repos': {
                    'params': ('/repos?per_page=100',),
                    'default': []
                  }
                }
  _cache = None
  __link_parser = re.compile(r'\<([^\>]+)\>;\srel="(\w+)"', re.I or re.U)

  def __init__(self, user):
    self._username = user
    self.api_base = self.api_base % self.__dict__
    self._cache = {}
  
  @classmethod
  def _fetch_data(cls, url):
    try:
      result = urllib2.urlopen(url)
    except (urllib2.URLError, urllib2.HTTPError):
      return None

    info = result.info()
    data = json.loads(result.read())
    if isinstance(data, list) and ("Link" in info):
      #logging.debug("Found links: %s" % info['Link'])
      links = dict(((cls.__link_parser.match(link.strip()).group(2, 1)
                       for link in info['Link'].split(','))))
      if "next" in links:
        #logging.debug("Found next link, fetching: %s" % links['next'])
        data += cls._fetch_data(links['next'])
    return data
  
  def __getattr__(self, name):
    #logging.debug('Property access for %s' % name)
    if name not in self._properties:
      raise AttributeError

    if name not in self._cache:
      prop_info = self._properties[name]
      api_values = prop_info['params']
      prop_value = self._fetch_data(self.api_base % api_values)
      if prop_value:
        self._cache[name] = prop_value
      else:
        return prop_info['default']
    
    return self._cache[name] 

  def sort_languages(self):
    lang_stats = self.get_language_stats()
    return sorted(lang_stats, key=lang_stats.get, reverse=True)
  
  @staticmethod
  def __lang_stat_reducer(stats, lang):
    if lang:
      stats[lang] = stats.setdefault(lang, 0) + 1
    return stats

  def get_language_stats(self):
    return reduce(self.__lang_stat_reducer,
                  (repo['language'] for repo in self.repos), {}
                 )
  
  def get_total_project_watchers(self):
    return reduce(operator.add, (repo['watchers'] for repo in self.repos), 0)


class Handler(webapp.RequestHandler):
  def render(self, file, values=None):
    if not values: values = {}
    path = posixpath.join(posixpath.dirname(__file__), 'templates/%s.html' % file)
    output = slimmer(template.render(path, values), 'html')
    self.response.out.write(output)
    return output

  def write(self, string):
    self.response.out.write(string)


class MainHandler(Handler):
  def get(self):
    self.render('index')


class BadgeHandler(Handler):
  def get(self, username):
    cached_data = memcache.get(username)

    if cached_data:
      return self.write(cached_data)
    else:
      github_data = GitHub(username)

      language_stats = github_data.get_language_stats()
      sorted_languages = github_data.sort_languages()
      top_language_count = max(language_stats.values())
      top_languages = sorted_languages[:5]
      remaining_languages = ', '.join(sorted_languages[5:])


      output = self.render('badge',
                           {'user': github_data.user,
                            'top_languages': ', '.join(top_languages),
                            'other_languages': remaining_languages,
                            'project_followers': github_data.get_total_project_watchers()
                           })
      
      if 'user' in github_data._cache and not memcache.add(username, output):
        logging.error('Memcache set failed for %s' % username)


class CacheHandler(Handler):
  def get(self):
    stats = memcache.get_stats()
    self.write("<b>Cache Hits:%s</b><br>" % stats['hits'])
    self.write("<b>Cache Misses:%s</b><br><br>" % stats['misses'])


application = webapp.WSGIApplication([
    ('/', MainHandler),
    ('/badge/([-\w]+)', BadgeHandler),
    ('/stats', CacheHandler),
  ],
  debug = os.environ.get('SERVER_SOFTWARE', None).startswith('Devel')
)

def main():
  run_wsgi_app(application)

if __name__ == '__main__':
  main()
