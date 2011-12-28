# coding: utf-8

from collections import deque
import datetime
from itertools import takewhile, count
import operator

from helpers import parallel_foreach
from packages.pyresto.apis import GitHub


# CONSTANTS
MAX_COMMITS_PER_BRANCH = 200


class User(GitHub.User):
    # Class name should be "user" to preserve compatibility
    # with the path variable defined on the main model

    @staticmethod
    def sort_languages(lang_stats):
        return sorted(lang_stats, key=lang_stats.get, reverse=True)

    @staticmethod
    def __lang_stat_reducer(stats, lang):
        stats[lang] = stats.setdefault(lang, 0) + 1
        return stats

    @property
    def language_stats(self):
        return reduce(self.__lang_stat_reducer,
                      (repo.language for repo in self.repos if repo.language),
                      {})

    @property
    def project_followers(self):
        return reduce(operator.add,
                      (repo.watchers for repo in self.repos
                       if repo.owner.login == self.login),
                      0)

    @staticmethod
    def __make_commit_recency_checker(recent_than, lim=MAX_COMMITS_PER_BRANCH):
        counter = count(lim, -1) if lim else count(1, 0)
        # if lim is None or 0, then return always 1

        def commit_checker(c):
            return counter.next() > 0 and\
                   c.commit['committer']['date'] >= recent_than
        return commit_checker

    def get_latest_commits(self, recent_than=None):
        if not recent_than:
            recent_than = datetime.datetime.today() - \
                          datetime.timedelta(days=14)
        recent_than = recent_than.isoformat()[:10]

        all_commits = deque()
        is_recent = self.__make_commit_recency_checker(recent_than)

        def collect_commits(branch):
            all_commits.extend(commit for commit
                                in takewhile(is_recent, branch.commits) if
                                (commit.author and commit.author['login'] or
                                 commit.committer and
                                 commit.committer['login']) == self.login)

        def repo_collector(repo):
            if repo.pushed_at < recent_than:
                return
            parallel_foreach(collect_commits, repo.branches)

        parallel_foreach(repo_collector, self.repos)

        return all_commits
