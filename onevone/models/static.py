from onevone.models.base import SerializedMixin
from onevone.db_manager import Base

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import Text
from sqlalchemy import ARRAY
from sqlalchemy.ext.hybrid import hybrid_property

class VersionedMixin(object):
    
    patch_version = Column(String(10))

class Champion(VersionedMixin, SerializedMixin, Base):

    __tablename__ = 'tb_champions'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), index=True)
    tags = Column(Text, nullable=True, index=True)
    title = Column(String(100))
    image_blob = Column(Text)
    splash_blob = Column(Text)

class Item(VersionedMixin, SerializedMixin, Base):

    __tablename__ = 'tb_items'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), index=True)
    plaintext = Column(Text)
    description = Column(Text)
    image_blob = Column(String(100))

class Mastery(VersionedMixin, SerializedMixin, Base):

    __tablename__ = 'tb_masteries'

    id = Column(Integer, primary_key=True)
    name = Column(Text, index=True)
    tree = Column(String(10), nullable=True, index=True)
    description = Column(ARRAY(Text))
    image_blob = Column(String(100))


class Rune(VersionedMixin, SerializedMixin, Base):

    __tablename__ = 'tb_runes'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), index=True)
    rtype = Column(String(10), nullable=True, index=True)
    tier = Column(Integer, index=True)
    description = Column(Text)
    image_blob = Column(String(100))

    def __init__(self, **kwargs):
        super(Rune, self).__init__(**kwargs)
        rune_type_mapping = {
            'black': 'quint',
            'red': 'mark',
            'yellow': 'seal',
            'blue': 'glyph'
        }
        rune_type = kwargs.get('rtype')
        self.rtype = rune_type_mapping[rune_type]

class SummonerSpell(VersionedMixin, SerializedMixin, Base):

    __tablename__ = 'tb_summoners'

    id = Column(Integer, primary_key=True)
    name = Column(String(20), index=True)
    description = Column(String)
    image_blob = Column(String(100))
