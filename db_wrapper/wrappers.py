#!/usr/bin/env python

import datetime
import pymongo

_client = None


def init(hostname, port, username, password):
    global _client
    _client = pymongo.MongoClient(hostname, port)
    _client.efir_bot.authenticate(username, password)


class User(object):
    def __init__(self, telegram_id):
        self.telegram_id = telegram_id
        rec = _client.efir_bot.users.find_one({'telegram_id': self.telegram_id}) or {}
        self.rating = rec.get('rating', 0)
        self.prev_rating = rec.get('prev_rating', 0)

    def update_rating(self, new_rating):
        _client.efir_bot.users.update_one({'telegram_id': self.telegram_id}, {'$set': {'rating': new_rating, 'prev_rating': self.rating}}, True)
        self.prev_rating = self.rating
        self.rating = new_rating


class Event(object):
    def __init__(self, event_id):
        self.event_id = event_id
        rec = _client.efir_bot.users.find_one({'event_id': self.event_id}) or {}
        self.score = rec.get('score')
        self.name = rec.get('name', '')
        self.processed = rec.get('processed', False)

    def set_score(self, new_score):
        _client.efir_bot.events.update_one({'event_id': self.event_id}, {'$set': {'score': new_score}}, True)

    def set_processed(self):
        _client.efir_bot.events.update_one({'event_id': self.event_id}, {'$set': {'processed': True}})

    def get_votes(self):
        return [Vote(rec['user_id'], self.event_id) for rec in _client.efir_bot.votes.find({'event_id': self.event_id})]

    @staticmethod
    def get_unprocessed_events():
        return [Event(rec['event_id']) for rec in _client.efir_bot.events.find({'processed': {'$exists': False}})]


class Vote(object):
    def __init__(self, user_id, event_id):
        self.user_id = user_id
        self.event_id = event_id
        rec = _client.efir_bot.votes.find_one({'user_id': self.user_id, 'event_id': self.event_id}) or {}
        self.predicted_score = rec.get('predicted_score')
        self.timestamp = rec.get('timestamp')

    def set_score(self, new_score):
        if self.predicted_score is None:
            _client.efir_bot.votes.update({'user_id': self.user_id, 'event_id': self.event_id}, {'$set': {'predicted_score': new_score, 'timestamp': datetime.datetime.now()}})
