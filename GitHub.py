import re
from pyresto import *

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

  def _get_id(self):
    return self.id


class Commit(GitHubModel):
  _path = '/repos/%(user)s/%(repo)s/commits/%(id)s'
  comments = Many(Comment, '/repos/%(user)s/%(repo)s/commits/%(commit)s/comments')

  def _get_id(self):
    return self.sha


class Branch(GitHubModel):
  _path = None
  commit = Foreign(Commit, key_extractor=lambda x:dict(id=x.__dict__['__commit']['sha']))

  def _get_id(self):
    return self.name
Tag = Branch


class Repo(GitHubModel):
  _path = '/repos/%(user)s/%(id)s'
  commits = Many(Commit, '/repos/%(user)s/%(repo)s/commits')
  comments = Many(Comment, '/repos/%(user)s/%(repo)s/comments')
  tags = Many(Tag, '/repos/%(user)s/%(repo)s/tags')
  branches = Many(Branch, '/repos/%(user)s/%(repo)s/branches')

  def _get_id(self):
    return self.name


class User(GitHubModel):
  _path = '/users/%(id)s'
  repos = Many(Repo, '/users/%(user)s/repos?per_page=100')

  def _get_id(self):
    return self.login

#Late bindings due to circular references
Repo.contributors = Many(User, '/repos/%(user)s/%(repo)s/contributors')
User.follower_list = Many(User, '/users/%(user)s/followers')
