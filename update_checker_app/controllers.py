import httplib

from flask import Blueprint, Response, abort, jsonify, request
from sqlalchemy import desc

from .helpers import (get_current_version, normalize, record_check,
                      standard_release)
from .models import Installation, Package, db


ALLOWED_PACKAGES = {'datacleaner', 'hackday_bot', 'praw', 'prawtools',
                    'redditanalysis', 'statsbot', 'topraw4', 'tpot',
                    'xrff2csv'}
ALLOWED_ORIGINS = {'http://bboe.github.io', 'http://localhost:8080'}

LIMIT = db.text('now() - interval \'1 day\'')
INSTALLATION_FILTER = db.and_(Installation.created_at > LIMIT,
                              Installation.package_id == Package.id)

INSTALLATION_QUERY_TITLES = ['id', 'package', 'version', 'unique', 'count']

blueprint = Blueprint('main', __name__)


@blueprint.route('/check', methods=['PUT'])
def check():
    if 'python-requests' not in request.headers.get('User-Agent', ''):
        abort(httplib.FORBIDDEN)
    required = set(('package_name', 'package_version', 'platform',
                   'python_version'))

    if not request.json or not required.issubset(request.json):
        abort(httplib.BAD_REQUEST)

    package_name = normalize(request.json['package_name'].rsplit('.', 1)[-1])
    if package_name not in ALLOWED_PACKAGES:
        abort(httplib.UNPROCESSABLE_ENTITY)

    package_version = request.json['package_version'].strip()
    # Many many requests come in with '' as the platform.
    platform = normalize(request.json['platform'])
    python_version = normalize(request.json['python_version'])
    if not (package_version and platform and python_version):
        abort(httplib.BAD_REQUEST)

    record_check(package_name, package_version, platform, python_version,
                 request.remote_addr)
    return jsonify(get_current_version(package_name,
                                       not standard_release(package_version)))


@blueprint.route('/')
def home():
    return ('', httplib.NO_CONTENT)


@blueprint.route('/packages')
def packages():
    query = (db.session.query(db.func.max(Package.id),
                              db.func.max(Package.package_name),
                              db.func.max(Package.package_version),
                              db.func.count(Installation.id),
                              db.func.sum(Installation.count))
             .filter(INSTALLATION_FILTER)
             .group_by(Installation.package_id)
             .order_by(desc(db.func.count(Installation.id))))

    results = []
    for row in query.all():
        results.append(dict(zip(INSTALLATION_QUERY_TITLES, row)))
    response = jsonify(results)
    origin = request.headers.get('Origin', '')
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
    return response
