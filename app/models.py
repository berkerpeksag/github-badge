# coding: utf-8

import datetime
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
    def __make_commit_recency_checker(recent_than):
        return lambda c: c.commit['committer']['date'] >= recent_than

    def get_latest_commits(self, recent_than=None):
        if not recent_than:
            recent_than = datetime.datetime.today() - \
                          datetime.timedelta(days=14)
        recent_than = recent_than.isoformat()[:10]

        all_commits = []
        is_recent = self.__make_commit_recency_checker(recent_than)

        def collect_commits(branch):
            new_commits = [commit for commit
                           in branch.commits.iter_upto(
                            is_recent, MAX_COMMITS_PER_BRANCH) if
                           (commit.author or
                            commit.committer)['login'] == self.login]
            all_commits.extend(new_commits)

        def repo_collector(repo):
            if repo.pushed_at >= recent_than:
                parallel_foreach(collect_commits, repo.branches)

        parallel_foreach(repo_collector, self.repos)

        return all_commits
