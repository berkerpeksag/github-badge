# coding: utf-8

import os

from app.core import webapp, MainHandler, BadgeHandler, CacheHandler
from google.appengine.ext.webapp.util import run_wsgi_app

# Load custom Django template filters
webapp.template.register_template_library('app.customfilters')

application = webapp.WSGIApplication([
        ('/', MainHandler),
        ('/badge/([-\w]+)', BadgeHandler),
        ('/stats', CacheHandler),
    ],
    debug=os.environ.get('SERVER_SOFTWARE', None).startswith('Devel')
)


def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
