# coding: utf-8

import os

from app.core import webapp2, MainHandler, BadgeHandler


application = webapp2.WSGIApplication([
        ('/', MainHandler),
        ('/badge/([-\w]+)', BadgeHandler),
    ],
    debug=os.environ.get('SERVER_SOFTWARE', None).startswith('Devel')
)
