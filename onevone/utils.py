from onevone.db_manager import DBManager
from onevone.models import *
from onevone import errors

from rest.restclient import RESTClient, ForbiddenException, NotFound

from collections import defaultdict
import json
import os
import sys
import requests
import re
import time
from datetime import datetime
from onevone import log
import redis
from sqlalchemy.orm import load_only
from sqlalchemy import exists
from sqlalchemy.exc import IntegrityError

cache = redis.from_url('redis://localhost:6379/0')


class cached(object):

    def __init__(self, timeout=-1, key_format='key'):
        self.timeout = timeout
        if not isinstance(key_format, str):
            raise
        self.key_format = key_format

    def __call__(self, f):
        def decorator(*args, **kwargs):
            cache_key = self.key_format.format(*args, **kwargs)
            ret = cache.get(cache_key)
            if ret is None:
                ret = f(*args, **kwargs)
                if ret is not None:
                    cache.set(cache_key, json.dumps(ret))
                    if self.timeout > 0:
                        cache.expire(cache_key, self.timeout)
                return ret
            return json.loads(ret.decode('utf-8'))
        return decorator

DBManager.init(os.environ['ONEVONE_PRODUCTION_DB'])
RIOT_GLOBAL_API = 'https://global.api.pvp.net/api/lol'
RIOT_API_KEY = os.environ['RIOT_API_KEY']
api_versions = {
    'static': 'v1.2',
    'matchlist': 'v2.2',
    'league': 'v2.5',
    'match': 'v2.2',
}

xy_version_regex = r'^((?:\d+\.*){2})((?:\.\d*)*)$'
xyz_version_regex = r'^((?:\d+\.*){3})((?:\.\d*)*)$'
static_url = '{0}/static-data/eune/{1}'.format(RIOT_GLOBAL_API,
                                               api_versions['static'])
riot_static_api = RESTClient(base_url=static_url, log=log)
riot_api = RESTClient(log=log)


class StaticDataContext(object):

    @classmethod
    def populate_static_data(cls, patch_versions=None):

        if patch_versions is None:
            patch_versions = cls.get_api_version()['versions'][:5]

        patch_versions.reverse()
        for patch_version in patch_versions:
            patch_version = re.sub(xyz_version_regex, r'\1',
                                   patch_version)
            cls.populate_champions(patch_version)
            cls.populate_items(patch_version)
            cls.populate_masteries(patch_version)
            cls.populate_runes(patch_version)
            cls.populate_summoners(patch_version)
            cache.flushall()

    @staticmethod
    def populate_static_table(endpoint='', model=None, payload={}, version=None):
        entity_name = model.__name__.lower()
        log.debug('Populating {0} table'.format(model.__tablename__))
        try:
            results = riot_static_api.get(endpoint=endpoint, payload=payload)
        except ForbiddenException:
            return
        results_length = len(results['data'].keys())
        log.info('Fetched {0} {1}s'.format(results_length, entity_name))
        with DBManager.create_session_scope() as session:
            status_cnt = 0
            for entity_data in results['data'].values():
                status_cnt += 1
                print(
                    '[*] Status {0}/{1}'.format(status_cnt, results_length),
                    end='\r')
                _process_ctx = getattr(
                    DataProcessContext,
                    'process_{0}_data'.format(entity_name)
                )
                if _process_ctx is None:
                    raise Exception(
                        'No data process function for model {0} was '
                        'defined'.format(entity_name))
                _processed_data = _process_ctx(entity_data)
                session.merge(model(**dict(_processed_data, patch_version=version)))
        log.debug('Done!')

    @classmethod
    def populate_champions(cls, version):
        payload = {
            'locale': 'en_US',
            'api_key': RIOT_API_KEY,
            'champData': 'image,tags',
            'version': version,
        }
        endpoint = '/champion'
        cls.populate_static_table(
            endpoint=endpoint, model=Champion, payload=payload, version=version)

    @classmethod
    def populate_items(cls, version):
        payload = {
            'itemListData': 'image',
            'api_key': RIOT_API_KEY,
            'version': version,
        }
        endpoint = '/item'
        cls.populate_static_table(endpoint=endpoint, model=Item,
                                  payload=payload, version=version)

    @classmethod
    def populate_masteries(cls, version):

        payload = {
            'masteryListData': 'all',
            'api_key': RIOT_API_KEY,
            'version': version,
        }
        endpoint = '/mastery'
        cls.populate_static_table(
            endpoint=endpoint, model=Mastery, payload=payload, version=version)

    @classmethod
    def populate_summoners(cls, version):
        payload = {
            'spellData': 'image',
            'api_key': RIOT_API_KEY,
        }
        endpoint = '/summoner-spell'
        cls.populate_static_table(
            endpoint=endpoint, model=SummonerSpell, payload=payload, version=version)

    @classmethod
    def populate_runes(cls, version):
        payload = {
            'runeListData': 'image',
            'api_key': RIOT_API_KEY,
            'version': version,
        }
        endpoint = '/rune'
        cls.populate_static_table(endpoint=endpoint, model=Rune,
                                  payload=payload, version=version)

    @staticmethod
    @cached(timeout=3600*24, key_format='api_version')
    def get_api_version():
        payload = {
            'api_key': RIOT_API_KEY
        }
        versions = riot_static_api.get(endpoint='/versions', payload=payload)
        return {
            'versions': versions
        }

    @staticmethod
    @cached(key_format='{0}:id', timeout=3600)
    def get_objects_id_dict(model):
        with DBManager.create_session_scope(expire_on_commit=False) as session:
            ret = {str(o.id): o.serialize() for o in
                   session.query(model).all()}
            return ret
        return None

    @staticmethod
    @cached(key_format='{0}:name:{1}', timeout=3600)
    def get_object_from_name(model, name):
        with DBManager.create_session_scope(expire_on_commit=False) as session:
            ret = session.query(model).filter_by(name=name).first()
            if ret is not None:
                ret = ret.serialize()
            return ret
        return None

    class MasteryTree(object):

        __instance = None

        def __new__(cls):
            if cls.__instance is None:
                cls.__instance = object.__new__(cls)
                payload = {
                    'masteryListData': 'all',
                    'api_key': RIOT_API_KEY
                }
                endpoint = '/mastery'
                data = riot_static_api.get(endpoint=endpoint, payload=payload)
                cls.__instance.mastery_tree = data['tree']
                cls.__instance.masteries = StaticDataContext.get_objects_id_dict(Mastery)
            return cls.__instance

    @classmethod
    def generate_mastery_tree(cls, masteries_list):
        ret = []
        masteries_list = {m: int(p) for m, p in map(lambda x: x.split(':'),
                                                    masteries_list)}
        mt = cls.MasteryTree()
        branch_order = ['Ferocity', 'Cunning', 'Resolve']
        for branch in branch_order:
            branch_data = []
            for level in mt.mastery_tree[branch]:
                level_masteries = []
                for mastery in level['masteryTreeItems']:
                    if mastery is None:
                        level_masteries.append(None)
                    else:
                        mid = str(mastery["masteryId"])
                        if masteries_list.get(mid) is None:
                            points = 0
                        else:
                            points = masteries_list[mid]
                        mastery_dict = mt.masteries[mid]
                        mastery_dict['points'] = points
                        level_masteries.append(mastery_dict)
                branch_data.append(level_masteries)
            ret.append({'name': branch, 'data': branch_data})
        return ret

    @classmethod
    def generate_static_images(cls):
        IMAGES_PER_LINE = 10
        IMAGE_SIZE = 64
        data = {}
        with DBManager.create_session_scope() as session:
            version = cls.get_api_version()['versions'][0]
            ddragon_api = RESTClient(base_url='http://ddragon.'
                                              'leagueoflegends.com/cdn',
                                     log=log)

            from PIL import Image
            import io
            models = [SummonerSpell, Champion, Mastery, Item, Rune]
            for model in models:
                if model == SummonerSpell:
                    model_name = 'spell'
                else:
                    model_name = model.__name__.lower()

                query_set = session.query(model)\
                                   .order_by('id')\
                                   .all()
                CONCAT_WIDTH = IMAGES_PER_LINE * IMAGE_SIZE
                CONCAT_HEIGHT = (int(len(query_set) / IMAGES_PER_LINE) + 1) * IMAGE_SIZE
                sprite_img = Image.new('RGB', (CONCAT_WIDTH, CONCAT_HEIGHT))
                data[model_name] = []
                i, j = 0, 0
                for entry in query_set:
                    data[model_name].append({
                        'id': entry.id,
                        'xoffset_small': -j*32,
                        'yoffset_small': -i*32,
                        'xoffset_big': -j*64,
                        'yoffset_big': -i*64,
                    })
                    endpoint = '/{0}/img/{1}/{2}'.format(entry.patch_version, 
                                                         model_name, entry.image_blob)
                    try:
                        image_stream = ddragon_api.get(endpoint=endpoint,
                                                       response_type='byte-stream')
                    except Exception:
                        continue
                    image = Image.open(image_stream).resize((IMAGE_SIZE, IMAGE_SIZE))
                    sprite_img.paste(image, (j*IMAGE_SIZE, i*IMAGE_SIZE))
                    j += 1
                    if j == IMAGES_PER_LINE:
                        i += 1
                        j = 0
                    splash_blob = getattr(entry, 'splash_blob', None)
                    if splash_blob is not None:
                        endpoint = '/{0}/loading/{1}'.format(model_name, splash_blob)
                        try:
                            image_stream = ddragon_api.get(url='http://ddragon.leagueoflegends.com/cdn/img'.format(model_name, splash_blob),
                                                           endpoint=endpoint,
                                                           response_type='byte-stream')
                        except Exception:
                            continue
                        image = Image.open(image_stream)
                        image.save('./onevone/static/images/'+ model_name + '-splash/' + splash_blob)

                sprite_img.save('./onevone/static/images/'+ model_name + '_sprite.png')
                sprite_img_s = sprite_img.copy().resize((int(CONCAT_WIDTH*0.5), int(CONCAT_HEIGHT*0.5)))
                sprite_img_s.save('./onevone/static/images/'+ model_name + '_sprite.small.png')
                sprite_grey = sprite_img.copy().convert('L')
                sprite_grey.save('./onevone/static/images/'+ model_name + '_sprite_grey.png')

        from jinja2 import Environment
        with open('./onevone/static/css/static_data.template.css', 'r') as t,\
                open('./onevone/static/css/static_data.css', 'w+') as f:
            template = t.read()
            f.write(Environment(trim_blocks=True, lstrip_blocks=True).
                    from_string(template).render(data=data))


class DataProcessContext(object):

    def process_champion_data(data):
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "title": data.get("title"),
            "image_blob": data.get("image").get("full"),
            "tags": ",".join(data.get("tags")),
            "splash_blob": data.get("image")
            .get("full").split('.png')[0] + '_0.jpg'
        }

    def process_item_data(data):
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "plaintext": data.get("plaintext"),
            "description": data.get("description"),
            "image_blob": data.get("image").get("full"),
        }

    def process_mastery_data(data):
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "tree": data.get("masteryTree"),
            "description": data.get("sanitizedDescription"),
            "image_blob": data.get("image").get("full"),
        }

    def process_rune_data(data):
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "description": data.get("description"),
            "image_blob": data.get("image").get("full"),
            "tier": data.get("rune").get("tier"),
            "rtype": data.get("rune").get("type"),
        }

    def process_summonerspell_data(data):
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "description": data.get("description"),
            "image_blob": data.get("image").get("full"),
        }


class MatchContext(object):

    @staticmethod
    def populate_players(region='EUNE', league='challenger', player_limit=50):
        # Get a list with the top 50 challenger players (if any)
        log.debug(
            'Fetching top {0} players from {1} in region '
            '{2}'.format(player_limit, league, region))
        payload = {
            'api_key': RIOT_API_KEY,
            'type': 'RANKED_SOLO_5x5'
        }
        url = 'https://{0}.api.pvp.net/api/lol/{0}'.format(region.lower())
        endpoint = '/{0}/league/{1}'.format(api_versions['league'], league)
        try:
            ladder = riot_api.get(url=url, endpoint=endpoint, payload=payload)
        except ForbiddenException:
            return

        if len(ladder.keys()) == 0:
            return

        players = [player for _, player in sorted(
            [(player['leaguePoints'], player) for player in ladder['entries']],
            reverse=True, key=lambda x: x[0])[:player_limit]]

        results_length = len(players)

        log.debug('[+] Fetched {0} players'.format(results_length))
        with DBManager.create_session_scope() as session:
            for player in players:
                player_data = {
                    'id': player.get('playerOrTeamId'),
                    'region': region.lower(),
                    'tier': league.lower(),
                    'name': player.get('playerOrTeamName')
                }
                session.merge(ProPlayer(player_data))
        log.debug('[+] Done!')

    @staticmethod
    def populate_queued_matches(limit=50, region='EUNE'):
        matches = {}
        log.debug(
            'Collecting match information for each player. This might '
            'take a while...')
        with DBManager.create_session_scope(expire_on_commit=False) as session:
            payload = {
                'api_key': RIOT_API_KEY,
                'rankedQueues': 'TEAM_BUILDER_DRAFT_RANKED_5x5,RANKED_SOLO_5x5',
                'seasons': 'SEASON2016,PRESEASON2016,PRESEASON2017',
                'beginIndex': 0,
                'endIndex': limit
            }

            latest_game = session.query(QueuedMatch).filter_by(
                region=region).order_by(
                QueuedMatch.match_timestamp.desc()).first()
            
            if latest_game is not None:
                payload['beginTime'] = latest_game.match_timestamp

            players = session.query(ProPlayer).all()
            url = 'https://{0}.api.pvp.net/api/lol/{0}'.format(region.lower())
            for player in players:
                endpoint = '/{0}/matchlist/by-summoner/{1}'\
                           .format(api_versions['matchlist'], player.id)
                try:
                    result = riot_api.get(url=url,
                                          endpoint=endpoint, payload=payload)
                except ForbiddenException:
                    continue
                except NotFound:
                    continue
                for match in result.get("matches", []):
                    match_data = {
                        'id': match.get('matchId'),
                        'region': match.get('region'),
                        'match_timestamp': match.get('timestamp'),
                        'added_at': datetime.now()
                    }
                    session.merge(QueuedMatch(match_data))
                    session.commit()

    @classmethod
    def populate_matchups(cls, limit=50, region='EUNE'):
        session = DBManager.create_session(expire_on_commit=False)
        matches = session.query(QueuedMatch).filter_by(region=region).filter(
            ~exists().where(QueuedMatch.id == CheckedMatch.id))\
            .limit(limit).all()
        for match in matches:
            payload = {
                'api_key': RIOT_API_KEY,
                'includeTimeline': 'true',
            }
            log.debug('Fetching info for match {0}'.format(match.id))
            url = 'https://{0}.api.pvp.net/api/lol/{0}'.format(region.lower())
            endpoint = '/{0}/match/{1}'.format(api_versions['match'], match.id)
            try:
                result = riot_api.get(url=url, endpoint=endpoint, payload=payload)
            except ForbiddenException:
                continue
            except NotFound:
                continue
            cls.populate_single_matchup(result)
            checked_match = CheckedMatch({
                'id': match.id,
                'region': match.region,
                'checked_at': datetime.now(),
                'match_timestamp': match.match_timestamp
            })
            session.merge(checked_match)
            session.commit()

    @staticmethod
    # TODO: Clean Up this ugliness
    def populate_single_matchup(data):

        try:
            frames = data['timeline']['frames']
        except KeyError:
            log.error('No timeline data')
            return

        item_timelines = defaultdict(list)
        spell_timelines = defaultdict(list)
        
        for frame in frames:
            for ev in frame.get('events', []):
                if ev['eventType'] == 'ITEM_PURCHASED':
                    item_timelines[ev['participantId']].append(ev['itemId'])
                elif ev['eventType'] == 'SKILL_LEVEL_UP':
                    spell_timelines[ev['participantId']].append(ev['skillSlot'])

        if data["teams"][0]["winner"] is True:
            winning_team = data["teams"][0]["teamId"]
        else:
            winning_team = data["teams"][1]["teamId"]

        results = {}
        # results = {
        #     'JUNGLE': {
        #         'vs': [{participant1}, {participant2}].
        #         'won': 202 -> champion id
        #     },
        #     ...
        # }
        for participant in data.get('participants', []):
            lane_role = '{0}:{1}'.format(
                participant['timeline']['lane'],
                participant['timeline']['role'])
            if results.get(lane_role) is None:
                results[lane_role] = {
                    'vs': [],
                    'won': None
                }
            results[lane_role]['vs'].append(participant)
            if participant['teamId'] == winning_team:
                results[lane_role]['won'] = participant['championId']

        with DBManager.create_session_scope(expire_on_commit=False) as session:
            for lane_role, result in results.items():

                # Sometimes there are no matchups
                if len(result['vs']) != 2:
                    continue

                for idx, participant in enumerate(result['vs']):
                    pid = participant['participantId']
                    enemy = result['vs'][(idx + 1) % 2]
                    try:
                        masteries = [
                            '{0}:{1}'.format(m['masteryId'], m['rank'])
                            for m in participant['masteries']
                        ]

                        runes = [
                            '{0}:{1}'.format(r['runeId'], r['rank'])
                            for r in participant['runes']
                        ]

                        summoners = '{0},{1}'.format(
                            participant['spell1Id'],
                            participant['spell2Id']
                        )

                        stats = participant.get('stats')
    
                        matchup_data = {
                            'champion': participant['championId'],
                            'enemy': enemy['championId'],
                            'won': participant['championId'] == result['won'],
                            'kills': stats.get('kills'),
                            'deaths': stats.get('deaths'),
                            'assists': stats.get('assists'),
                            'creep_score': stats.get('minionsKilled'),
                            'damage_dealt':
                                stats.get('totalDamageDealtToChampions'),
                            'duration': data.get('matchDuration'),
                            'patch_version':
                                '.'.join(data.get('matchVersion').
                                         split('.')[:2]),
                            'masteries': masteries,
                            'runes': runes,
                            'summoners': summoners,
                        }
                    except KeyError:
                        continue

                    matchup = Matchup(matchup_data)
                    session.add(matchup)
                    session.flush()
                    session.refresh(matchup)
                    item_timeline_data = {
                        'matchup_id': matchup.id,
                        'item_timeline': item_timelines[pid]
                    }
                    item_timeline = ItemTimeline(item_timeline_data)
                    spell_timeline_data = {
                        'matchup_id': matchup.id,
                        'spell_timeline': spell_timelines[pid]
                    }
                    spell_timeline = SpellTimeLine(spell_timeline_data)
                    session.add(item_timeline)
                    session.add(spell_timeline)
                    session.commit()

    @classmethod
    def populate_averages(cls):
        with DBManager.create_session_scope(expire_on_commit=False) as session:
            champions = [c.id for c in session.query(Champion).options(
                load_only('id')).order_by('id').all()]
            total_champs = len(champions)
            versions = StaticDataContext.get_api_version()['versions'][:2]
            for version in versions:
                # Keep only the 2 majon numbers of the patch version
                patch_version = re.sub(r'^((?:\d+\.*){2})((?:\.\d*)*)$', r'\1',
                                       version)
                log.debug('Calculating Averages for patch : {0}'
                          .format(patch_version))
                for i in range(0, total_champs):
                    print('Status {0}/{1}'.format(i, total_champs), end='\r')
                    for j in range(0, total_champs):
                        if i == j:
                            continue
                        idA = champions[i]
                        idB = champions[j]
                        matchups = session.query(Matchup, SpellTimeLine, ItemTimeline)\
                            .join(SpellTimeLine,
                                  (Matchup.id == SpellTimeLine.matchup_id)) \
                            .join(ItemTimeline,
                                  (Matchup.id == ItemTimeline.matchup_id)) \
                            .filter(
                            (Matchup.champion == idA) & (Matchup.enemy == idB) &
                            (Matchup.checked == False) & (Matchup.patch_version == patch_version)
                        ).all()
                        
                        total_games = len(matchups)
                        if total_games == 0:
                            continue
                        
                        matchups, spell_timelines, item_timelines = zip(*matchups)

                        kills = 0
                        deaths = 0
                        assists = 0
                        damage_dealt = 0
                        wins = 0
                        creep_score = 0
                        duration = 0
                        for matchup in matchups:
                            if matchup.won:
                                wins += 1
                            kills += matchup.kills
                            deaths += matchup.deaths
                            assists += matchup.assists
                            damage_dealt += matchup.damage_dealt
                            creep_score += matchup.creep_score
                            duration += matchup.duration

                        sts = [st.spell_timeline for st in spell_timelines]
                        avg_spells = cls.timelines_average(data=sts)

                        its = [it.item_timeline for it in item_timelines]
                        avg_items = cls.timelines_average(data=its)

                        mus = [(mu.masteries, mu.runes, mu.summoners)
                               for mu in matchups]
                        masteries, runes, summoners = zip(*mus)
                        avg_masteries = cls.timelines_average(masteries)
                        avg_runes = cls.timelines_average(runes)

                        summoners = [sorted(s.split(',')) for s in summoners]
                        avg_summoners = cls.timelines_average(summoners)

                        matchup_avgs = {
                            'champion': idA,
                            'enemy': idB,
                            'total_games': total_games,
                            'kills': float(kills/total_games),
                            'deaths': float(deaths/total_games),
                            'assists': float(assists/total_games),
                            'creep_score': float(creep_score/total_games),
                            'damage_dealt': float(damage_dealt/total_games),
                            'duration': float(duration/total_games),
                            'wins': wins,
                            'item_timeline': avg_items,
                            'spell_timeline': avg_spells,
                            'masteries': avg_masteries,
                            'runes': avg_runes,
                            'summoners': avg_summoners,
                            'patch_version': patch_version
                        }
                        try:
                            matchup_avgs = MatchupAverages(matchup_avgs)
                            session.merge(matchup_avgs)
                            session.commit()
                        except IntegrityError:
                            session.rollback()
                            log.warn('Average already {0}vs{1} patch {2}'
                                     'exists. Updating'.format(
                                        idA, idB, patch_version))
                            prev_matchup = session.query(
                                MatchupAverages).filter_by(
                                champion=idA, enemy=idB,
                                patch_version=patch_version).first()

                            session.merge(matchup_avgs)
                            session.commit()

    @staticmethod
    def timelines_average(data=[]):
        ret = []
        bag = list(filter(lambda x: len(x) > 0, data))
        idx = 0
        data_keys = ({k: None for entry in data for k in entry}).keys()
        while len(bag) > 0:
            freq_table = {k: 0 for k in data_keys}
            for entry in bag:
                val = entry[idx]
                freq_table[val] += 1
            max_s = max(freq_table, key=freq_table.get)
            ret.append(max_s)
            bag = list(filter(lambda x: x[idx] == max_s, bag))
            bag = list(filter(lambda x: len(x) > idx + 1, bag))
            idx += 1
        return ret

    @staticmethod
    def process_matchup(matchup):
        # Process Match Statistics
        # Seconds to h:m:s http://stackoverflow.com/a/775075/2277088
        minutes, seconds = divmod(matchup.duration, 60)
        hours, minutes = divmod(minutes, 60)
        stats = {
            'total_games': matchup.total_games,
            'kills': '%.2f' % matchup.kills,
            'deaths': '%.2f' % matchup.deaths,
            'assists': '%.2f' % matchup.assists,
            'damage_dealt': '%.2f k' % (matchup.damage_dealt*0.001),
            'creep_score': '%.2f' % (60 * matchup.creep_score / matchup.duration),
            'duration': "%d:%02d:%02d" % (hours, minutes, seconds),
            'win_rate': matchup.win_rate * 100
        }

        # Process Masteries
        masteries = StaticDataContext.generate_mastery_tree(matchup.masteries)

        runes_collection = StaticDataContext.get_objects_id_dict(Rune)
        runes = {(r, p) for r, p in map(lambda x: x.split(':'), matchup.runes)}
        runes = [dict(runes_collection[rid], points=p) for rid, p in runes]

        summoners_collection = StaticDataContext.get_objects_id_dict(SummonerSpell)
        summoners = matchup.summoners[1:-1].split(',')
        summoners = [summoners_collection[s] for s in summoners]

        items_collection = StaticDataContext.get_objects_id_dict(Item)
        # We need to make items list RLE
        items = []
        prev = None
        cnt = 0
        ignore_items = ['potion', 'biscuit', 'ward']
        for index, item in enumerate(matchup.item_timeline):
            if prev is None:
                prev = item
                continue
            elif prev == item:
                cnt += 1
            else:
                item_dict = items_collection[str(prev)]
                ignore = False
                for ign in ignore_items:
                    if ign in item_dict['name'].lower():
                        ignore = True
                if not ignore or index < 5:
                    items.append((item_dict, cnt))
                cnt = 0
            prev = item

        spell_mapping = ['Q', 'W', 'E', 'R']

        spell_tree = defaultdict(list)
        for level in range(1, 19):
            for index, spell_name in enumerate(spell_mapping):
                if level >= len(matchup.spell_timeline):
                    spell_tree[spell_name].append(False)
                else:
                    spell = matchup.spell_timeline[level]
                    spell_tree[spell_name].append(index + 1 == spell)

        spell_timeline = []
        for spell in spell_mapping:
            spell_timeline.append({
                'spell_name': spell,
                'spell_row': spell_tree[spell]
            })

        return {
            'stats': stats,
            'mastery_tree': masteries,
            'runes': runes,
            'summoners': summoners,
            'items': items,
            'spell_timeline': spell_timeline,
            'patch_version': matchup.patch_version
        }

    @staticmethod
    @cached(key_format='matchup:{0}:{1}:{2}', timeout=60*60*24)
    def get_matchup(champion_name, enemy_name, patch_version):
        champion = StaticDataContext.get_object_from_name(Champion, champion_name)
        enemy = StaticDataContext.get_object_from_name(Champion, enemy_name)
        versions = StaticDataContext.get_api_version()['versions'][:5]
        versions = list(map(lambda x: re.sub(xy_version_regex, r"\1", x),
                            versions))
        if champion is None or enemy is None:
            raise errors.BadRequest('Both champions must be provided')
        with DBManager.create_session_scope(expire_on_commit=False) as session:
            matchup_avg = session.query(MatchupAverages).filter(
                (MatchupAverages.champion == champion['id']) &
                (MatchupAverages.enemy == enemy['id'])
            )
            if patch_version is None:
                matchup_avg = matchup_avg.filter(
                    MatchupAverages.patch_version == versions[0])
            else:
                matchup_avg = matchup_avg.filter(
                    MatchupAverages.patch_version == patch_version)
            matchup_avg = matchup_avg.first()
            if matchup_avg is None:
                raise errors.MatchupNotFound('Matchup not Found')
            matchup_avg = matchup_avg
            return dict(MatchContext.process_matchup(matchup_avg),
                        champion=champion, enemy=enemy, versions=versions)
