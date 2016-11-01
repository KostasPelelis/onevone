from onevone.db_manager import DBManager
from onevone import log

from flask import Flask

app = Flask(__name__)
app.config.from_object('onevone.configuration.DevelopmentConfig')
DBManager.init(app.config['DATABASE_URI'])

from onevone import urls
