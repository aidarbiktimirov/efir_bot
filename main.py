#!/usr/bin/env python
# coding: utf-8

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


def profile_link(user_id):
    return '\nShare your stats — http://tahminet.fenegram.com/{}'.format(user_id)


def dump_top_stats(top_stats, the_user):
    def dump_line(pos, user, is_specified_user):
        smilies = ['👳', '👦', '👨', '👩', '👵', '👴', '👱']
        return '{}. {} {} {}{} ({})'.format(
            pos, smilies[hash(user.name['first_name']) % len(smilies)], user.name['first_name'].encode('utf8'), user.name['last_name'].encode('utf8'),
            ' (you)' if is_specified_user else '', int(100 * user.rating))

    user_pos = the_user.get_leaderbord_index()
    if user_pos == len(top_stats) + 1:
        top_stats.append(the_user)
    return 'Leaderboard ({} people total)\n'.format(
        db_wrapper.User.count()
    ) + '\n'.join(
        dump_line(i + 1, user, i + 1 == user_pos) for i, user in enumerate(top_stats)
    ) + (
        '\n-----\n' + dump_line(user_pos, the_user, True) if user_pos > len(top_stats) else ''
    ) + profile_link(the_user.telegram_id)


def vote_distribution(event):
    return '\n'.join(
        '{} — {}%'.format(k, int(100 * v))
        for k, v in event.get_vote_stats().iteritems()
    )


def dump_grouptop_stats(chat_id, user_id):
    def dump_line(user):
        smilies = ['👳', '👦', '👨', '👩', '👵', '👴', '👱']
        return '{}. {} {} {} ({})'.format(user.get_leaderbord_index(), smilies[hash(user.name['first_name']) % len(smilies)],
            user.name['first_name'].encode('utf8'), user.name['last_name'].encode('utf8'), int(100 * user.rating))

    users = [db_wrapper.User(telegram_id) for telegram_id in db_wrapper.Chat(chat_id).users]
    return 'Leaderboard ({} people total)\n'.format(
        db_wrapper.User.count()
    ) + '\n'.join(dump_line(user) for user in sorted(users, key=lambda user: -user.rating)) + profile_link(user_id)


def save_chat_user(message):
    if isinstance(message.chat, telebot.types.GroupChat):
        db_wrapper.Chat(message.chat.id).add_user(message.from_user.id)


@bot.message_handler(commands=['vote'])
def vote_handler(message):
    save_chat_user(message)
    event = get_upcoming_event(message.from_user.id)
    if event is None:
        bot.reply_to(message, 'You’ve already voted. You cannot change your vote.😛')
        return
    bot.reply_to(message, 'Guess the score for the game {} on {}. Type the score you expect, like 3:2 or 0-1.'.format(event.name.encode('utf8'), event.vote_until.strftime('%d %B, %Y')))
    user_states[message.from_user.id] = UserState.WAITING_FOR_VOTE
    user_events[message.from_user.id] = event.event_id
    users = event_users.get(event.event_id, set())
    users.add(message.from_user.id)
    event_users[event.event_id] = users


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, UserState.UNKNOWN) == UserState.WAITING_FOR_VOTE)
def handle_vote(message):
    save_chat_user(message)
    if db_wrapper.Event(user_events.get(message.from_user.id)).vote_until <= datetime.datetime.utcnow():
        bot.reply_to(message, 'Sorry, the event has already started')
        user_states[user_events.get(message.from_user.id)] = UserState.UNKNOWN
        return
    predictions = [word.split(':') for word in message.text.split() if ':' in word] + [word.split('-') for word in message.text.split() if '-' in word]
    try:
        assert predictions and len(predictions[0]) == 2
        a, b = int(predictions[0][0]), int(predictions[0][1])
    except:
        bot.reply_to(message, '{} I expect something like 3:2 or 0-1.'.format(telegram.Emoji.GRINNING_FACE_WITH_SMILING_EYES))
        return
    event = db_wrapper.Event(user_events.get(message.from_user.id))
    bot.reply_to(message, 'Your guess is {}:{}. You’ll know how well you did right after the end of the match on {}. Here’s how other people voted:\n{}'.format(
        a, b, event.vote_until.strftime('%d %B, %Y'), vote_distribution(event)))
    db_wrapper.Vote(message.from_user.id, user_events.get(message.from_user.id)).set_score('{}:{}'.format(a, b))
    user_states[message.from_user.id] = UserState.UNKNOWN
    db_wrapper.User.ensure_exists(message.from_user.id, {'first_name': message.from_user.first_name, 'last_name': message.from_user.last_name})
    event_id = user_events.get(message.from_user.id)
    db_wrapper.Event(event_id).add_listener_chat(message.chat.id)
    del user_events[message.from_user.id]


@bot.message_handler(commands=['top'])
def top_handler(message):
    save_chat_user(message)
    if isinstance(message.chat, telebot.types.User):
        bot.send_message(message.chat.id, dump_top_stats(db_wrapper.User.get_top(5), db_wrapper.User(message.from_user.id)))
    else:
        bot.send_message(message.chat.id, dump_grouptop_stats(message.chat.id, message.from_user.id))


@bot.message_handler(commands=['help'])
def help_handler(message):
    save_chat_user(message)
    bot.send_message(message.chat.id, str(bot.get_me()))


@bot.message_handler(commands=['stats'])
def stats_handler(message):
    save_chat_user(message)
    if isinstance(message.chat, telebot.types.User):
        user = db_wrapper.User(message.from_user.id)
        vote = user.get_last_vote_for_finished_event()
        event = db_wrapper.Event(vote.event_id)
        p = vote.predicted_score.split(':')
        t = event.score.split(':')
        score_diff = abs(int(p[0]) - int(t[0])) + abs(int(p[1]) - int(t[1]))
        status_line = '👯 You knew it! 👯' if score_diff == 0 else '👋 You’ve almost got it! 👋' if score_diff == 1 else '😔 Hope you’ll do better next time! 😔'
        result_line = '{} {} {}:{} {} {}'.format(
            event.team1.flag.encode('utf8'), event.team1.name.encode('utf8'), t[0],
            t[1], event.team2.name.encode('utf8'), event.team2.flag.encode('utf8'),
        )
        prediction_line = 'Your prediction was {}:{}'.format(*p)
        score_line = 'Total score: {} points (+{})'.format(int(100 * user.rating), int(100 * (user.rating - user.prev_rating)))
        rating_line = 'Current rating — {} of {}'.format(user.get_leaderbord_index(), db_wrapper.User.count())
        share_line = profile_link(user.telegram_id).strip()
        bot.send_message(message.chat.id, '{}\n\n{}\n{}\n\n{}\n{}\n{}'.format(status_line, result_line, prediction_line, score_line, rating_line, share_line))
    else:
        event = db_wrapper.Event.get_last_processed_event()
        if event is None:
            return
        smilies = ['👳', '👦', '👨', '👩', '👵', '👴', '👱']
        t = event.score.split(':')
        result_line = '{} {} {}:{} {} {}'.format(
            event.team1.flag.encode('utf8'), event.team1.name.encode('utf8'), t[0],
            t[1], event.team2.name.encode('utf8'), event.team2.flag.encode('utf8'),
        )
        prediction_lines = [
            '{}. {} {} {}: voted {} +{} points ({} total)'.format(i + 1, smilies[hash(user.name['first_name']) % len(smilies)],
                user.name['first_name'].encode('utf8'), user.name['last_name'].encode('utf8'),
                db_wrapper.Vote(user.telegram_id, event.event_id).predicted_score,
                int(100 * user.rating - user.prev_rating), int(100 * user.rating),
            )
            for i, user in enumerate(
                sorted((db_wrapper.User(user_id) for user_id in db_wrapper.Chat(message.chat.id).users), key=lambda user: -(user.rating - user.prev_rating))
            )
            if db_wrapper.Vote(user.telegram_id, event.event_id).predicted_score is not None
        ]
        bot.send_message(message.chat.id, 'The match ⚽️ has finished!\n\n{}\n{}'.format(result_line, '\n'.join(prediction_lines)))


@bot.message_handler()
def handle_other_messages(message):
    save_chat_user(message)
    """
    bot.reply_to(message, 'No poll is currently active for you, maybe you want to start one by typing /vote?')
    """


def event_notifier(bot):
    while True:
        for event in db_wrapper.Event.get_events_with_no_start_notification():
            print '{} didn’t have start notification'.format(event.name.encode('utf8'))
            listeners = event.get_listeners()
            print '{} are listening for it'.format(listeners)
            for chat in listeners:
                bot.send_message(chat, '{} has just started!'.format(event.name.encode('utf8')))
            event.set_start_notification_sent()
        for event in db_wrapper.Event.get_events_with_no_score_notification():
            print '{} didn’t have score notification'.format(event.name.encode('utf8'))
            listeners = event.get_listeners()
            print '{} are listening for it'.format(listeners)
            for chat in listeners:
                bot.send_message(chat, '{} has just finished! Final score is {}\nCheck out how everyone did by typing /stats'.format(event.name.encode('utf8'), event.score))
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
