#!/usr/bin/env python

import threading
import datetime
import json
import time

import telegram
import telebot

import db_wrapper

bot = telebot.TeleBot(token='132375141:AAGndKMqlQL-g0X-s6v-Sit5Xv-8ihZX1Yc')
user_states = {}
user_events = {}
event_users = {}

class UserState(object):
    UNKNOWN = 0
    WAITING_FOR_VOTE = 1


def get_upcoming_event(user_id):
    events = [event for event in db_wrapper.Event.get_upcoming_events() if db_wrapper.Vote(user_id, event.event_id).predicted_score is None]
    return events[0] if events else None


def dump_top_stats(top_stats, the_user):
    def dump_line(pos, user, is_specified_user):
        return '{}. {} {} - {} points{}'.format(
            pos, user.name['first_name'], user.name['last_name'],
            int(100 * user.rating), ' (you)' if is_specified_user else '')
    user_pos = the_user.get_leaderbord_index()
    if user_pos == len(top_stats) + 1:
        top_stats.append(the_user)
    return '\n'.join(
        dump_line(i + 1, user, i + 1 == user_pos) for i, user in enumerate(top_stats)
    ) + (
        '\n-----\n' + dump_line(user_pos, the_user, True) if user_pos > len(top_stats) else ''
    )


@bot.message_handler(commands=['vote'])
def vote_handler(message):
    event = get_upcoming_event(message.from_user.id)
    if event is None:
        bot.reply_to(message, 'There are no upcoming events for you to vote for {}'.format(telegram.Emoji.CRYING_CAT_FACE))
        return
    bot.reply_to(message, 'Vote for upcoming match {}'.format(event.name))
    user_states[message.from_user.id] = UserState.WAITING_FOR_VOTE
    user_events[message.from_user.id] = event.event_id
    users = event_users.get(event.event_id, set())
    users.add(message.from_user.id)
    event_users[event.event_id] = users


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, UserState.UNKNOWN) == UserState.WAITING_FOR_VOTE)
def handle_vote(message):
    if db_wrapper.Event(user_events.get(message.from_user.id)).vote_until <= datetime.datetime.utcnow():
        bot.reply_to(message, 'Sorry, the event has already started')
        user_states[user_events.get(message.from_user.id)] = UserState.UNKNOWN
        return
    predictions = [word.split(':') for word in message.text.split() if ':' in word] + [word.split('-') for word in message.text.split() if '-' in word]
    try:
        assert predictions and len(predictions[0]) == 2
        a, b = int(predictions[0][0]), int(predictions[0][1])
    except:
        bot.reply_to(message, 'Please fix your vote, it\'s incorrect {}\nYour vote should look like 1:2 or 1-2'.format(telegram.Emoji.ANGRY_FACE))
        return
    bot.reply_to(message, 'Thank you for your vote {}!'.format(message.from_user.first_name))
    db_wrapper.Vote(message.from_user.id, user_events.get(message.from_user.id)).set_score('{}:{}'.format(a, b))
    user_states[message.from_user.id] = UserState.UNKNOWN
    db_wrapper.User.ensure_exists(message.from_user.id, {'first_name': message.from_user.first_name, 'last_name': message.from_user.last_name})
    event_id = user_events.get(message.from_user.id)
    db_wrapper.Event(event_id).add_listener_chat(message.chat.id)
    del user_events[message.from_user.id]


@bot.message_handler(commands=['stats'])
def stats_handler(message):
    bot.send_message(message.chat.id, dump_top_stats(db_wrapper.User.get_top(1), db_wrapper.User(message.from_user.id)))


@bot.message_handler()
def handle_other_messages(message):
    bot.reply_to(message, 'No poll is currently active for you, maybe you want to start one by typing /vote?')


def event_notifier(bot):
    while True:
        for event in db_wrapper.Event.get_events_with_no_start_notification():
            print '{} didn\'t have start notification'.format(event.name)
            listeners = event.get_listeners()
            print '{} are listening for it'.format(listeners)
            for chat in listeners:
                bot.send_message(chat, '{} has just started!'.format(event.name))
            event.set_start_notification_sent()
        for event in db_wrapper.Event.get_events_with_no_score_notification():
            print '{} didn\'t have score notification'.format(event.name)
            listeners = event.get_listeners()
            print '{} are listening for it'.format(listeners)
            for chat in listeners:
                bot.send_message(chat, '{} has just finished! Final score is {}\nCheck out how everyone did by typing /stats'.format(event.name, event.score))
            event.set_score_notification_sent()
        time.sleep(5)


if __name__ == '__main__':
    with open('config.json') as config:
        config = json.load(config)
        db_wrapper.init(**config)
        event_notifier_thread = threading.Thread(target=event_notifier, args=(bot, ))
        event_notifier_thread.start()
        bot.polling()
        event_notifier_thread.join()
