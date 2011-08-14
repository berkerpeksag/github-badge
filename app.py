# coding: utf-8

import logging
import os
import operator
import posixpath
import sys

from GitHub import User as GitHubUser
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from slimmer import slimmer

logging.getLogger().setLevel(logging.DEBUG)

sys.setrecursionlimit(10000) # SDK fix


class User(GitHubUser):
    #Class name should be "user" to preserve compatibility
    #with the path variable defined on the main model
    _default_dict = dict(login='?',
                         html_url='#',
                         avatar_url='https://a248.e.akamai.net/assets.github.com'
                                    '/images/gravatars/gravatar-140.png',
                         name='?',
                         blog='#'
                        )

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
                      (repo.language for repo in self.repos), {}
                     )
  
    def get_project_watchers(self):
        return reduce(operator.add, (repo.watchers for repo in self.repos), 0)


class Handler(webapp.RequestHandler):
    def render(self, file, values=None):
        if not values: values = {}
        path = posixpath.join(posixpath.dirname(__file__),
                              'templates/%s.html' % file)
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
          github_user = User.get(username)
    
          sorted_languages = github_user.sort_languages()
          top_languages = sorted_languages[:5]
          remaining_languages = ', '.join(sorted_languages[5:])
          fork_count = sum((1 for repo in github_user.repos if repo.fork))
    
          output = \
            self.render('badge',
                         {'user': github_user,
                          'own_repos': github_user.public_repos - fork_count,
                          'fork_repos': fork_count,
                          'top_languages': ', '.join(top_languages),
                          'other_languages': remaining_languages,
                          'project_followers': github_user.get_project_watchers()
                         })
    
          if github_user.login != '?' and not memcache.add(username, output):
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
    debug=os.environ.get('SERVER_SOFTWARE', None).startswith('Devel')
)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()

