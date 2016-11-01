from onevone.models.base import SerializedMixin
from onevone.db_manager import Base

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer, BIGINT
from sqlalchemy import Date

class ProPlayer(SerializedMixin, Base):

    __tablename__ = 'tb_pro_players'

    id = Column(BIGINT, primary_key=True)
    region = Column(String(100), index=True)
    tier = Column(String(30), index=True)
    name = Column(String(100))

    def __init__(self, data):
        self.id = data['id']
        self.region = data['region']
        self.tier = data['tier']
        self.name = data['name']


class QueuedMatch(SerializedMixin, Base):

    __tablename__ = 'tb_queued_matches'

    id = Column(BIGINT, primary_key=True)
    region = Column(String(100), index=True)
    added_at = Column(Date, index=True)
    match_timestamp = Column(BIGINT, index=True)

    def __init__(self, data):
        self.id = data['id']
        self.region = data['region']
        self.added_at = data['added_at']
        self.match_timestamp = data['match_timestamp']


class CheckedMatch(SerializedMixin, Base):

    __tablename__ = 'tb_checked_matches'

    id = Column(BIGINT, primary_key=True)
    region = Column(String(100), index=True)
    checked_at = Column(Date, index=True)
    match_timestamp = Column(BIGINT, index=True)

    def __init__(self, data):
        self.id = data['id']
        self.region = data['region']
        self.checked_at = data['checked_at']
        self.match_timestamp = data['match_timestamp']
