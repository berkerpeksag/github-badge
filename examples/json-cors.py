#!/usr/bin/env python
# coding: utf-8

import httplib
try:
    import json
except ImportError:
    import simplejson as json

headers = {'Accept': 'application/json'}

conn = httplib.HTTPConnection('githubbadge.appspot.com')
conn.request('GET', '/badge/berkerpeksag', headers=headers)

response = conn.getresponse()
result = response.read()
json = json.loads(result)

print 'Username: {}, Followers: {}'.format(json['user']['login'], json['user']['followers'])
