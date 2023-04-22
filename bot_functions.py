import datetime as dt
import json
import qrcode
import telebot
import db


from telebot.util import quick_markup
from datetime import timedelta
from globals import (
    bot, agreement, USER_NOT_FOUND, ACCESS_DENIED, UG_CLIENT, ACCESS_DUE_TIME, ACCESS_ALLOWED,
    markup_client, markup_admin, markup_cancel_step, markup_skip, markup_agreement, markup_type_rent, markup_remove,
    UG_ADMIN, INPUT_DUE_TIME, chats, rate_box, rate_rack, rate_weight,
    # rules, ADMINS
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
        'address': None,  # адрес доставки
        'access': access,  # код доступа
        'shelf_life': None,  # количество месяцев аренды
        'type': None,  # тип аренды
        'value': None,
        'weight': None,  # значение для веса
        'agreement': None,  # для согласия на обработку данных
        'text': None,  # для разных целей - перспектива
        'number': None,  # для разных целей - перспектива
        'step_due': None,  # срок актуальности ожидания ввода данных (используем в callback функциях)
    }
    if access == ACCESS_DENIED and group == UG_CLIENT:
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
        'address': None,                # адрес доставки
        'shelf_life': None,             # количество месяцев аренды
        'type': None,                   # тип аренды
        'value': None,                  # значение для объема или количества
        'weight': None,                 # значение для веса
        'agreement': None,              # для согласия на обработку данных
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
    if not group or group == UG_CLIENT:
        markup = markup_client
        with open('data/welcome.json', 'r', encoding='utf-8') as fh:
            rules = json.load(fh)
        text = '\n'.join(rules)
        bot.send_message(chat_id, text)
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


def get_rent_to_client(message: telebot.types.Message, step=0):
    user = chats[message.chat.id]
    user['callback'] = 'rent_to_client'
    if step == 0:
        msg = bot.send_message(message.chat.id, 'Введите Имя',
                               parse_mode='Markdown', reply_markup=markup_cancel_step)
        user['callback_source'] = [msg.id, ]
        bot.register_next_step_handler(msg, get_rent_to_client, 1)
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
        bot.register_next_step_handler(message, get_rent_to_client, 2)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(message.chat.id, 'Время ввода данных истекло')
        cancel_step(message)
        return
    elif step == 2:
        user['number'] = message.text
        bot.send_document(message.chat.id, open(agreement, 'rb'))
        msg = bot.send_message(message.chat.id, 'Ознакомьтесь с согласием на обработку персональных данных. '
                             'При согласии введите "Принять" или нажмите кнопку отмены.',
                             parse_mode='Markdown', reply_markup=markup_agreement)
        user['callback_source'] = [msg.id, ]
        bot.register_next_step_handler(msg, get_rent_to_client, 3)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(message.chat.id, 'Время ввода данных истекло')
        cancel_step(message)
        return
    elif step == 3:
        user['agreement'] = message.text
        if user['agreement'] == 'Принять':
            msg = bot.send_message(message.chat.id, 'Выбирите тип аренды. Бокс для хранения или стеллаж для документов.'
                                   , parse_mode='Markdown', reply_markup=markup_type_rent)
            user['callback_source'] = [msg.id, ]
            bot.register_next_step_handler(msg, get_rent_to_client, 4)
            user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
        else:
            bot.send_message(message.chat.id, 'Отмена заявки')
            cancel_step(message)
    elif step == 4:
        user['type'] = message.text
        if user['type'] == 'Бокс':
            msg = bot.send_message(message.chat.id, 'Введите перечень вещей, которые хотите сдать на хранение '
                                                    'или просто нажмите пропустить и мы все сделаем сами при приемке',
                                   parse_mode='Markdown', reply_markup=markup_skip)
            user['callback_source'] = [msg.id, ]
            bot.register_next_step_handler(msg, get_rent_to_client, 5)
            user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
        elif user['type'] == 'Стеллаж':
            msg = bot.send_message(message.chat.id, 'Введите цифрой общий количество стеллажей, которые хотите взять в '
                                                    'аренду или просто нажмите пропустить и мы все сделаем '
                                                    'сами при приемке',
                                   parse_mode='Markdown', reply_markup=markup_skip)
            user['callback_source'] = [msg.id, ]
            bot.register_next_step_handler(msg, get_rent_to_client, 6)
            user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
        else:
            bot.send_message(message.chat.id, 'Отмена заявки')
            cancel_step(message)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(message.chat.id, 'Время ввода данных истекло')
        cancel_step(message)
        return
    elif step == 5:
        user['text'] = message.text
        msg = bot.send_message(message.chat.id, 'Введите цифрой общий объем вещей в м3, которые хотите сдать на '
                                                'хранение или просто нажмите пропустить и мы все сделаем сами '
                                                'при приемке',
                                   parse_mode='Markdown', reply_markup=markup_skip)
        user['callback_source'] = [msg.id, ]
        bot.register_next_step_handler(msg, get_rent_to_client, 6)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(message.chat.id, 'Время ввода данных истекло')
        cancel_step(message)
        return
    elif step == 6:
        try:
            user['value'] = int(message.text)
        except:
            user['value'] = 0

        msg = bot.send_message(message.chat.id, 'Введите цифрой общий вес вещей в кг, которые хотите сдать на хранение '
                                                'или просто нажмите пропустить и мы все сделаем сами при приемке',
                                                parse_mode='Markdown', reply_markup=markup_skip)
        user['callback_source'] = [msg.id, ]
        bot.register_next_step_handler(msg, get_rent_to_client, 7)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(message.chat.id, 'Время ввода данных истекло')
        cancel_step(message)
        return
    elif step == 7:
        try:
            user['weight'] = int(message.text)
        except:
            user['weight'] = 0
        msg = bot.send_message(message.chat.id, 'Введите цифрой количество месяцев хранения '
                                                'или просто нажмите пропустить и мы все сделаем сами при приемке',
                               parse_mode='Markdown', reply_markup=markup_skip)
        user['callback_source'] = [msg.id, ]
        bot.register_next_step_handler(msg, get_rent_to_client, 8)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(message.chat.id, 'Время ввода данных истекло')
        cancel_step(message)
        return
    elif step == 8:
        try:
            user['shelf_life'] = int(message.text)
        except:
            user['shelf_life'] = 0
        msg = bot.send_message(message.chat.id, 'Введите адрес забора вещей на хранение '
                                                'или просто нажмите пропустить если самостоятельно их привезете',
                               parse_mode='Markdown', reply_markup=markup_skip)
        user['callback_source'] = [msg.id, ]
        bot.register_next_step_handler(msg, get_rent_to_client, 9)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(message.chat.id, 'Время ввода данных истекло')
        cancel_step(message)
        return
    elif step == 9:
        user['address'] = message.text
        tg_name = message.from_user.username
        tg_user_id = message.chat.id
        date_reg = dt.date.today()
        date_end = date_reg + timedelta(days=user['shelf_life']*30)
        status = 1
        box_number = db.get_number_box(user['type'])
        price = get_price(user['type'], user['value'], user['weight'], user['shelf_life'])
        db.add_new_user(user['name'], user['number'], tg_name, tg_user_id)
        order_id = db.add_order(tg_user_id, user['number'], user['address'], user['agreement'], user['value'],
                                user['weight'], user['shelf_life'], date_reg, date_end, status, user['text'], price,
                                box_number)

        bot.send_message(message.chat.id, f'Заявка на хранение #{order_id} зарегистрирована. '
                         f'Предварительная стоимость {price} руб.',
                         reply_markup=markup_remove)
        bot.send_message(message.chat.id, f'Варианты действий ',
                         reply_markup=markup_client)
        user['callback'] = None
        user['callback_source'] = []

def get_price(type, value=0, weight=0, shelf_life=0):
    if type == 'Бокс':
        price = int(value) * int(shelf_life) * rate_box + (int(weight) * rate_weight)
    else:
        price = int(value) * rate_rack
    return price


def get_rules_to_client(message: telebot.types.Message):
    user = chats[message.chat.id]
    with open('data/rules.json', 'r', encoding='utf-8') as fh:
        rules = json.load(fh)
    text = ' \n '.join(rules)
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup_client)
    user['callback'] = None
    user['callback_source'] = []


def get_client_pantry(message: telebot.types.Message):
    user_orders = db.get_user_orders(message.chat.id)
    client_calls: list = chats[message.chat.id]['callback_source']
    if not user_orders:
        bot.send_message(message.chat.id, 'У вас нет зарегистрированных заявок')
        return
    for order in user_orders:
        buttons = {}
        order_id = order['order_id']
        inventory = order['inventory']
        date_reg = order['date_reg']
        client_address = order['client_address']
        if client_address == 'Пропустить':
            client_address = 'Самостоятельная доставка'
        if order['status'] == 1:
            status_text = 'заявка принята к исполнению'
            buttons['Отменить заявку'] = {'callback_data': f'cancel_app_id:{order_id}'}
        if order['status'] == 2:
            status_text = 'заявка на складе'
            buttons['Открыть бокс'] = {'callback_data': f'open_box_id:{order["order_id"]}'}
            buttons['Оформить доставку'] = {'callback_data': f'arrange_delivery_id:{order["order_id"]}'}
            buttons['Закрыть аренду'] = {'callback_data': f'close_lease_id:{order["order_id"]}'}
        if order['status'] == 3:
            status_text = 'заявка в статусе доставки'
        if order['status'] == 4:
            status_text = 'заявка в статусе закрытия'

        msg_text = f'*Заявка #{order_id}*\n---\n' \
                   f'На хранение: {inventory}\n---\n' \
                   f'Адрес доставки: {client_address}\n---\n' \
                   f'Дата регистрации: {date_reg}\n---\n' \
                   f'Статус: {status_text}\n'
        msg = bot.send_message(message.chat.id, msg_text,
                               parse_mode='Markdown',
                               reply_markup=quick_markup(buttons))
        client_calls.append(msg.id)


def cancel_app_id(message: telebot.types.Message, order_id):
    callback_source: list = chats[message.chat.id]['callback_source']
    db.change_status(order_id, 5)
    msg = bot.send_message(message.chat.id, 'Заявка закрыта', reply_markup=markup_client)
    callback_source.append(msg.id)


def open_box_id(message: telebot.types.Message, order_id):
    callback_source: list = chats[message.chat.id]['callback_source']
    msg = bot.send_message(message.chat.id, 'Для открытия воспользуйтесь QR code')
    create_qrcode(order_id, msg.id)
    msg = bot.send_photo(message.chat.id, open('open_box.png', 'rb'), reply_markup=markup_client)
    callback_source.append(msg.id)


def arrange_delivery_id(message: telebot.types.Message, order_id, step=0):
    user = chats[message.chat.id]
    user['callback'] = 'arrange_delivery_id'
    if step == 0:
        user['name'] = message.text
        msg = bot.send_message(message.chat.id,
                               'Введите номер контактного телефона', reply_markup=markup_cancel_step)
        user['callback_source'] = [msg.id]
        bot.register_next_step_handler(msg, arrange_delivery_id, order_id, 1)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(message.chat.id, 'Время ввода данных истекло')
        cancel_step(message)
        return
    if step == 1:
        user['number'] = message.text
        msg = bot.send_message(message.chat.id,
                               'Введите адрес доставки', reply_markup=markup_cancel_step)
        user['callback_source'] = [msg.id]
        bot.register_next_step_handler(msg, arrange_delivery_id, order_id, 2)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(message.chat.id, 'Время ввода данных истекло')
        cancel_step(message)
        return
    if step == 2:
        user['address'] = message.text
        db.change_status(order_id, 3)
        db.change_delyvery_data(order_id, user['number'], user['address'])
        msg = bot.send_message(message.chat.id,
                               'Заказ принят, в течение часа с Вами свяжутся для согласования времени доставки '
                               , reply_markup=markup_client)
        user['callback'] = None
        user['callback_source'] = []


def close_lease_id(message: telebot.types.Message, order_id):
    callback_source: list = chats[message.chat.id]['callback_source']
    db.change_status(order_id, 4)
    msg = bot.send_message(message.chat.id, 'Заявка на закрытие принята', reply_markup=markup_client)
    callback_source.append(msg.id)


def create_qrcode(data, msq_id):
    filename = 'open_box.png'
    img = qrcode.make(''.join([data, str(msq_id)]))
    img.save(filename)



#
# просроченное хранение
# def get_overdue_storage(message: telebot.types.Message):
#     msg_text = None
#     if not msg_text:
#         msg_text = 'overdue_storage'
#     # msg_text = db.get_requests(status)
#     bot.send_message(message.chat.id, msg_text, parse_mode='Markdown')
#
# заказы на хранение
# def get_storage_orders(message: telebot.types.Message):
#     msg_text = None
#     # msg_text = db.get_requests(status)
#     if not msg_text:
#         msg_text = 'status = storage_order'
#     bot.send_message(message.chat.id, msg_text, parse_mode='Markdown')
#
# возврат заказов
# def get_return_orders(message: telebot.types.Message):
#     msg_text = None
#     # msg_text = db.get_requests(status)
#     if not msg_text:
#         msg_text = 'status = return_order'
#     bot.send_message(message.chat.id, msg_text, parse_mode='Markdown')
#
# удачные заказы
# def get_success_orders(message: telebot.types.Message):
#     msg_text = None
#     # msg_text = db.get_requests(status)
#     if not msg_text:
#         msg_text = 'status = success'
#     bot.send_message(message.chat.id, msg_text, parse_mode='Markdown')
#
# неудачные заказы
# def get_fail_orders(message: telebot.types.Message):
#     msg_text = None
#     # msg_text = db.get_requests(status)
#     if not msg_text:
#         msg_text = 'status = fail'
#     bot.send_message(message.chat.id, msg_text, parse_mode='Markdown')


