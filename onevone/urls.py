from onevone.app import app
from onevone.views import *
from onevone.views import ErrorViews


# Static Data API endpoints
def register_api(view, endpoint, url, pk='id', pk_type='int'):
    url = '/api/v0' + url
    view_func = view.as_view(endpoint)
    app.add_url_rule(
        url, defaults={pk: None}, view_func=view_func, methods=['GET'])
    if pk_type is 'str':
        app.add_url_rule(
            '%s<%s>' % (url, pk), view_func=view_func, methods=['GET'])
    else:
        app.add_url_rule(
            '%s<%s:%s>' % (url, pk_type, pk), view_func=view_func,
            methods=['GET'])

register_api(
    ChampionAPI, 'champion_api', '/champions/', pk='name', pk_type='str')
register_api(MasteryAPI, 'mastery_api', '/masteries/', pk='id', pk_type='int')
register_api(RunesAPI, 'rune_api', '/runes/', pk='id', pk_type='int')
register_api(ItemsAPI, 'items_api', '/items/', pk='id', pk_type='int')
register_api(SummonerSpellAPI,
             'summoners_api', '/summoners/', pk='id', pk_type='int')
app.add_url_rule('/api/v0/matchup/<int:champion>/<int:enemy>',
                 view_func=MatchupAPI.as_view('matchup_api'), methods=['GET'])

# Generic routes

app.add_url_rule('/', view_func=Index.as_view('index'), methods=['GET'])
app.add_url_rule('/about', view_func=About.as_view('about'), methods=['GET'])
app.add_url_rule('/contact', view_func=Contact.as_view('contact'),
                 methods=['GET'])
app.add_url_rule(
    '/matchup/<champion>/<enemy>', view_func=MatchupView.as_view('matchup'),
    methods=['GET'])

app.register_error_handler(404, ErrorViews.not_found)
