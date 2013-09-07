# coding: utf-8

from operator import itemgetter  # built-in

from requests.auth import AuthBase  # third party

from pyresto.core import Foreign, Many, Model, AuthList, enable_auth


class QSAuth(AuthBase):
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __call__(self, req):
        if not req.redirect:
            req.params['username'] = self.username
            req.params['password'] = self.password
        return req


class BugzillaModel(Model):
    _url_base = __service_url__

    def __repr__(self):
        if hasattr(self, 'ref'):
            desc = self.ref
        else:
            desc = self._current_path

        return '<Bugzilla.{0} [{1}]>'.format(self.__class__.__name__, desc)

    @classmethod
    def _rest_call(cls, url, method='GET', fetch_all=True, **kwargs):
        if 'headers' not in kwargs:
            kwargs['headers'] = dict()

        kwargs['headers']['Content-Type'] = 'application/json'
        kwargs['headers']['Accept'] = 'application/json'

        return super(BugzillaModel, cls)._rest_call(url, method, fetch_all,
                                                    **kwargs)


class User(BugzillaModel):
    _path = 'user/{email}'
    _pk = 'email'


class Comment(BugzillaModel):
    _path = None
    _pk = 'id'

    creator = Foreign(User, '__creator', embedded=True)


class Flag(BugzillaModel):
    _path = None
    _pk = 'id'

    setter = Foreign(User, '__setter', embedded=True)


class Group(BugzillaModel):
    _path = 'group/{name}'
    _pk = 'name'


class ChangeSet(BugzillaModel):
    _path = None
    _pk = tuple()

    changer = Foreign(User, '__changer', embedded=True)


class Attachment(BugzillaModel):
    _path = 'attachment/{id}?exclude_fields=flags'
    _pk = 'id'

    attacher = Foreign(User, '__attacher', embedded=True)
    flags = Many(Flag, 'attachment/{id}?include_fields=flags',
                 preprocessor=itemgetter('flags'))


class Bug(BugzillaModel):
    _path = 'bug/{id}'
    _pk = 'id'

    @classmethod
    def init_many_fields(cls, many_fields):
        for field, model in many_fields.iteritems():
            path = cls._path + '?include_fields=' + field
            if model is cls:
                preprocessor = lambda d: list(dict(id=b) for b in d[field])
            else:
                preprocessor = itemgetter(field)
            setattr(cls, field, Many(model, path, preprocessor=preprocessor))
        cls._path = cls._path + '?include_fields=_all&exclude_fields=' + \
                   ','.join(many_fields.keys())

        return cls


    assigned_to = Foreign(User, '__assigned_to', embedded=True)
    creator = Foreign(User, '__creator', embedded=True)
    qa_contact = Foreign(User, '__qa_contact', embedded=True)


# late bindings
Attachment.bug = Foreign(Bug, 'bug_id')
Bug.dupe_of = Foreign(Bug, '__dupe_of')  # only present if RESOLVED DUPLICATE

# initialize all many fields at once for the sake of DRY
Bug.init_many_fields({
    'attachments': Attachment,
    'blocks': Bug,
    'cc': User,
    'comments': Comment,
    'depends_on': Bug,
    'groups': Group,
    'history': ChangeSet
})


# define authentication methods
auths = AuthList(querystring=QSAuth)

# enable and publish global authentication
auth = enable_auth(auths, BugzillaModel, 'querystring')
