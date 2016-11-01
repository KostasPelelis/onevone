from onevone import log

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class DBManager:

    def init(url):
        DBManager.engine = create_engine(url)
        DBManager.Session = sessionmaker(
            bind=DBManager.engine, autoflush=False)
        DBManager.ScopedSession = scoped_session(
            sessionmaker(bind=DBManager.engine))

    def create_session(**options):
        """
        Useful options:
        expire_on_commit=False
        """

        try:
            return DBManager.Session(**options)
        except:
            log.exception('Unhandled exception while creating a session')

        return None

    def create_scoped_session(**options):
        """
        Useful options:
        expire_on_commit=False
        """

        try:
            return DBManager.ScopedSession(**options)
        except:
            loglog.exception(
                'Unhandled exception while creating a scoped session')

        return None

    @contextmanager
    def create_session_scope(**options):
        session = DBManager.create_session(**options)
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def create_session_scope_nc(**options):
        session = DBManager.create_session(**options)
        try:
            yield session
        except:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def create_session_scope_ea(**options):
        session = DBManager.create_session(**options)
        try:
            yield session
            session.expunge_all()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def create_scoped_session_scope(**options):
        session = DBManager.create_scoped_session(**options)
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
