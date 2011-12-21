# coding: utf-8

import datetime
import threading
import operator
from packages.pyresto.apis import GitHub


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
                      (repo.watchers for repo in self.repos), 0)

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
        threads = []
        def collect_commits(branch):
            all_commits.extend(branch.commits.collect_while(is_recent))

        for repo in self.repos:
            if repo.pushed_at >= recent_than:
                for branch in repo.branches:
                    threads.append(threading.Thread(target=collect_commits,
                                                    args=(branch,)))

        for t in threads:
            t.start()

        for t in threads:
            if t.is_alive():
                t.join()

        own_commits = [commit for commit in all_commits
                       if
                       commit.author and commit.author['login'] == self.login or
                       commit.committer and
                       commit.committer['login'] == self.login]

        return own_commits
