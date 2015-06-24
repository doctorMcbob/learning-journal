# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
from pyramid.config import Configurator
from pyramid.view import view_config
from waitress import serve
import datetime
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension
from pyramid.httpexceptions import HTTPNotFound
#--maybe--
from sqlalchemy.exc import IntegrityError
#---------

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://wesleywooten@localhost:5432/learning-journal'
)


class Entry(Base):
    __tablename__ = 'entries'
    
    id = sa.Column(sa.Integer, primary_key=True)
    title = sa.Column(sa.Unicode(127), nullable=False, unique=True)
    text = sa.Column(sa.Unicode(), nullable=False)
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow)

    @classmethod
    def write(cls, title=None, text=None, session=None):
        if title == "":
            raise ValueError()
        if not session:
            session = DBSession
        instance = cls(title=title, text=text)
        session.add(instance)
        return instance
    
    @classmethod
    def all(cls, session=None):
        if session == None:
            session = DBSession
        return session.query(cls).order_by(cls.created.desc()).all()

def init_db():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)

@view_config(route_name='home', renderer='templates/list.jinja2')
def home(request):
    #import pdb; pdb.set_trace()
    return {"entries":Entry.all()}

@view_config(route_name="other", renderer="string")
def other(request):
    import pdb; pdb.set_trace()
    return request.matchdict

def main():
    """Create a configured wsgi app"""
    settings = {}
    debug = os.environ.get('DEBUG', True)
    settings['reload_all'] = debug
    settings['debug_all'] = debug
    if not os.environ.get('TESTING', False):
        engine = sa.create_engine(DATABASE_URL)
        DBSession.configure(bind=engine)
    # configuration setup
    config = Configurator(
        settings=settings
    )
    config.include('pyramid_tm')
    config.include('pyramid_jinja2')
    config.add_route('home', '/')
    config.add_route('other', '/ayylmao/{special_val}')
    config.scan()
    app = config.make_wsgi_app()
    return app


if __name__ == '__main__':
    app = main()
    port = os.environ.get('PORT', 5000)
    serve(app, host='0.0.0.0', port=port)
