import os


class Config(object):
    DEBUG = False
    TESTING = False
    CSRF_ENABLED = True
    DATABASE_URI = os.environ['ONEVONE_DEV_DB']
    RIOT_API_KEY = os.environ['RIOT_API_KEY']


class ProductionConfig(Config):
    DATABASE_URI = os.environ['ONEVONE_PRODUCTION_DB']

class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
