# coding: utf-8

import httplib
import json
import logging
from urllib import quote

__all__ = ('Error', 'Model', 'Many', 'Foreign')


class Error(Exception):
    pass


class ModelBase(type):
    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return super(ModelBase, cls).__new__(cls, name, bases, attrs)
        new_class = type.__new__(cls, name, bases, attrs)

        if not hasattr(new_class, '_path'):
            new_class._path = u'/{}/{{id}}'.format(quote(name.lower()))
        else:
            new_class._path = unicode(new_class._path)

        if new_class._secure:
            conn_class = httplib.HTTPSConnection
        else:
            conn_class = httplib.HTTPConnection
        new_class._get_connection = classmethod(lambda c: conn_class(c._host))

        return new_class


class WrappedList(list):
    def __init__(self, iterable, wrapper):
        super(self.__class__, self).__init__(iterable)
        self.__wrapper = wrapper

    def __getitem__(self, key):
        item = super(self.__class__, self).__getitem__(key)
        should_wrap = (isinstance(item, dict) or isinstance(key, slice) and
                       any(isinstance(it, dict) for it in item))

        if should_wrap:
            item = (map(self.__wrapper, item)
                    if isinstance(key, slice) else self.__wrapper(item))
            self[key] = item

        return item

    def __getslice__(self, i, j):
        items = super(self.__class__, self).__getslice__(i, j)
        if any(isinstance(it, dict) for it in items):
            items = map(self.__wrapper, items)
            self[i:j] = items
        return items

    def __iter__(self):
        iterator = super(self.__class__, self).__iter__()
        return (self.__wrapper(item) for item in iterator)

    def __contains__(self, item):
        return item in iter(self)


class LazyList(object):
    def __init__(self, wrapper, fetcher):
        self.__wrapper = wrapper
        self.__fetcher = fetcher

    def __iter__(self):
        fetcher = self.__fetcher
        while fetcher:
            data, fetcher = fetcher()
            for item in data:
                yield self.__wrapper(item)


class Relation(object):
    pass


class Many(Relation):
    def __init__(self, model, path=None, lazy=False):
        self.__model = model
        self.__path = unicode(path) or model._path
        self.__lazy = lazy
        self.__cache = {}

    def _with_owner(self, owner):
        def mapper(data):
            if isinstance(data, dict):
                instance = self.__model(**data)
                # set auto fetching true for man fields
                # which usually contain a summary
                instance._auto_fetch = True
                instance._pyresto_owner = owner
                return instance
            elif isinstance(data, self.__model):
                return data

        return mapper

    def __make_fetcher(self, url):
        def fetcher():
            data, new_url = self.__model._rest_call(method='GET',
                                                    url=url,
                                                    fetch_all=False)
            if not data:
                data = []

            new_fetcher = self.__make_fetcher(new_url) if new_url else None
            return data, new_fetcher

        return fetcher

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
            path = self.__path.format(**path_params)

            if self.__lazy:
                self.__cache[instance] = LazyList(self._with_owner(instance),
                                                  self.__make_fetcher(path))
            else:
                data, next_url = model._rest_call(method='GET', url=path)
                self.__cache[instance] =\
                            WrappedList(data or [], self._with_owner(instance))
        return self.__cache[instance]


class Foreign(Relation):
    def __init__(self, model, key_property=None, key_extractor=None):
        self.__model = model
        if not key_property:
            key_property = model.__name__.lower()
        model_pk = model._pk
        self.__key_extractor = (key_extractor if key_extractor else
            lambda x: {model_pk: getattr(x, '__' + key_property)[model_pk]})

        self.__cache = {}

    def __get__(self, instance, owner):
        if not instance:
            return self.__model

        if instance not in self.__cache:
            keys = instance._get_id_dict()
            keys.update(self.__key_extractor(instance))
            pk = keys.pop(self.__model._pk)
            self.__cache[instance] = self.__model.get(pk, **keys)

        return self.__cache[instance]


class Model(object):
    __metaclass__ = ModelBase
    _secure = True
    _continuator = lambda x, y: None
    _parser = staticmethod(json.loads)
    _fetched = False
    _get_params = dict()

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

        cls = self.__class__
        overlaps = set(cls.__dict__) & set(kwargs)

        for item in overlaps:
            if issubclass(getattr(cls, item), Model):
                self.__dict__['__' + item] = self.__dict__.pop(item)

        try:
            self._current_path = self._path and (
            self._path.format(**self.__dict__))
        except KeyError:
            self._current_path = None

    @property
    def _id(self):
        return getattr(self, self._pk)

    def _get_id_dict(self):
        ids = {}
        owner = self
        while owner:
            ids[owner.__class__.__name__.lower()] = owner
            owner = getattr(owner, '_pyresto_owner', None)
        return ids

    @classmethod
    def _rest_call(cls, fetch_all=True, **kwargs):
        conn = cls._get_connection()
        response = None
        try:
            conn.request(**kwargs)
            response = conn.getresponse()
        except Exception as e:
            # should call conn.close() on any error
            # to allow further calls to be made
            conn.close()
            if isinstance(e, httplib.BadStatusLine):
                if not response:  # retry
                    return cls._rest_call(fetch_all, **kwargs)
            else:
                raise e

        if response.status >= 200 and response.status < 300:
            continuation_url = cls._continuator(response)
            encoding = response.getheader('content-type', '').split('charset=')
            encoding = encoding[1] if len(encoding) > 1 else 'utf-8'
            response_data = unicode(response.read(), encoding, 'replace')
            data = cls._parser(response_data) if response_data else None
            if continuation_url:
                logging.debug('Found more at: %s', continuation_url)
                if fetch_all:
                    kwargs['url'] = continuation_url
                    data += cls._rest_call(**kwargs)[0]
                else:
                    return data, continuation_url
            return data, None
        else:
            conn.close()
            logging.error("URL returned HTTP %d: %s", response.status, kwargs)
            raise Error("Server response not OK. Response code: %d" %
                        response.status)

    def __fetch(self):
        if not self._current_path:
            self._fetched = True
            return

        data, next_url = self._rest_call(method='GET', url=self._current_path)
        if next_url:
            self._current_path = next_url

        if data:
            self.__dict__.update(data)
            self._fetched = True

    def __getattr__(self, name):
        if self._fetched:
            raise AttributeError
        self.__fetch()
        return getattr(self, name)

    @classmethod
    def get(cls, model_id, **kwargs):
        kwargs[cls._pk] = model_id
        path = cls._path.format(**kwargs)
        data = cls._rest_call(method='GET', url=path)[0]

        if not data:
            return

        instance = cls(**data)
        instance._get_params = kwargs
        instance._fetched = True
        return instance
