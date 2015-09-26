#!/usr/bin/env python

import db_wrapper
import resources
import requests
import time
import dateutil.parser

# country_flags = {
#     'TR': unicode('\x1f1f7')
# }


class Competition(object):
    def __init__(self, sportapi_competition):
        if 'teams' not in sportapi_competition or len(sportapi_competition['teams']) != 2:
            raise Exception('invalid competition')
        else:
            self._teams = []
            self._is_fenerbache_playing = False
            for team in sportapi_competition['teams']:
                self._teams.append(
                    {
                        'id': team['id'],
                        'name': team['name']['en'],
                        'flag': unicode(resources.country_flags[team['country_iso']]) \
                            if team['country_iso'] in resources.country_flags else unicode('')
                    }
                )

                if team['id'] == 78710:
                    self._is_fenerbache_playing = True

            self._id = sportapi_competition['_id']
            self._is_started = (sportapi_competition['status'] == 'in_progress' or
                                sportapi_competition['status'] == 'finished')
            self._is_finished = sportapi_competition['status'] == 'finished'
            self._result = sportapi_competition['result']
            self._start_date = dateutil.parser.parse(sportapi_competition['dt_start'])

    def __str__(self):
        return 'id: %s, is_started: %r, is_finished: %r, result: %s' % \
               (str(self._id),
                str(self._is_started),
                str(self._is_finished),
                str(self._result))

    def is_fenerbache(self):
        return self._is_fenerbache_playing

    def competition_id(self):
        return self._id

    def score(self):
        return "%d:%d" % (self._result[0], self._result[1])

    def finished(self):
        return self._is_finished

    def teams(self):
        return self._teams

    def name(self):
        return "%s - %s" % (self._teams[0]['name'],
                            self._teams[1]['name'])

    def start_date(self):
        return self._start_date


class YandexSportAPICrawler(object):
    def __init__(self):
        db_wrapper.init('188.166.85.96', 27017, None, None)

    @staticmethod
    def get_new_competitions():

        skip = 0
        payload = {
            'period': '7d',
            'limit': '1000',
        }

        new_events = []
        has_more_competitions = True
        while has_more_competitions:
            payload['skip'] = skip

            fetched = False
            while not fetched:
                response = requests.get('http://api.sport.yandex.ru/v2/football/events', params=payload)
                fetched = (response.status_code == 200)
                time.sleep(1)

            api_competitions = response.json()

            if len(api_competitions) == 0:
                has_more_competitions = False

            skip += len(api_competitions)
            for api_competition in api_competitions:
                try:
                    competition = Competition(api_competition)
                except Exception as e:
                    continue
                if competition.is_fenerbache():
                    new_events.append(competition)

        return new_events

    @staticmethod
    def crawl():
        competitions = YandexSportAPICrawler.get_new_competitions()
        for competition in competitions:
            # print 'Competition: '
            # print competition.name()
            print '%s %s' % (competition.name(), str(competition.start_date()))
            db_wrapper.Event.add(competition.competition_id(), competition.name(), competition.teams(), competition.start_date())
            event = db_wrapper.Event(competition.competition_id())
            if competition.finished():
                event.set_score(competition.score())

    @staticmethod
    def get_known_events():
        known_event_ids = []
        for event in db_wrapper.Event.get_all():
            known_event_ids.append(event.event_id)
        return known_event_ids


if __name__ == '__main__':
    db_wrapper.init('188.166.85.96', 27017, None, None)

    while True:
        try:
            YandexSportAPICrawler.crawl()
        except Exception as e:
            print e
        finally:
            time.sleep(60)
