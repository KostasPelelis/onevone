import logging
import threading
import json
from onevone import log
from onevone.utils import (StaticDataContext, MatchContext)
from daemon import Daemon
import sys

MINUTE = 60
HOUR = 3600
DAY = HOUR * 24
WEEK = DAY * 7


REGIONS = [
    'EUNE',
    'EUW',
    'NA',
    'KR'
]


class IntervalWorker(object):

    def __init__(self, interval, action, *args, **kwargs):
        log.debug('New Interval Worker {0}'.format(action))
        self._timer = None
        self.interval = interval
        self.action = action
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.run()

    def run(self):
        self.is_running = False
        self.execute()

    def execute(self):
        if not self.is_running:
            self.is_running = True
            self.action(*self.args, **self.kwargs)
        else:
            log.ward('Worker {0} already running. Restarting...'.format(
                self.action))
        self._timer = threading.Timer(self.interval, self.run)
        self._timer.start()

    def stop(self):
        self._timer.cancel()
        self.is_running = False


class UpdaterDaemon(Daemon):

    def check_version(self):
        latest_versions = StaticDataContext.get_api_version()['versions'][:10]
        with open('/var/tmp/onevone/api_version.json', 'r+') as v:
            versions = json.load(v)
            current_version = versions['versions'][0]
            if current_version is None or latest_versions[0] > current_version:
                log.debug('Updating Version from {0} to {1}'.format(
                    current_version, latest_versions[0]))
                v.seek(0)
                v.truncate()
                json.dump({'versions': latest_versions}, v, indent=4)
                return False
        return True

    def update_static_data(self):
        if not self.check_version():
            log.warn('Older version detected. Updating Static Tables')
            StaticDataContext.populate_static_data()
            StaticDataContext.generate_static_images()

    def run(self):
        self.update_static_data()
        version_checker = IntervalWorker(DAY, self.update_static_data)
        log.debug('Found {0} Regions {1}'.format(len(REGIONS), ', '.join(REGIONS)))
        log.debug('Booting {0} threads'.format(len(REGIONS) * 3))
        for region in REGIONS:
            player_worker = IntervalWorker(WEEK,
                                           MatchContext.populate_players,
                                           region=region, player_limit=100)
            match_worker = IntervalWorker(5 * HOUR,
                                          MatchContext.populate_queued_matches,
                                          region=region, limit=30)
            matchup_worker = IntervalWorker(30*MINUTE,
                                            MatchContext.populate_matchups,
                                            region=region, limit=125)
        average_calc_worker = IntervalWorker(DAY,
                                             MatchContext.populate_averages)


if __name__ == "__main__":
    daemon = UpdaterDaemon('/tmp/onevone_updater-daemon.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print("Unknown command")
            sys.exit(2)
        sys.exit(0)
    else:
        print("usage: %s start|stop|restart" % sys.argv[0])
        sys.exit(2)
