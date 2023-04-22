import datetime as dt
import threading
import time

import schedule

import bot_functions as calls
from globals import *

calls_map = {
    'rules_to_client': calls.get_rules_to_client,
    'rent_to_client': calls.get_rent_to_client,
    'client_pantry': calls.get_client_pantry,
    # 'overdue_storage': calls.get_overdue_storage,
    # 'storage_orders': calls.get_storage_orders,
    # 'return_orders': calls.get_return_orders,
}

calls_id_map = {
    'cancel_app_id': calls.cancel_app_id,
    'open_box_id': calls.open_box_id,
    'arrange_delivery_id': calls.arrange_delivery_id,
    'close_lease_id': calls.close_lease_id,

}


@bot.message_handler(commands=['start'])
def command_start(message: telebot.types.Message):
    calls.start_bot(message)


@bot.message_handler(commands=['menu'])
def command_menu(message: telebot.types.Message):
    user = calls.check_user_in_cache(message)
    if not user:
        return
    else:
        calls.show_main_menu(message.chat.id, user['group'])


@bot.message_handler()
def get_text(message):
    if calls.check_user_in_cache(message):
        bot.send_message(message.chat.id, 'Для работы с ботом пользуйтесь кнопками')


@bot.callback_query_handler(func=lambda call: call.data)
def handle_buttons(call):
    user = calls.check_user_in_cache(call.message)
    if not user:
        return
    source = user['callback_source']
    if source and not call.message.id in user['callback_source']:
        bot.send_message(call.message.chat.id, 'Кнопка не актуальна\n'
                                               '/menu - показать основное меню')
        return
    elif (dt.datetime.now() - dt.timedelta(0, 180)) > dt.datetime.fromtimestamp(call.message.date):
        bot.send_message(call.message.chat.id, 'Срок действия кнопки истек')
        calls.show_main_menu(call.message.chat.id, chats[call.message.chat.id]['group'])
        return
    btn_command: str = call.data
    current_command = user['callback']
    if btn_command == 'cancel_step':
        if current_command:
            calls.cancel_step(call.message)
        return
    if user['callback']:
        bot.send_message(call.message.chat.id,
                         f'Вы находитесь в режиме '
                         f'ввода данных другой команды.\n'
                         f'Сначала завершите ее или отмените')
        return
    if 'id' in btn_command:
        parts = btn_command.split(':')
        key_func = parts[-1]
        func_name = parts[0]
        calls_id_map[func_name](call.message, key_func)
        return
    else:
        calls_map[call.data](call.message)


def runBot():
    bot.polling(none_stop=True, interval=0)


def runSchedulers():
    schedule.every().monday.at("11:30")

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    t1 = threading.Thread(target=runBot)
    t2 = threading.Thread(target=runSchedulers)
    # starting thread 1
    t1.start()
    # starting thread 2
    t2.start()
