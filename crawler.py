#!/usr/bin/env python

import db_wrapper
import requests
import time
import datetime


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
                        'country_iso': team['country_iso']
                    }
                )

                if team['id'] == 78710:
                    self._is_fenerbache_playing = True

            self._id = sportapi_competition['_id']
            self._is_started = (sportapi_competition['status'] == 'in_progress' or
                                sportapi_competition['status'] == 'finished')
            self._is_finished = sportapi_competition['status'] == 'finished'
            self._result = sportapi_competition['result']

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

    def name(self):
        return "%s(%s) vs %s(%s)" % (self._teams[0]['name'],
                                     self._teams[0]['country_iso'],
                                     self._teams[1]['name'],
                                     self._teams[1]['country_iso'])


class YandexSportAPICrawler(object):
    def __init__(self):
        db_wrapper.init('188.166.85.96', 27017, None, None)

    @staticmethod
    def get_new_competitions():

        skip = 0
        payload = {
            'period': '150d',
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
        for competition in YandexSportAPICrawler.get_new_competitions():
            print competition.name()
            now = datetime.datetime.utcnow()
            db_wrapper.Event.add(competition.competition_id(), competition.name(), now)
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

    start_time = time.time()
    while True:
        YandexSportAPICrawler.crawl()
        time.sleep(60.0 - ((time.time() - start_time) % 60.0))
