#!/usr/bin/env python

import datetime
import pymongo

_client = None


def init(hostname, port, username, password):
    global _client
    _client = pymongo.MongoClient(hostname, port)
    if username is not None and password is not None:
        _client.zefir.authenticate(username, password)


class User(object):
    def __init__(self, telegram_id):
        self.telegram_id = telegram_id
        rec = _client.zefir.users.find_one({'telegram_id': self.telegram_id}) or {}
        self.rating = rec.get('rating', 0)
        self.prev_rating = rec.get('prev_rating', 0)

    def update_rating(self, new_rating):
        _client.zefir.users.update_one({'telegram_id': self.telegram_id}, {'$set': {'rating': new_rating, 'prev_rating': self.rating}}, True)
        self.prev_rating = self.rating
        self.rating = new_rating


class Event(object):
    def __init__(self, event_id):
        self.event_id = event_id
        rec = _client.zefir.events.find_one({'event_id': self.event_id}) or {}
        self.score = rec.get('score')
        self.vote_unit = rec.get('vote_until')
        self.name = rec.get('name', '')
        self.processed = rec.get('processed', False)

    def set_score(self, new_score):
        _client.zefir.events.update_one({'event_id': self.event_id}, {'$set': {'score': new_score}}, True)

    def set_processed(self):
        _client.zefir.events.update_one({'event_id': self.event_id}, {'$set': {'processed': True}})

    def get_votes(self):
        return [Vote(rec['user_id'], self.event_id) for rec in _client.zefir.votes.find({'event_id': self.event_id})]

    @staticmethod
    def get_unprocessed_events():
        return [Event(rec['event_id'])
                for rec in _client.zefir.events.find({'processed': {'$exists': False}, 'score': {'$exists': True}})]


class Vote(object):
    def __init__(self, user_id, event_id):
        self.user_id = user_id
        self.event_id = event_id
        rec = _client.zefir.votes.find_one({'user_id': self.user_id, 'event_id': self.event_id}) or {}
        self.predicted_score = rec.get('predicted_score')
        self.timestamp = rec.get('timestamp')

    def set_score(self, new_score):
        if self.predicted_score is None:
            _client.zefir.votes.update({'user_id': self.user_id, 'event_id': self.event_id}, {'$set': {'predicted_score': new_score, 'timestamp': datetime.datetime.now()}})


def get_events():
    events = []
    for event in _client.zefir.events.find({}):
        events.append(event)
    return events
