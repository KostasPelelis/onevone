import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from alembic import command, config
import os
import pwd

from onevone.logger import init_logging
from onevone.app import log
from onevone.app import app

alebic_logger = init_logging(name='alembic')

from onevone.utils import (StaticDataContext)


def generate_migration(cfg, message='Initial Version'):
    # Alembic has a bug with ARRAY type. This is a temporary workaround
    command.revision(cfg, message='Initial Version', autogenerate=True)
    result = []
    pattern = '_'.join([chunk.lower() for chunk in message.split(' ')])
    for root, dirs, files in os.walk('./alembic/versions'):
        for name in files:
            if pattern in name:
                result.append(os.path.join(root, name))

    with open(result[0], 'r') as file:
        filedata = file.read()

    # Replace the target string
    filedata = filedata.replace('ARRAY(', 'ARRAY(sa.')

    # Write the file out again
    with open(result[0], 'w') as file:
        file.write(filedata)


def create_database():
    engine = psycopg2.connect(os.environ['PSQL_ADMIN_URI'])
    engine.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = engine.cursor()
    try:
        conn = psycopg2.connect(app.config['DATABASE_URI'])
        log.info('Already found a database. It will be destroyed and recreated')
        conn.close()
        cur.execute('DROP DATABASE onevone_production')
    except Exception as e:
        log.error(e)
        log.warn('Production Database does not exist. Creating')

    cur.execute('CREATE DATABASE onevone_production')
    log.info('Database onevone_production created')
    cur.close()
    engine.close()
    cfg = config.Config("./alembic.ini")
    log.info('Creating Migration File')
    generate_migration(cfg)
    log.info('Runing migrations')
    filedata = None
    command.upgrade(cfg, "head")
    log.info('Done applying migrations')
    StaticDataContext.populate_static_data()
    StaticDataContext.generate_static_images()

if __name__ == "__main__":
    create_database()
