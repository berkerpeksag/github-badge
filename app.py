# coding: utf-8

import logging
import os
import posixpath
import re
import sys

from google.appengine.api import users
from google.appengine.ext import blobstore
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import models


sys.setrecursionlimit(10000) # SDK fix


class Handler(webapp.RequestHandler):
	def __init__(self):
		self.user = users.get_current_user()

		if self.user:
			self.url = users.create_logout_url('/')
			self.is_logged = True
		else:
			self.url = users.create_login_url('/')
			self.is_logged = False

		self.values = {
			'user': self.user,
			'url': self.url,
			'is_logged': self.is_logged
		}

	def get_user_info(self):
		if self.is_logged:
			return models.User.gql('WHERE name=:1', self.user).get()
		else:
			return None

	def render(self, file, values = {}):
		values.update(self.values)
		path = posixpath.join(posixpath.dirname(__file__), 'templates/%s.html' % file)
		self.response.out.write(template.render(path, values))

	def write(self, string):
		self.response.out.write(string)


class MainHandler(Handler):
	def get(self):
		self.render('index')


class FooHandler(Handler):
    def get(self):
        self.write('Lorem ipsum dolor sit amet.')


application = webapp.WSGIApplication(
	[
        ('/', MainHandler),
        ('/foo', FooHandler),
	],
	debug = True
)

def main():
	logging.getLogger().setLevel(logging.DEBUG)
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
