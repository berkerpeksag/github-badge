# coding: utf-8

import re
from ..core import *

class GitHubModel(Model):
    _host = 'api.github.com'

    _link_parser = re.compile(r'\<([^\>]+)\>;\srel="(\w+)"', re.I or re.U)
    @classmethod
    def _continuator(cls, response):
        link_val = response.getheader('Link', None)
        if not link_val: return

        links = dict(((cls._link_parser.match(link.strip()).group(2, 1)
                     for link in link_val.split(','))))
        return links.setdefault('next', None)


class Comment(GitHubModel):
    _path = '/repos/%(user)s/%(repo)s/comments/%(id)s'
    _pk = 'id'


class Commit(GitHubModel):
    _path = '/repos/%(user)s/%(repo)s/commits/%(sha)s'
    _pk = 'sha'
    comments = Many(Comment, '/repos/%(user)s/%(repo)s/commits/%(commit)s/comments')


class Branch(GitHubModel):
    _path = None
    _pk = 'name'
    commit = Foreign(Commit)
Tag = Branch


class Repo(GitHubModel):
    _path = '/repos/%(user)s/%(name)s'
    _pk = 'name'
    commits = Many(Commit, '/repos/%(user)s/%(repo)s/commits')
    comments = Many(Comment, '/repos/%(user)s/%(repo)s/comments')
    tags = Many(Tag, '/repos/%(user)s/%(repo)s/tags')
    branches = Many(Branch, '/repos/%(user)s/%(repo)s/branches')


class User(GitHubModel):
    _path = '/users/%(login)s'
    _pk = 'login'
    repos = Many(Repo, '/users/%(user)s/repos?per_page=100')


#Late bindings due to circular references
Repo.contributors = Many(User, '/repos/%(user)s/%(repo)s/contributors')
User.follower_list = Many(User, '/users/%(user)s/followers')
