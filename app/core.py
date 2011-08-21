# coding: utf-8

import base64
import logging
import posixpath
import packages.sparklines as sparklines
import sys
import urllib

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
    @staticmethod
    def reduce_commits_by_date(aggr, commit):
        date = commit['commit']['committer']['date'].split('T')[0]
        aggr[date] = aggr.setdefault(date, 0) + 1
        return aggr

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
            own_commits = github_user.own_commits[:50]
            grouped_commits = reduce(BadgeHandler.reduce_commits_by_date, own_commits, {})
            commit_data = [grouped_commits[d] for d in sorted(grouped_commits)]
            logging.debug('Commit data %s', str(commit_data))
            commit_sparkline = 'data:image/png;base64,' + \
                                urllib.quote(base64.b64encode(
                                    sparklines.impulse(commit_data,
                                    dmin=min(commit_data), dmax=max(commit_data)
                                    )
                                ))

            values = {'user': github_user,
                      'own_repos': github_user.public_repos - fork_count,
                      'fork_repos': fork_count,
                      'top_languages': ', '.join(top_languages),
                      'other_languages': remaining_languages,
                      'project_followers': github_user.project_followers,
                      'commit_sparkline': commit_sparkline,
                      }

            output = self.render('badge_v2', values)

            if github_user.login != '?' and not memcache.add(username, output):
                logging.error('Memcache set failed for %s' % username)


class CacheHandler(Handler):
    def get(self):
        stats = memcache.get_stats()
        self.write("<b>Cache Hits:%s</b><br>" % stats['hits'])
        self.write("<b>Cache Misses:%s</b><br><br>" % stats['misses'])

