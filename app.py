# coding: utf-8

import os
import posixpath
import re
import sys
import urllib2

from django.utils import simplejson as json
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import models

sys.setrecursionlimit(10000) # SDK fix


class Github(object):
  pass


class Handler(webapp.RequestHandler):
	def render(self, file, values = {}):
		path = posixpath.join(posixpath.dirname(__file__), 'templates/%s.html' % file)
		self.response.out.write(template.render(path, values))

	def write(self, string):
		self.response.out.write(string)


class MainHandler(Handler):
	def get(self):
		self.render('index')


class WidgetHandler(Handler):
  def get(self, username):
    url = 'https://api.github.com/users/%s' % (username)
    json_string = urllib2.urlopen(url).read()    
    self.render('widget', {'user': json.loads(json_string)})

  def post(self):
    self.write('Save')


application = webapp.WSGIApplication(
	[
    ('/', MainHandler),
    ('/widget/(\w+)', WidgetHandler),
	],
	debug = os.environ.get('SERVER_SOFTWARE', None).startswith('Devel')
)

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
