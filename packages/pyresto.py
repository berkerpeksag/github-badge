import httplib
from django.utils import simplejson as json
import logging
from urllib import quote

__all__ = ['Model', 'Many', 'Foreign']

logging.getLogger().setLevel(logging.DEBUG)

class ModelBase(type):
  def __new__(cls, name, bases, attrs):
    if name == 'Model':
      return super(ModelBase, cls).__new__(cls, name, bases, attrs)
    new_class = type.__new__(cls, name, bases, attrs)

    if not hasattr(new_class, '_path'):
      new_class._path = '/%s/%%(id)s' % quote(name.lower())

    conn_class = httplib.HTTPSConnection if new_class._secure else httplib.HTTPConnection
    new_class._connection = conn_class(new_class._host)

    return new_class


class WrappedList(list):
  def __init__(self, iterable, wrapper):
    super(self.__class__, self).__init__(iterable)
    self.__wrapper = wrapper

  @staticmethod
  def is_dict(obj):
    return isinstance(obj, dict)

  def __getitem__(self, key):
    item = super(self.__class__, self).__getitem__(key)
    should_wrap = self.is_dict(item) or isinstance(key, slice) and any(map(self.is_dict, item))
    if should_wrap:
      item = map(self.__wrapper, item) if isinstance(key, slice) \
        else self.__wrapper(item)
      self[key] = item

    return item

  def __getslice__(self, i, j):
    items = super(self.__class__, self).__getslice__(i, j)
    if any(map(self.is_dict, items)):
      items = map(self.__wrapper, items)
      self[i:j] = items
    return items

  def __iter__(self):
    iterator = super(self.__class__, self).__iter__()
    return (self.__wrapper(item) for item in iterator)


class Relation(object):
  pass


class Many(Relation):
  def __init__(self, model, path=None):
    self.__model = model
    self.__path = path or model._path
    self.__cache = {}

  def _with_owner(self, owner):
    def mapper(data):
      if isinstance(data, dict):
        data = dict((k.encode('utf8'), v) for (k, v) in data.items()) #unicode fix for Python 2.6-
        instance = self.__model(**data)
        instance._id = instance._get_id()
        instance._owner = owner
        return instance
      elif isinstance(data, self.__model):
        return data
    return mapper

  def __get__(self, instance, owner):
    if not instance:
      return self.__model

    if instance not in self.__cache:
      model = self.__model
      if not instance:
        return model

      path_params = instance._get_id_dict()
      if hasattr(instance, '_get_params'):
        path_params.update(instance._get_params)
      logging.debug('Path params for many: ' + str(path_params))
      path = self.__path % path_params

      logging.debug('Call many path: %s' % path)
      data = model._rest_call(method='GET', url=path) or []
      self.__cache[instance] = WrappedList(data, self._with_owner(instance))
    return self.__cache[instance]


class Foreign(Relation):
  def __init__(self, model, key_extractor=None):
    self.__model = model
    self.__key_extractor = key_extractor if key_extractor else \
      lambda x:dict(id=x.__dict__['__' + model.__name__.lower()])

    self.__cache = {}

  def __get__(self, instance, owner):
    if not instance:
      return self.__model

    if instance not in self.__cache:
      keys = instance._get_id_dict()
      keys.update(self.__key_extractor(instance))
      self.__cache[instance] = self.__model.get(**keys)

    return self.__cache[instance]


class Model(object):
  __metaclass__ = ModelBase
  _secure = True
  _continuator = lambda x, y:None
  _parser = staticmethod(json.loads)
  _default_dict = dict()

  def __init__(self, **kwargs):
    self.__dict__.update(kwargs)
    cls = self.__class__
    overlaps = set(cls.__dict__) & set(kwargs)
    logging.debug('Found overlaps: ' + str(overlaps))
    for item in overlaps:
      if issubclass(getattr(cls, item), Model):
        self.__dict__['__' + item] = self.__dict__.pop(item)

  def _get_id_dict(self):
    ids = {}
    owner = self
    while owner:
      ids[owner.__class__.__name__.lower()] = owner._id
      owner = getattr(owner, '_owner', None)
    return ids

  @classmethod
  def _rest_call(cls, **kwargs):
    conn = cls._connection

    try:
      conn.request(**kwargs)
      response = conn.getresponse()
    except: #should call conn.close() on any error to allow further calls to be made
      conn.close()
      return None

    logging.debug('Response code: %s' % response.status)
    if response.status == 200:
      continuation_url = cls._continuator(response)
      data = cls._parser(response.read())
      if continuation_url:
        logging.debug('Found more at: ' + continuation_url)
        kwargs['url'] = continuation_url
        data += cls._rest_call(**kwargs)

      return data

  @classmethod
  def get(cls, id, **kwargs):
    default = kwargs.pop('_default', cls._default_dict.copy())
    kwargs.update(dict(id=quote(id)))
    path = cls._path % kwargs
    data = cls._rest_call(method='GET', url=path) or default
    data = dict((k.encode('utf8'), v) for (k, v) in data.items()) #unicode key fix for python 2.6-

    instance = cls(**data)
    instance._id = id
    instance._get_params = kwargs
    return instance

