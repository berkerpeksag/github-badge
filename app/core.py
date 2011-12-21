# coding: utf-8

import base64
import datetime
import jinja2
import logging
import operator
import os
import packages.sparklines as sparklines
import sys
import webapp2

import customfilters
from .models import User
from google.appengine.api import memcache
from packages.slimmer import slimmer

sys.setrecursionlimit(10000)  # SDK fix


# Constants
MEMCACHE_EXPIRATION = 60 * 60 * 24  # 1 day in seconds


# Helper Functions
def daterange(start_date=None, end_date=None, range=None):
    if range:
        start_date = min(range)
        end_date = max(range)
    for n in xrange((end_date - start_date).days):
        yield start_date + datetime.timedelta(n)


# Request Handlers
class Handler(webapp2.RequestHandler):
    @webapp2.cached_property
    def template_provider(self):
        jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.join(os.getcwd(),
                                                        'templates'))
        )
        jinja_env.filters['shortnum'] = customfilters.shortnum
        return jinja_env

    def render(self, template_name, values=None):
        if not values:
            values = {}

        template = self.template_provider.get_template(template_name + '.html')
        output = slimmer(template.render(values), 'html')
        self.write(output)
        return output

    def write(self, string):
        self.response.write(string)


class MainHandler(Handler):
    def get(self):
        self.render('index')


class BadgeHandler(Handler):
    @staticmethod
    def reduce_commits_by_date(aggr, commit):
        date = commit.commit['committer']['date'][:10]
        aggr[date] = aggr.setdefault(date, 0) + 1
        return aggr

    @staticmethod
    def reduce_commits_by_repo(aggr, commit):
        repo = commit._owner.name
        aggr[repo] = aggr.setdefault(repo, 0) + 1
        return aggr

    def get_option(self, name, defval):
        return False if self.request.get(name, defval) == '0' else True

    def get(self, username):
        support = self.get_option('s', '0')
        analytics = self.get_option('a', '1')
        memcache_key = '%s?s%sa%s' % (username, support, analytics)
        cached_data = memcache.get(memcache_key)

        if cached_data:
            return self.write(cached_data)
        else:
            try:
                github_user = User.get(username)
            except Exception as err:
                self.response.set_status(500)
                logging.error(err)
                return

            sorted_languages = User.sort_languages(github_user.language_stats)
            top_languages = sorted_languages[:5]
            remaining_languages = ', '.join(sorted_languages[5:])
            fork_count = sum((1 for repo in github_user.repos if repo.fork))

            today = datetime.datetime.today()
            days = 10
            recent_than = today - datetime.timedelta(days=days)
            own_commits = github_user.get_latest_commits(recent_than)

            commits_by_repo = reduce(self.reduce_commits_by_repo,
                                        own_commits, dict())
            if commits_by_repo:
                last_project = max(commits_by_repo, key=operator.itemgetter)
            else:
                last_project = ''
            logging.info(commits_by_repo)
            commits_by_date = reduce(self.reduce_commits_by_date,
                                     own_commits, dict())
            range = daterange(recent_than, today)
            for d in range:
                key = unicode(d.date())
                if key not in commits_by_date:
                    commits_by_date[key] = 0

            commit_data = [commits_by_date[d] for d in sorted(commits_by_date)]
            logging.debug('Commit data %s', str(commit_data))
            commit_sparkline = 'data:image/png;base64,' + \
                                base64.b64encode(
                                    sparklines.impulse(commit_data,
                                                       below_color='SlateGray',
                                                       width=3,
                                                       dmin=0,
                                                       dmax=max(commit_data)
                                    ).replace('+', '%2B').replace('/', '%2F'),
                                )

            values = {'user': github_user,
                      'own_repos': github_user.public_repos - fork_count,
                      'fork_repos': fork_count,
                      'top_languages': ', '.join(top_languages),
                      'other_languages': remaining_languages,
                      'project_followers': github_user.project_followers - \
                                           github_user.public_repos,
                      'commit_sparkline': commit_sparkline,
                      'last_project': last_project,
                      'support': support,
                      'analytics': analytics,
                      'days': days,
                      'render_date': today
                      }

            output = self.render('badge', values)

            if not memcache.set(memcache_key, output, MEMCACHE_EXPIRATION):
                logging.error('Memcache set failed for %s' % username)


class CacheHandler(Handler):
    def get(self):
        stats = memcache.get_stats()
        self.write("<b>Cache Hits:%s</b><br>" % stats['hits'])
        self.write("<b>Cache Misses:%s</b><br><br>" % stats['misses'])
