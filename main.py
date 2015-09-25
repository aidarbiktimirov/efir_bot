#!/usr/bin/env python

import json

import telegram
import telebot

import db_wrapper

bot = telebot.TeleBot(token='132375141:AAGndKMqlQL-g0X-s6v-Sit5Xv-8ihZX1Yc')
user_states = {}
user_events = {}

class UserState(object):
    UNKNOWN = 0
    WAITING_FOR_VOTE = 1


def get_upcoming_event(user_id):
    try:
        events = [event for event in db_wrapper.Event.get_upcoming_events() if db_wrapper.Vote(user_id, event.event_id).predicted_score is None]
        return events[0] if events else None
    except Exception as e:
        print e


@bot.message_handler(commands=['vote'])
def vote_handler(message):
    event = get_upcoming_event(message.from_user.id)
    if event is None:
        bot.reply_to(message, 'There are no upcoming events for you to vote for {}'.format(telegram.Emoji.CRYING_CAT_FACE))
        return
    bot.reply_to(message, 'Vote for upcoming match {}'.format(event.name))
    user_states[message.from_user.id] = UserState.WAITING_FOR_VOTE
    user_events[message.from_user.id] = event.event_id


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, UserState.UNKNOWN) == UserState.WAITING_FOR_VOTE)
def handle_vote(message):
    predictions = [word.split(':') for word in message.text.split() if ':' in word]
    try:
        assert predictions and len(predictions[0]) == 2
        a, b = int(predictions[0][0]), int(predictions[0][1])
    except:
        bot.reply_to(message, 'Please fix your vote, it\'s incorrect {}'.format(telegram.Emoji.ANGRY_FACE))
        return
    bot.reply_to(message, 'Thank you for your vote {}!'.format(message.from_user.first_name))
    db_wrapper.Vote(message.from_user.id, user_events.get(message.from_user.id)).set_score('{}:{}'.format(a, b))
    user_states[message.from_user.id] = UserState.UNKNOWN
    del user_events[message.from_user.id]
    db_wrapper.User.ensure_exists(message.from_user.id, {'first_name': message.from_user.first_name, 'last_name': message.from_user.last_name})


@bot.message_handler(commands=['stats'])
def stats_handler(message):
    bot.send_message(message.chat.id, 'TODO')


@bot.message_handler()
def handle_other_messages(message):
    bot.reply_to(message, 'No poll is currently active for you, maybe you want to start one by typing /vote?')


if __name__ == '__main__':
    with open('config.json') as config:
        config = json.load(config)
        db_wrapper.init(**config)
        bot.polling()
