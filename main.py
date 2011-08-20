# coding: utf-8

from app.core import *
#from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

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
