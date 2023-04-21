import telebot


from telebot import types
from environs import Env
from telebot.util import quick_markup


env = Env()
env.read_env()
tg_bot_token = env('TG_CLIENTS_TOKEN')
agreement = env('AGREEMENT')
bot = telebot.TeleBot(token=tg_bot_token)
# rules = env('RULES')
# ADMINS = env.list('ADMINS')

# user groups
UG_ADMIN = 0      # admimnistrators
UG_CLIENT = 1     # clients

# others
INPUT_DUE_TIME = 60     # time (sec) to wait for user text input
BUTTONS_DUE_TIME = 30   # time (sec) to wait for user clicks button
ACCESS_DUE_TIME = 300   # if more time has passed since last main menu we should check access again

# user access status
USER_NOT_FOUND = -1     # user not found in DB
ACCESS_DENIED = 0       # user is found but access is forbidden
ACCESS_ALLOWED = 1      # user is found and access is allowed

# main menu callback buttons
markup_client = quick_markup({
    'Правила хранения': {'callback_data': 'rules_to_client'},
    'Арендовать бокс': {'callback_data': 'rent_to_client'},
    'Моя кладовка': {'callback_data': 'client_pantry'},
})

markup_admin = quick_markup({
    'Просроченное хранение ': {'callback_data': 'overdue_storage'},
    'Заказы на хранение': {'callback_data': 'storage_orders'},
    'Заказы на возврат': {'callback_data': 'return_orders'},
})

markup_cancel_step = quick_markup({
    'Отмена': {'callback_data': 'cancel_step'},
  })

markup_skip = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
skip = types.KeyboardButton(text='Пропустить')
markup_skip.add(skip)

markup_type_rent = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
box = types.KeyboardButton(text='Бокс')
rack = types.KeyboardButton(text='Стеллаж')
markup_type_rent.add(box, rack)

markup_agreement = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
cancel = types.KeyboardButton(text='Отмена')
accept = types.KeyboardButton(text='Принять')
markup_agreement.add(cancel, accept)

markup_remove = types.ReplyKeyboardRemove()

chats = {}

rate_box = 1000
rate_rack = 899
rate_weight = 2
