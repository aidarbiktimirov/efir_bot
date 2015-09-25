#!/usr/bin/env python

import telebot
import telegram

bot = telebot.TeleBot(token='133575332:AAGsTXPkOIhJ2Mlmj-QOVQ-QhKmff5GMCoo')


@bot.message_handler()
def handle_every_message(message):
    print message.text
    if message.text in ['a', 'b', telegram.Emoji.TOILET]:
        bot.reply_to(message, message.text, reply_markup=telebot.types.ReplyKeyboardHide())
        return
    keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    keyboard.row('a', 'b')
    keyboard.row(telegram.Emoji.TOILET)
    bot.reply_to(message, message.text, reply_markup=keyboard)


if __name__ == '__main__':
    bot.polling()
