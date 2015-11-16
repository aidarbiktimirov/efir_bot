#!/usr/bin/env python
# coding: utf-8

import threading
import datetime
import json
import time

import telegram
import telebot
import flask

import db_wrapper
from texts import TEXTS

bot = telebot.TeleBot(token='132375141:AAGndKMqlQL-g0X-s6v-Sit5Xv-8ihZX1Yc')
user_states = {}
user_events = {}
event_users = {}

class UserState(object):
    UNKNOWN = 0
    WAITING_FOR_VOTE = 1


def get_upcoming_event():
    events = db_wrapper.Event.get_upcoming_events(limit = 1)
    if len(events) > 0:
        return events[0]
    return None

def profile_link(user_id):
    return '\n{} — http://tahminet.fenegram.com/{}'.format(TEXTS['top_share_stats'], user_id)


def dump_top_stats(top_stats, the_user):
    def dump_line(pos, user, is_specified_user):
        smilies = ['👳', '👦', '👨', '👩', '👵', '👴', '👱']
        return '{}. {} {} {}{} ({})'.format(
            pos, smilies[hash(user.name['first_name']) % len(smilies)], user.name['first_name'].encode('utf8'), user.name['last_name'].encode('utf8'),
            ' (you)' if is_specified_user else '', int(100 * user.rating))

    user_pos = the_user.get_leaderbord_index()
    if user_pos == len(top_stats) + 1:
        top_stats.append(the_user)
    return TEXTS["top_leaderboard_header"].format(
        db_wrapper.User.count()
    ) + '\n' + '\n'.join(
        dump_line(i + 1, user, user.telegram_id == the_user.telegram_id) for i, user in enumerate(top_stats)
    ) + (
        '\n-----\n' + dump_line(user_pos, the_user, True) if user_pos > len(top_stats) else ''
    ) + profile_link(the_user.telegram_id)


def vote_distribution(event):
    smilies = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']
    return '\n'.join(
        '{} {}% {}{}'.format(s, int(100 * v), k, ' 🚀' if s == smilies[0] else '')
        for s, (k, v) in zip(smilies, sorted(event.get_vote_stats().iteritems(), key=lambda x: -x[1]))
    )


def dump_grouptop_stats(top_stats, chat_id, user_id):
    def dump_line(user):
        smilies = ['👳', '👦', '👨', '👩', '👵', '👴', '👱']
        return '{}. {} {} {} ({})'.format(user.get_leaderbord_index(), smilies[hash(user.name['first_name']) % len(smilies)],
            user.name['first_name'].encode('utf8'), user.name['last_name'].encode('utf8'), int(100 * user.rating))
    users = top_stats
    user_ids = [user.telegram_id for user in top_stats]
    for telegram_id in db_wrapper.Chat(chat_id).users:
        if not telegram_id in user_ids:
            users += [db_wrapper.User(telegram_id)]
    return TEXTS["top_leaderboard_header"].format(
        db_wrapper.User.count()
    ) + '\n' + '\n'.join(dump_line(user) for user in sorted(users, key=lambda user: -user.rating) if user.name['first_name']) + profile_link(user_id)


def save_chat_user(message):
    if message.chat.type == "group":
        db_wrapper.Chat(message.chat.id).add_user(message.from_user.id)


@bot.message_handler(commands=['vote'])
def vote_handler(message):
    save_chat_user(message)
    event = get_upcoming_event()
    user_vote = db_wrapper.Vote(message.from_user.id, event.event_id)
    if not user_vote.predicted_score is None:
        bot.reply_to(message, TEXTS["vote_already_voted"].format(user_vote.predicted_score, event.vote_until.day, event.vote_until.strftime('%B %Y')))
        return
    bot.reply_to(message, TEXTS["vote_prompt"].format(event.name.encode('utf8'), event.vote_until.day, event.vote_until.strftime('%B %Y')))
    user_states[message.from_user.id] = UserState.WAITING_FOR_VOTE
    user_events[message.from_user.id] = event.event_id
    users = event_users.get(event.event_id, set())
    users.add(message.from_user.id)
    event_users[event.event_id] = users


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, UserState.UNKNOWN) == UserState.WAITING_FOR_VOTE)
def handle_vote(message):
    save_chat_user(message)
    if db_wrapper.Event(user_events.get(message.from_user.id)).vote_until <= datetime.datetime.utcnow():
        bot.reply_to(message, TEXTS["vote_already_started"])
        user_states[user_events.get(message.from_user.id)] = UserState.UNKNOWN
        return
    predictions = [word.split(':') for word in message.text.split() if ':' in word] + [word.split('-') for word in message.text.split() if '-' in word]
    try:
        assert predictions and len(predictions[0]) == 2
        a, b = int(predictions[0][0]), int(predictions[0][1])
    except:
        bot.reply_to(message, TEXTS["vote_invalid_prediction"].format(telegram.Emoji.GRINNING_FACE_WITH_SMILING_EYES))
        return
    event = db_wrapper.Event(user_events.get(message.from_user.id))
    bot.reply_to(message, TEXTS["vote_accept_prediction"].format(
        a, b, event.vote_until.day, event.vote_until.strftime('%B, %Y'), vote_distribution(event)))
    db_wrapper.Vote(message.from_user.id, user_events.get(message.from_user.id)).set_score('{}:{}'.format(a, b))
    user_states[message.from_user.id] = UserState.UNKNOWN
    db_wrapper.User.ensure_exists(message.from_user.id, {'first_name': message.from_user.first_name, 'last_name': message.from_user.last_name})
    event_id = user_events.get(message.from_user.id)
    db_wrapper.Event(event_id).add_listener_chat(message.chat.id)
    del user_events[message.from_user.id]


@bot.message_handler(commands=['top'])
def top_handler(message):
    save_chat_user(message)
    if message.chat.type == "private":
        bot.send_message(message.chat.id, dump_top_stats(db_wrapper.User.get_top(5), db_wrapper.User(message.from_user.id)))
    else:
        bot.send_message(message.chat.id, dump_grouptop_stats(db_wrapper.User.get_top(5), message.chat.id, message.from_user.id))


@bot.message_handler(commands=['help'])
def help_handler(message):
    save_chat_user(message)
    bot.send_message(message.chat.id, TEXTS["help"])


@bot.message_handler(commands=['stats'])
def stats_handler(message):
    save_chat_user(message)
    if message.chat.type == "private":
        message_stat_for_user(message.chat.id)
    else:
        message_stat_for_group(message.chat.id)

def message_stat_for_user(user_id):
    user = db_wrapper.User(user_id)
    vote = user.get_last_vote_for_finished_event()
    if vote is None:
        return
    event = db_wrapper.Event(vote.event_id)
    p = vote.predicted_score.split(':')
    t = event.score.split(':')
    score_diff = abs(int(p[0]) - int(t[0])) + abs(int(p[1]) - int(t[1]))
    status_line = TEXTS["user_stat_result_good"] if score_diff == 0 else TEXTS["user_stat_result_ok"] if score_diff == 1 else TEXTS["user_stat_result_bad"]
    result_line = '{} {} {}:{} {} {}'.format(
        event.team1.flag.encode('utf8'), event.team1.name.encode('utf8'), t[0],
        t[1], event.team2.name.encode('utf8'), event.team2.flag.encode('utf8'),
    )
    prediction_line = TEXTS["user_stat_prediction"].format(*p)
    score_line = TEXTS["user_stat_score"].format(int(100 * user.rating), int(100 * (user.rating - user.prev_rating)))
    rating_line = TEXTS["user_stat_rating"].format(user.get_leaderbord_index(), db_wrapper.User.count())
    share_line = profile_link(user.telegram_id).strip()
    bot.send_message(user_id, '{}\n\n{}\n{}\n\n{}\n{}\n{}'.format(status_line, result_line, prediction_line, score_line, rating_line, share_line))

def message_stat_for_group(group_id):
    event = db_wrapper.Event.get_last_processed_event()
    if event is None:
        return
    smilies = ['👳', '👦', '👨', '👩', '👵', '👴', '👱']
    result_line = TEXTS["group_stat_result"].format(
        event.team1.flag.encode('utf8'), event.team1.name.encode('utf8'),
        event.score,
        event.team2.name.encode('utf8'), event.team2.flag.encode('utf8'),
        event.vote_until.day, event.vote_until.strftime('%B %Y')
    )
    prediction_lines = [
        TEXTS["group_stat_prediction"].format(i + 1,
                                              smilies[hash(user.name['first_name']) % len(smilies)],
                                              user.name['first_name'].encode('utf8'),
                                              user.name['last_name'].encode('utf8'),
                                              db_wrapper.Vote(user.telegram_id, event.event_id).predicted_score,
                                              int(100 * (user.rating - user.prev_rating)), int(100 * user.rating)
        )
        for i, user in enumerate(
            sorted((db_wrapper.User(user_id) for user_id in db_wrapper.Chat(group_id).users), key=lambda user: -(user.rating - user.prev_rating))
        )
        if db_wrapper.Vote(user.telegram_id, event.event_id).predicted_score is not None
    ]
    bot.send_message(group_id, '{}\n{}'.format(result_line, '\n'.join(prediction_lines)))

@bot.message_handler(commands=['debug'])
def handle_debug_command(message):
    bot.send_message(message.chat.id, 'trying to remove custom keyboard', reply_markup=telebot.types.ReplyKeyboardHide())
    # bot.send_message(message.chat.id, bot.get_file(bot.get_user_profile_photos(int(message.text.split()[1])).photos[0][0].file_id).file_path)
    bot.send_message(message.from_user.id, 'debug')


@bot.message_handler()
def handle_other_messages(message):
    save_chat_user(message)
    """
    bot.reply_to(message, 'No poll is currently active for you, maybe you want to start one by typing /vote?')
    """


def event_notifier(bot):
    while True:
        try:
            for event in db_wrapper.Event.get_events_with_no_start_notification():
                print '{} didn’t have start notification'.format(event.name.encode('utf8'))
                listeners = event.get_listeners()
                print '{} are listening for it'.format(listeners)
                
                for chat in listeners:
                    try:
                        bot.send_message(chat, 'Voting has finished as the {} match is about to begin. Here’s what other people think:\n{}'.format(event.name.encode('utf8'), vote_distribution(event)))
                    except Exception as e:
                        print 'Couldn\'t send message to chat {} : {}'.format(chat, e)   
            	event.set_start_notification_sent()
            for event in db_wrapper.Event.get_events_with_no_score_notification():
                print '{} didn’t have score notification'.format(event.name.encode('utf8'))
                listeners = event.get_listeners()
                print '{} are listening for it'.format(listeners)
                for chat in listeners:
                    try:
                        if chat >= 0:
                            message_stat_for_user(chat)
                        else:
                            message_stat_for_group(chat)
                    except Exception as e:
                        print 'Couldn\'t send message to chat {} : {}'.format(chat, e) 
                event.set_score_notification_sent()
        except:
            pass
        time.sleep(5)


def handle_updates():
    try:
        data = flask.request.get_data()
        update = telebot.types.Update.de_json(data)
        bot.process_new_messages([update.message])
        return ''
    except Exception as e:
        print >> sys.stderr, 'Couldn\'t update: {}'.format(e)


def run_webhooks(cert, webhook):
    bot.remove_webhook()
    bot.set_webhook(url='https://{}:{}{}'.format(webhook['host'], webhook['port'], webhook['url']), certificate=open(cert['public']))
    app = flask.Flask(__name__)
    app.add_url_rule(webhook['url'], 'update', handle_updates, methods=['POST'])
    app.run(host='0.0.0.0', port=webhook['port'], ssl_context=(cert['public'], cert['private']), debug=False, threaded=True)


if __name__ == '__main__':
    with open('config.json') as config:
        config = json.load(config)
        db_wrapper.init(**config)
        event_notifier_thread = threading.Thread(target=event_notifier, args=(bot, ))
        event_notifier_thread.start()
        # bot.polling(True)
        run_webhooks(config['certificate'], config['webhook'])
        event_notifier_thread.join()
