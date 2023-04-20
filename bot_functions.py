import datetime as dt
import telebot
import db


from telebot.util import quick_markup
from datetime import timedelta
from globals import (
    bot, USER_NOT_FOUND, ACCESS_DENIED, UG_CLIENT, ACCESS_DUE_TIME, ACCESS_ALLOWED,
    markup_client, markup_admin, markup_cancel_step, markup_add_user, UG_ADMIN, INPUT_DUE_TIME, chats
)


# COMMON FUNCTIONS

def start_bot(message: telebot.types.Message):
    user_name = message.from_user.username
    bot.send_message(message.chat.id, f'Здравствуйте, {message.from_user.username}.')
    access_due = dt.datetime.now() + dt.timedelta(0, ACCESS_DUE_TIME)
    access, group = db.check_user_access(tg_name=user_name)
    chats[message.chat.id] = {
        'callback': None,  # current callback button
        'last_msg': [],  # последние отправленные за один раз сообщения (для подчистки кнопок) -- перспектива
        'callback_source': [],  # если задан, колбэк кнопки будут обрабатываться только с этих сообщений
        'group': group,  # группа, к которой принадлежит пользователь
        'access_due': access_due,  # дата и время актуальности кэшированного статуса
        'access': access,  # код доступа
        'text': None,  # для разных целей - перспектива
        'number': None,  # для разных целей - перспектива
        'step_due': None,  # срок актуальности ожидания ввода данных (используем в callback функциях)
    }
    if access == USER_NOT_FOUND:
        bot.send_message(message.chat.id, 'Вы не зарегистрированы в системе.', reply_markup=markup_add_user)
        return
    elif access == ACCESS_DENIED and group == UG_CLIENT:

        bot.send_message(message.chat.id, 'Ваша аренда в просроке, новые заявки создать нельзя.'
                                          'обратитесь к администратору для решения данного вопроса')
    show_main_menu(message.chat.id, group)


def cache_user(chat_id):
    user = db.get_user_by_chat_id(chat_id)
    access_due = dt.datetime.now() + dt.timedelta(0, ACCESS_DUE_TIME)
    chats[chat_id] = {
        'name': None,
        'callback': None,               # current callback button
        'last_msg': [],                 # последние отправленные за один раз сообщения, в которых нужно удалить кнопки
        'callback_source': [],          # если задан, колбэк кнопки будут обрабатываться только с этих сообщений
        'group': user['user_group'],    # группа, к которой принадлежит пользователь
        'access_due': access_due,       # дата и время актуальности кэшированного статуса
        'access': user['access'],       # код доступа
        'text': None,                   # для разных целей - перспектива
        'number': None,                 # для разных целей - перспектива
        'step_due': None,               # срок  ожидания ввода данных (используем в callback функциях)
    }
    return chats[chat_id]


def check_user_in_cache(msg: telebot.types.Message):
    """проверят наличие user в кэше
    это на случай, если вдруг случился сбой/перезапуск скрипта на сервере
    и кэш приказал долго жить. В этом случае нужно отправлять пользователя в начало
    пути, чтобы избежать ошибок """
    user = chats.get(msg.chat.id)
    if not user:
        bot.send_message(msg.chat.id, 'Упс. Что то пошло не так.\n'
                                      'Начнем с главного меню')
        start_bot(msg)
        return None
    else:
        return user


def show_main_menu(chat_id, group):
    user = chats[chat_id]
    if user['access_due'] < dt.datetime.now():
        access, group = db.check_user_access(tg_user_id=chat_id)
        user['access_due'] = dt.datetime.now() + dt.timedelta(0, ACCESS_DUE_TIME)
        user['access'] = access
        user['group'] = group
    """
    show main menu (the set of callback buttons depending on user group)
    :param chat_id: chat_id of the user
    :param group: user group (see UT_* constants in db.py)
    :return:
    """
    markup = None
    if group == UG_CLIENT:
        markup = markup_client
    elif group == UG_ADMIN:
        markup = markup_admin
    msg = bot.send_message(chat_id, 'Варианты действий', reply_markup=markup)
    chats[chat_id]['callback_source'] = [msg.id, ]
    chats[chat_id]['callback'] = None


def cancel_step(message: telebot.types.Message):
    """cancel current input process and show main menu"""
    bot.clear_step_handler(message)
    bot.send_message(message.chat.id, 'Действие отменено')
    show_main_menu(message.chat.id, chats[message.chat.id]['group'])
    chats[message.chat.id]['callback'] = None


def add_user(message: telebot.types.Message, step=0):
    user = chats[message.chat.id]
    user['callback'] = 'add_user'
    if step == 0:
        msg = bot.send_message(message.chat.id, 'Введите ФИО пользователя для регистации',
                               parse_mode='Markdown', reply_markup=markup_cancel_step)
        user['callback_source'] = [msg.id, ]
        bot.register_next_step_handler(msg, add_user, 1)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(message.chat.id, 'Время ввода данных истекло')
        cancel_step(message)
        return
    elif step == 1:
        user['name'] = message.text
        msg = bot.send_message(
            message.chat.id, 'Введите номер телефона', parse_mode='Markdown', reply_markup=markup_cancel_step)
        user['callback_source'] = [msg.id]
        bot.register_next_step_handler(message, add_user, 2)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif step == 2:
        tg_name = message.from_user.username
        tg_user_id = message.chat.id
        phone = message.text
        user_id = db.add_new_user(user['name'], phone, tg_name, tg_user_id)
        bot.send_message(message.chat.id, f'Пользователь #{user_id} - {user["name"]} зарегистрирован.',
                         reply_markup=markup_client)
        user['callback'] = None
        user['callback_source'] = []


def get_rules_to_client(message: telebot.types.Message):
    msg_text = '''Написать правила хранения'''
    bot.send_message(message.chat.id, msg_text, parse_mode='Markdown')


def get_rent_to_client(message: telebot.types.Message):
    msg_text = '''Функция не готова'''
    bot.send_message(message.chat.id, msg_text, parse_mode='Markdown')


def get_client_pantry(message: telebot.types.Message):
    msg_text = '''Функция не готова'''
    bot.send_message(message.chat.id, msg_text, parse_mode='Markdown')

