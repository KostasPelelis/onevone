from onevone.app import app
from onevone.models import *
from onevone.db_manager import DBManager
from onevone.utils import StaticDataContext, MatchContext
from onevone import errors

from functools import wraps
import json
import redis

from flask import request, Response, jsonify, render_template, abort
from flask.views import MethodView, View
from sqlalchemy.orm import load_only
import re

from onevone import log

__all__ = [
    'ChampionAPI',
    'MasteryAPI',
    'RunesAPI',
    'ItemsAPI',
    'MatchupAPI',
    'SummonerSpellAPI',
    'Index',
    'About',
    'Contact',
    'MatchupView',
]

view_session = DBManager.create_session(expire_on_commit=False)


def create_error_response(message, error_code):
    data = json.dumps({
        'error': True,
        'message': message
    })
    response = Response(status=error_code,
                        mimetype='application/json')
    response.set_data(data)
    return response


def create_success_response(payload):
    data = json.dumps({
        'data': payload,
    })
    response = Response(status=200,
                        mimetype='application/json')
    response.set_data(data)
    return response


def info_view(available_fields, default='id'):
    def pseudo_wrapper(wrapped_view):
        @wraps(wrapped_view)
        def view_wrapper(*args, **kwargs):
            lookup_table = {k: True for k in available_fields}
            filter_fields = {}
            for field, value in request.args.items():
                if lookup_table[field] is None:
                    return create_error_response('Unkown filter {0}'.format(field), 400)
                else:
                    filter_fields[field] = value
            response = wrapped_view(filter_fields, *args, **kwargs)

            if response is not None:
                if type(response) == list:
                    return create_success_response([item.serialize() for item in response])
                else:
                    return create_success_response(response.serialize())
            else:
                return create_error_response('Not found', 404)
        return view_wrapper
    return pseudo_wrapper


class StaticView(View):

    def get_arguments(self):
        return {}

    def dispatch_request(self):
        if self.template is None:
            abort(404)
        return render_template(self.template, **self.get_arguments())


class VersionedView(StaticView):

    def get_arguments(self):
        version = StaticDataContext.get_api_version()['versions'][0]
        patch_version = re.sub(r'^((?:\d+\.*){2})((?:\.\d*)*)$', r'\1',
                               version)
        return {'latest': patch_version}


class Index(VersionedView):

    template = 'index.html'


class About(VersionedView):

    template = 'about.html'


class Contact(VersionedView):

    template = 'contact.html'


class MatchupView(VersionedView):

    def dispatch_request(self, champion, enemy):

        patch_version = request.args.get('patch_version')
        if patch_version is not None:
            patch_version = re.sub(r'^((?:\d+\.*){2})((?:\.\d*)*)$', r'\1',
                                   patch_version)
        try:
            matchup = MatchContext.get_matchup(champion, enemy, patch_version)
        except errors.BadRequest:
            abort(400)
        except errors.MatchupNotFound:
            abort(404)
        return render_template('matchup.html',
                               **dict(matchup, **self.get_arguments()))


class ErrorViews(object):

    def not_found(exc):
        return render_template('404.html')


class ModelAPI(MethodView):

    name_id_mapping = False
    decorators = [info_view(['id', 'name'])]

    def get(self, filter, *args, **kwargs):
        pk_val = kwargs[self.pk_name]
        query = view_session.query(self.model)

        if pk_val is not None:
            filter[self.pk_name] = pk_val
            result = query.filter_by(**filter).first()
            return result
        elif len(filter.keys()) > 0:
            result = query.filter_by(**filter).first()
            return result
        else:
            result = query.all()
            return result


class ChampionAPI(ModelAPI):

    model = Champion
    pk_name = 'name'
    name_id_mapping = True


class MasteryAPI(ModelAPI):

    model = Mastery
    pk_name = 'id'


class RunesAPI(ModelAPI):

    model = Rune
    pk_name = 'id'


class ItemsAPI(ModelAPI):

    model = Item
    pk_name = 'id'


class SummonerSpellAPI(ModelAPI):

    model = SummonerSpell
    pk_name = 'id'


class MatchupAPI(MethodView):

    def get(self, champion, enemy):
        matchup_avg = None
        if champion is None:
            return create_error_response("Both champions must be supplied", 400)
        if enemy is None:
            matchup_avgs = view_session.query(MatchupAverages).filter(
                ((MatchupAverages.champion == champion) |
                 (MatchupAverages.enemy == champion))
            ).all()
            matchup_avgs = [v.serialize() for v in matchup_avgs]
            return create_success_response(matchup_avg)
        else:
            matchup_avg = view_session.query(MatchupAverages).filter(
                (MatchupAverages.champion == champion) & (
                    MatchupAverages.enemy == enemy)
            ).first()
        if matchup_avg is None:
            return create_error_response('Not found', 404)
        else:
            return create_success_response(matchup_avg.serialize())
