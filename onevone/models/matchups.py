from onevone.models.base import SerializedMixin
from onevone.db_manager import Base
from onevone.models.static import Champion

from sqlalchemy import Column
from sqlalchemy import Integer, Float
from sqlalchemy import Text
from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import ARRAY
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property


class Matchup(SerializedMixin, Base):

    __tablename__ = 'tb_matchups'

    id = Column(Integer, primary_key=True)
    champion = Column(Integer, ForeignKey(Champion.id), index=True)
    enemy = Column(Integer, ForeignKey(Champion.id), index=True)

    won = Column(Boolean)

    kills = Column(Integer)
    deaths = Column(Integer)
    assists = Column(Integer)
    damage_dealt = Column(Float)
    creep_score = Column(Integer)
    duration = Column(Integer)

    masteries = Column(ARRAY(Text))
    runes = Column(ARRAY(Text))
    summoners = Column(Text)

    patch_version = Column(Text, index=True)
    checked = Column(Boolean, index=True)

    def __init__(self, data):
        self.champion = data['champion']
        self.enemy = data['enemy']

        self.won = data['won']

        self.kills = data['kills']
        self.deaths = data['deaths']
        self.assists = data['assists']
        self.creep_score = data['creep_score']
        self.damage_dealt = data['damage_dealt']

        self.duration = data['duration']
        self.patch_version = data['patch_version']

        self.masteries = data['masteries']
        self.runes = data['runes']
        self.summoners = data['summoners']

        self.checked = False


class ItemTimeline(SerializedMixin, Base):

    __tablename__ = 'tb_item_timelines'

    matchup_id = Column(Integer, ForeignKey(Matchup.id), index=True,
                        primary_key=True)
    item_timeline = Column(ARRAY(Integer))

    def __init__(self, data):
        self.matchup_id = data['matchup_id']
        self.item_timeline = data['item_timeline']


class SpellTimeLine(SerializedMixin, Base):

    __tablename__ = 'tb_spell_timelines'

    matchup_id = Column(Integer, ForeignKey(Matchup.id), index=True,
                        primary_key=True)
    spell_timeline = Column(ARRAY(Integer))

    def __init__(self, data):
        self.matchup_id = data['matchup_id']
        self.spell_timeline = data['spell_timeline']


class MatchupAverages(SerializedMixin, Base):

    __tablename__ = 'tb_matchup_averages'

    champion = Column(Integer, ForeignKey(Champion.id),
                      primary_key=True, index=True)
    enemy = Column(Integer, ForeignKey(Champion.id),
                   primary_key=True, index=True)
    patch_version = Column(Text, index=True, primary_key=True)

    kills = Column(Float)
    deaths = Column(Float)
    assists = Column(Float)
    creep_score = Column(Float)
    damage_dealt = Column(Float)

    duration = Column(Float)
    wins = Column(Integer)
    total_games = Column(Integer)

    item_timeline = Column(ARRAY(Integer))
    spell_timeline = Column(ARRAY(Integer))

    masteries = Column(ARRAY(Text))
    runes = Column(ARRAY(Text))
    summoners = Column(Text)


    __table_args__ = (UniqueConstraint('champion', 'enemy', 'patch_version',
                      name='matchup_uniq_id'),)

    @hybrid_property
    def win_rate(self):
        return float(self.wins / self.total_games)

    @hybrid_property
    def kda_str(self):
        return '%.2f{0}/%.2f{1}/%.2f{2}'.format(self.kills,
                                                self.deaths, self.assists)

    def __init__(self, data):
        self.champion = data['champion']
        self.enemy = data['enemy']

        self.kills = data['kills']
        self.deaths = data['deaths']
        self.assists = data['assists']
        self.creep_score = data['creep_score']
        self.damage_dealt = data['damage_dealt']

        self.duration = data['duration']
        self.wins = data['wins']
        self.total_games = data['total_games']

        self.item_timeline = data['item_timeline']
        self.spell_timeline = data['spell_timeline']

        self.masteries = data['masteries']
        self.runes = data['runes']
        self.summoners = data['summoners']

        self.patch_version = data['patch_version']
