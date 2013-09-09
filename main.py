# coding: utf-8

import webapp2

from app.config import current as conf
from app.core import MainHandler, BadgeHandler


application = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/badge/([-\w]+)', BadgeHandler)],
    debug=conf.DEBUG,
    config=dict((name, getattr(conf, name))
                for name in dir(conf) if not name.startswith('_'))
)
