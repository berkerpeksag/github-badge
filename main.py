# coding: utf-8

import webapp2

from app.config import current as conf
from app.core import MainHandler, BadgeHandler, OldBadgeHandler


application = webapp2.WSGIApplication(
    [
        webapp2.Route('/<username:[-\w]+>', BadgeHandler),
        webapp2.Route('/badge/<username:[-\w]+>', OldBadgeHandler),
        webapp2.Route('/', MainHandler),
    ],
    debug=conf.DEBUG,
    config={name: getattr(conf, name) for name in dir(conf)
            if not name.startswith('_')}
)
