# coding: utf-8

import datetime
import operator
from packages.pyresto.apis import GitHub


class User(GitHub.User):
    # Class name should be "user" to preserve compatibility
    # with the path variable defined on the main model
    _default_dict = dict(login='?',
                         html_url='#',
                         avatar_url='https://a248.e.akamai.net/'
                                    'assets.github.com'
                                    '/images/gravatars/gravatar-140.png',
                         name='?',
                         blog='#'
                        )

    @staticmethod
    def sort_languages(lang_stats):
        return sorted(lang_stats, key=lang_stats.get, reverse=True)

    @staticmethod
    def __lang_stat_reducer(stats, lang):
        if lang:
            stats[lang] = stats.setdefault(lang, 0) + 1
        return stats

    @property
    def language_stats(self):
        return reduce(self.__lang_stat_reducer,
                      (repo.language for repo in self.repos), {})

    @property
    def project_followers(self):
        return reduce(operator.add,
                      (repo.watchers for repo in self.repos), 0)

    @property
    def latest_commits(self, recent_than=None):
        if not recent_than:
            recent_than = datetime.datetime.today() - datetime.timedelta(days=7)
        recent_than = recent_than.isoformat()

        all_commits = reduce(operator.add, 
                             map(lambda x:x.commits,
                                 (repo for repo in self.repos
                                  if repo.pushed_at >= recent_than)
                                 ), [])
        own_commits = filter(lambda x:
                        x['committer'] and
                        x['committer']['login'] == self.login, all_commits)
        
        return sorted(own_commits, key=lambda x:x['commit']['committer']['date'])