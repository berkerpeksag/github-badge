# coding: utf-8

from requests.auth import AuthBase, HTTPBasicAuth  # third party

from ...core import Foreign, Many, Model, AuthList, enable_auth


class AppQSAuth(AuthBase):
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    def __call__(self, req):
        if not req.redirect:
            req.params['client_id'] = self.client_id
            req.params['client_secret'] = self.client_secret
        return req


class GitHubModel(Model):
    _url_base = 'https://api.github.com'

    def __repr__(self):
        if hasattr(self, '_links'):
            desc = self._links['self']
        elif hasattr(self, 'url'):
            desc = self.url
        else:
            desc = self._current_path

        return '<GitHub.{0} [{1}]>'.format(self.__class__.__name__, desc)


class Comment(GitHubModel):
    _path = '/repos/{repo_name}/comments/{id}'
    _pk = ('repo_name', 'id')


class Commit(GitHubModel):
    _path = '/repos/{repo_name}/commits/{sha}'
    _pk = ('repo_name', 'sha')
    comments = Many(Comment, '{self._current_path}/comments?per_page=100')


class Branch(GitHubModel):
    _path = '/repos/{repo_name}/branches/{name}'
    _pk = ('repo_name', 'name')
    commit = Foreign(Commit, embedded=True)
    commits = Many(Commit, '/repos/{repo_name}/commits'
                           '?per_page=100&sha={self._id}', lazy=True)


class Tag(GitHubModel):
    _path = '/repos/{repo_name}/tags/{name}'
    _pk = ('repo_name', 'name')
    commit = Foreign(Commit, embedded=True)


class Key(GitHubModel):
    _path = '/user/keys/{id}'
    _pk = 'id'


class Repo(GitHubModel):
    _path = '/repos/{full_name}'
    _pk = 'full_name'
    commits = Many(Commit, '{self._current_path}/commits?per_page=100', lazy=True)
    comments = Many(Comment, '{self._current_path}/comments?per_page=100')
    tags = Many(Tag, '{self._current_path}/tags?per_page=100')
    branches = Many(Branch, '{self._current_path}/branches?per_page=100')
    keys = Many(Key, '{self._current_path}/keys?per_page=100')


class User(GitHubModel):
    _path = '/users/{login}'
    _pk = 'login'

    repos = Many(Repo, '{self._current_path}/repos?type=all&per_page=100')


class Me(User):
    _path = '/user'
    repos = Many(Repo, '/user/repos?type=all&per_page=100')
    keys = Many(Key, '/user/keys?per_page=100')

    @classmethod
    def get(cls, **kwargs):
        return super(Me, cls).get(None, **kwargs)


# Late bindings due to circular references
Commit.committer = Foreign(User, '__committer', embedded=True)
Commit.author = Foreign(User, '__author', embedded=True)
Repo.contributors = Many(User,
                         '{self._current_path}/contributors?per_page=100')
Repo.owner = Foreign(User, '__owner', embedded=True)
Repo.watcher_list = Many(User, '{self._current_path}/watchers?per_page=100')
User.follower_list = Many(User, '{self._current_path}/followers?per_page=100')
User.watched = Many(Repo, '{self._current_path}/watched?per_page=100')

# Define authentication methods
auths = AuthList(basic=HTTPBasicAuth, app=AppQSAuth)

# Enable and publish global authentication
auth = enable_auth(auths, GitHubModel, 'app')
