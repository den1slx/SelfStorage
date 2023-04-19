import telebot


from environs import Env
from telebot.util import quick_markup


env = Env()
env.read_env()
tg_bot_token = env('TG_CLIENTS_TOKEN')
bot = telebot.TeleBot(token=tg_bot_token)

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

markup_add_user = quick_markup({
    'Регистрация': {'callback_data': 'add_user'},
  })


chats = {}
