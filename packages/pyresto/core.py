# coding: utf-8

import httplib
import json
import logging
from urllib import quote

__all__ = ('Model', 'Many', 'Foreign')

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
                instance = self.__model(**data)
                #set auto fetching true for man fields which usually contain a summary
                instance._auto_fetch = True
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
            path = self.__path % path_params
            
            logging.debug('Call many path: %s' % path)
            data = model._rest_call(method='GET', url=path) or []
            self.__cache[instance] = WrappedList(data, self._with_owner(instance))
        return self.__cache[instance]


class Foreign(Relation):
    def __init__(self, model, key_extractor=None):
        self.__model = model
        model_name = model.__name__.lower()
        model_pk = model._pk
        self.__key_extractor = key_extractor if key_extractor else \
            lambda x:{model_pk: getattr(x, '__' + model_name)[model_pk]}
        
        self.__cache = {}
    
    def __get__(self, instance, owner):
        if not instance:
            return self.__model
        
        if instance not in self.__cache:
            keys = instance._get_id_dict()
            keys.update(self.__key_extractor(instance))
            logging.debug('Keys dict for foreign acccess: %s', str(keys))
            pk = keys.pop(self.__model._pk)
            self.__cache[instance] = self.__model.get(pk, **keys)
        
        return self.__cache[instance]


class Model(object):
    __metaclass__ = ModelBase
    _secure = True
    _continuator = lambda x, y:None
    _parser = staticmethod(json.loads)
    _fetched = False
    _get_params = dict()
    
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        
        cls = self.__class__
        overlaps = set(cls.__dict__) & set(kwargs)
        #logging.debug('Found overlaps: %s', str(overlaps))
        for item in overlaps:
            if issubclass(getattr(cls, item), Model):
                self.__dict__['__' + item] = self.__dict__.pop(item)
    
    def _get_id_dict(self):
        ids = {}
        owner = self
        while owner:
            ids[owner.__class__.__name__.lower()] = getattr(owner, owner._pk)
            owner = getattr(owner, '_owner', None)
        return ids
    
    @classmethod
    def _rest_call(cls, **kwargs):
        conn = cls._connection
        
        try:
            conn.request(**kwargs)
            response = conn.getresponse()
        except Exception as e:
            #should call conn.close() on any error to allow further calls to be made
            logging.debug('httplib error: %s', e.__class__.__name__)
            conn.close()
            return None
        
        logging.debug('Response code: %s', response.status)
        if response.status == 200:
            continuation_url = cls._continuator(response)
            encoding = response.getheader('content-type', '').split('charset=')
            encoding = encoding[1] if len(encoding) > 1 else 'utf-8'
            data = cls._parser(unicode(response.read(), encoding, 'replace'))
            if continuation_url:
                logging.debug('Found more at: %s', continuation_url)
                kwargs['url'] = continuation_url
                data += cls._rest_call(**kwargs)
            
            return data
    
    def __fetch(self):
        path = self._path % self.__dict__
        data = self._rest_call(method='GET', url=path)
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
        path = cls._path % kwargs
        data = cls._rest_call(method='GET', url=path)
        
        if not data:
            return
        
        instance = cls(**data)
        instance._get_params = kwargs
        instance._fetched = True
        return instance

