from google.appengine.ext import db

class User(db.Model):
    name = db.UserProperty(auto_current_user = True, auto_current_user_add = True)
    date = db.DateTimeProperty(auto_now = True, auto_now_add = True)
