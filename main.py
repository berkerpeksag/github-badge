# coding: utf-8

import os

from app.core import webapp2, MainHandler, BadgeHandler, CacheHandler


application = webapp2.WSGIApplication([
        ('/', MainHandler),
        ('/badge/([-\w]+)', BadgeHandler),
        ('/stats', CacheHandler),
    ],
    debug=os.environ.get('SERVER_SOFTWARE', None).startswith('Devel')
)
