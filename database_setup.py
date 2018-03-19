import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key = True)
    name = Column(String(80), nullable = False)
    email = Column(String(80), nullable = False)
    picture = Column(String(250))

class Theme(Base):
    __tablename__ = 'theme'

    name = Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):

        return {
            'name': self.name,
            'id': self.id,
        }

class Painting(Base):
    __tablename__ = 'painting'

    name = Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)
    year = Column(String(4))
    description = Column(String(250))
    #imageurl = Column(String(250))
    theme_id = Column(Integer, ForeignKey('theme.id'))
    theme = relationship(Theme)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)


    # We added this serialize function to be able to send JSON objects in a
# serializable format
    @property
    def serialize(self):

        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'year': self.year,
        }

engine = create_engine('sqlite:///artportfolio.db')
Base.metadata.create_all(engine)
