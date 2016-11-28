from os import getenv

from flask import Flask

from .controllers import blueprint
from .helpers import configure_logging
from .models import db

__version__ = '0.13'


def create_app(db_uri='postgresql://@/updatechecker'):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.debug = getenv('DEBUG')
    app.register_blueprint(blueprint)
    db.init_app(app)
    return app


app = create_app()
configure_logging(app)


def main():
    db.create_all(app=app)
    app.run('', 65429, processes=4)
