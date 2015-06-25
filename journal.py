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
from pyramid.httpexceptions import HTTPFound
from sqlalchemy.exc import DBAPIError
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from cryptacular.bcrypt import BCRYPTPasswordManager
from pyramid.security import remember, forget

HERE = os.path.dirname(os.path.abspath(__file__))
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
    Entry.write(title=title, text=text)
    return HTTPFound(request.route_url('home'))

@view_config(context=DBAPIError)
def db_exception(context, request):
    from pyramid.response import Response
    response = Response(context.message)
    response.status_int = 500
    return response

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
    config.add_route('other', '/ayylmao/{special_val}')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.scan()
    app = config.make_wsgi_app()
    return app


if __name__ == '__main__':
    app = main()
    port = os.environ.get('PORT', 5000)
    serve(app, host='0.0.0.0', port=port)
