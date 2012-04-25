# coding: utf-8

import re
from ..core import Foreign, Many, Model


class GitHubModel(Model):
    _host = 'api.github.com'
    _link_parser = re.compile(r'\<([^\>]+)\>;\srel="(\w+)"', re.I | re.U)

    @classmethod
    def _continuator(cls, response):
        link_val = response.getheader('Link', None)
        if not link_val:
            return

        links = dict(((cls._link_parser.match(link.strip()).group(2, 1)
        for link in link_val.split(','))))
        return links.setdefault('next', None)

    def __eq__(self, other):
        return  isinstance(other, self.__class__) and self.url == other.url


class Comment(GitHubModel):
    _path = '{repo.url}/comments/{id}'
    _pk = 'id'


class Commit(GitHubModel):
    _path = '{repo.url}/commits/{sha}'
    _pk = 'sha'
    comments = Many(Comment, '{commit.url}/comments?per_page=100')


class Branch(GitHubModel):
    _path = None
    _pk = 'name'
    commit = Foreign(Commit)
    commits = Many(Commit, '{repo.url}/commits?per_page=100&sha={branch._id}',
                   lazy=True)


class Tag(GitHubModel):
    _path = None
    _pk = 'name'
    commit = Foreign(Commit)


class Repo(GitHubModel):
    _path = '{user.url}/{name}'
    _pk = 'name'
    commits = Many(Commit, '{repo.url}/commits?per_page=100', lazy=True)
    comments = Many(Comment, '{repo.url}/comments?per_page=100')
    tags = Many(Tag, '{repo.url}/tags?per_page=100')
    branches = Many(Branch, '{repo.url}/branches?per_page=100')


class User(GitHubModel):
    _path = '/users/{login}'
    _pk = 'login'
    repos = Many(Repo, '{user.url}/repos?type=all&per_page=100')


# Late bindings due to circular references
Repo.contributors = Many(User, '{repo.url}/contributors?per_page=100')
Repo.owner = Foreign(User, 'owner')
Repo.watcher_list = Many(User, '{repo.url}/watchers?per_page=100')
User.follower_list = Many(User, '{user.url}/followers?per_page=100')
User.watched = Many(Repo, '{user.url}/watched?per_page=100')
