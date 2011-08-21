# coding: utf-8

import logging
import posixpath
import sys

from .models import User
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from packages.slimmer import slimmer

logging.getLogger().setLevel(logging.DEBUG)

sys.setrecursionlimit(10000)  # SDK fix


class Handler(webapp.RequestHandler):
    def render(self, file, values=None):
        if not values:
            values = {}
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

            sorted_languages = User.sort_languages(github_user.language_stats)
            top_languages = sorted_languages[:5]
            remaining_languages = ', '.join(sorted_languages[5:])
            fork_count = sum((1 for repo in github_user.repos if repo.fork))

            values = {'user': github_user,
                      'own_repos': github_user.public_repos - fork_count,
                      'fork_repos': fork_count,
                      'top_languages': ', '.join(top_languages),
                      'other_languages': remaining_languages,
                      'project_followers': github_user.project_followers}

            output = self.render('badge_v2', values)

            if github_user.login != '?' and not memcache.add(username, output):
                logging.error('Memcache set failed for %s' % username)


class CacheHandler(Handler):
    def get(self):
        stats = memcache.get_stats()
        self.write("<b>Cache Hits:%s</b><br>" % stats['hits'])
        self.write("<b>Cache Misses:%s</b><br><br>" % stats['misses'])

