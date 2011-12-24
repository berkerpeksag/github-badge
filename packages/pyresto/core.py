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
            new_class._path = '/{}/{{id}}'.format(quote(name.lower()))

        if new_class._secure:
            conn_class = httplib.HTTPSConnection
        else:
            conn_class = httplib.HTTPConnection
        new_class._connection = conn_class(new_class._host)

        return new_class


class WrappedList(list):
    def __init__(self, iterable, wrapper):
        super(self.__class__, self).__init__(iterable)
        self.__wrapper = wrapper

    def __getitem__(self, key):
        item = super(self.__class__, self).__getitem__(key)
        should_wrap = isinstance(item, dict) or isinstance(key, slice)\
        and any(isinstance(it, dict) for it in item)

        if should_wrap:
            item = map(self.__wrapper, item) if isinstance(key, slice)\
            else self.__wrapper(item)
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


class LazyList(object):
    __length = None

    def __init__(self, data, wrapper, fetcher):
        self.__data = data
        self.__length = len(data)
        self.__wrapper = wrapper
        self.__fetcher = fetcher

    def __iter__(self):
        cursor = 0
        while cursor < self.__length or self.__fetcher:
            if cursor >= self.__length:
                new_data, new_fetcher = self.__fetcher()
                self.__fetcher = new_fetcher
                if not new_data:
                    break
                self.__data.extend(new_data)
                self.__length = len(self.__data)

            item = self.__data[cursor]
            if isinstance(item, dict):  # not wrapped
                item = self.__wrapper(item)
                self.__data[cursor] = item

            cursor += 1
            yield item

    def iter_while(self, checker):
        for item in self:
            if checker(item):
                yield item
            else:
                break

    def collect_while(self, checker):
        return [item for item in self.iter_while(checker)]

    def collect_upto(self, checker, limit=10):
        results = []
        for item in self:
            if limit < 1:
                break
            elif checker(item):
                results.append(item)
                limit -= 1
        return results


class Relation(object):
    pass


class Many(Relation):
    def __init__(self, model, path=None, lazy=False):
        self.__model = model
        self.__path = path or model._path
        self.__lazy = lazy
        self.__cache = {}

    def _with_owner(self, owner):
        def mapper(data):
            if isinstance(data, dict):
                instance = self.__model(**data)
                # set auto fetching true for man fields
                # which usually contain a summary
                instance._auto_fetch = True
                instance._owner = owner
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

            data, next_url = model._rest_call(method='GET',
                                              url=path,
                                              fetch_all=(not self.__lazy))
            if not data:
                data = []

            if self.__lazy:
                self.__cache[instance] = LazyList(data,
                                                  self._with_owner(instance),
                                                  self.__make_fetcher(next_url)
                )
            else:
                self.__cache[instance] = WrappedList(data,
                                                     self._with_owner(instance)
                )
        return self.__cache[instance]


class Foreign(Relation):
    def __init__(self, model, key_extractor=None):
        self.__model = model
        model_name = model.__name__.lower()
        model_pk = model._pk
        self.__key_extractor = key_extractor if key_extractor else\
        lambda x: {model_pk: getattr(x, '__' + model_name)[model_pk]}

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
            self._current_path = self._path and (self._path.format(**self.__dict__))
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
            owner = getattr(owner, '_owner', None)
        return ids

    @classmethod
    def _rest_call(cls, fetch_all=True, **kwargs):
        conn = cls._connection
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
                    return cls._restcall(fetch_all, **kwargs)
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
    def get(cls, id, **kwargs):
        kwargs[cls._pk] = id
        path = cls._path.format(**kwargs)
        data = cls._rest_call(method='GET', url=path)[0]

        if not data:
            return

        instance = cls(**data)
        instance._get_params = kwargs
        instance._fetched = True
        return instance
