# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import datetime
import json

from pyramid.config import Configurator
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember, forget

from cryptacular.bcrypt import BCRYPTPasswordManager
from markdown import markdown
from waitress import serve

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension
from sqlalchemy.exc import DBAPIError

HERE = os.path.dirname(os.path.abspath(__file__))
DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://wesleywooten@localhost:5432/learning-journal'
)


class Entry(Base):
    __tablename__ = 'entries'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.Unicode(127), nullable=False, unique=True)
    text = sa.Column(sa.Unicode(), nullable=False)
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow)

    @classmethod
    def get_entry_by_id(cls, entry_id, session=None):
        if session is None:
            session = DBSession
        return session.query(cls).filter(cls.id == entry_id).one()

    @classmethod
    def write(cls, title=None, text=None, session=None):
        if title == "":
            raise ValueError()
        if not session:
            session = DBSession
        instance = cls(title=title, text=text)
        session.add(instance)
        session.flush()
        return instance

    @classmethod
    def all(cls, session=None):
        if session is None:
            session = DBSession
        return session.query(cls).order_by(cls.created.desc()).all()

    @classmethod
    def update(cls, entry_id, title, text, session=None):
        if session is None:
            session = DBSession
        entry = Entry.get_entry_by_id(entry_id, session=session)
        entry.text = text
        entry.title = title
        return entry


@view_config(route_name='login', renderer="templates/login.jinja2")
def login(request):
    """authenticate a user by username/password"""
    username = request.params.get('username', '')
    error = ''
    if request.method == 'POST':
        error = "Login Failed"
        authenticated = False
        try:
            authenticated = do_login(request)
        except ValueError as e:
            error = str(e)

        if authenticated:
            headers = remember(request, username)
            return HTTPFound(request.route_url('home'), headers=headers)

    return {'error': error, 'username': username}


@view_config(route_name='logout')
def logout(request):
    headers = forget(request)
    return HTTPFound(request.route_url('home'), headers=headers)


@view_config(route_name='add', request_method='POST')
def add_entry(request):
    title = request.params.get('title')
    text = request.params.get('text')
    entry = Entry.write(title=title, text=text)
    return HTTPFound(request.route_url('detail', entryID=entry.id))


@view_config(context=DBAPIError)
def db_exception(context, request):
    from pyramid.response import Response
    response = Response(context.message)
    response.status_int = 500
    return response


def init_db():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)


@view_config(route_name='home', renderer='templates/index.jinja2')
def home(request):
    return {"entries": Entry.all()}


@view_config(route_name="detail", renderer="templates/detail.jinja2")
def detail(request):
    entry = Entry.get_entry_by_id(request.matchdict["entryID"])
    if 'HTTP_X_REQUESTED_WITH' in request.environ:
        return Response(body=json.dumps({
                                        "title": entry.title,
                                        "text": markdown(
                                            entry.text,
                                            extensions=['codehilite',
                                                        'fenced_code'])
                                        }), content_type=b'application/json')
    return {
        "entry": {
            "id": entry.id,
            "text": entry.text,
            "created": entry.created,
            "title": entry.title
        },
        "markdown_text": markdown(entry.text, extensions=['codehilite',
                                                          'fenced_code'])
    }


@view_config(route_name="edit", renderer="templates/edit.jinja2")
def edit(request):
    entry = Entry.get_entry_by_id(request.matchdict["entryID"])
    if 'HTTP_X_REQUESTED_WITH' in request.environ:
        return Response(body=json.dumps({
                                        "title": entry.title,
                                        "text": entry.text
                                        }), content_type=b'application/json')
    return {"entry": {
            "id": entry.id,
            "text": entry.text,
            "created": entry.created,
            "title": entry.title}
            }


@view_config(route_name="edit_entry", request_method='POST')
def edit_entry(request):
    entry = Entry.get_entry_by_id(request.matchdict["entryID"])
    entry.update(entry.id, request.params.get("title"),
                 request.params.get("text"))
    return HTTPFound(request.route_url('detail', entryID=entry.id))


@view_config(route_name="new", renderer="templates/new.jinja2")
def new(request):
    return {}


def do_login(request):
    username = request.params.get('username', None)
    password = request.params.get('password', None)
    if not (username and password):
        raise ValueError('both username and password are required')

    settings = request.registry.settings
    manager = BCRYPTPasswordManager()
    if username == settings.get('auth.username', ''):
        hashed = settings.get('auth.password', '')
        return manager.check(hashed, password)


def main():
    """Create a configured wsgi app"""
    settings = {}
    debug = os.environ.get('DEBUG', True)
    settings['reload_all'] = debug
    settings['debug_all'] = debug
    settings['auth.username'] = os.environ.get('AUTH_USERNAME', 'admin')
    manager = BCRYPTPasswordManager()
    settings['auth.password'] = os.environ.get(
        'AUTH_PASSWORD', manager.encode('secret')
    )
    if not os.environ.get('TESTING', False):
        engine = sa.create_engine(DATABASE_URL)
        DBSession.configure(bind=engine)
    auth_secret = os.environ.get('JOURNAL_AUTH_SECRET', 'itsaseekrit')
    # and add a new value to the constructor for our Configurator:
    config = Configurator(
        settings=settings,
        authentication_policy=AuthTktAuthenticationPolicy(
            secret=auth_secret,
            hashalg='sha512'
        ),
        authorization_policy=ACLAuthorizationPolicy(),
    )
    config.include('pyramid_tm')
    config.include('pyramid_jinja2')
    config.add_static_view('static', os.path.join(HERE, 'static'))
    config.add_route('home', '/')
    config.add_route('add', '/add')
    config.add_route('new', '/new')
    config.add_route('edit_entry', '/edit_entry/{entryID}')
    config.add_route('detail', '/detail/{entryID}')
    config.add_route('edit', '/edit/{entryID}')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.scan()
    app = config.make_wsgi_app()
    return app


if __name__ == '__main__':
    app = main()
    port = os.environ.get('PORT', 5000)
    serve(app, host='0.0.0.0', port=port)
