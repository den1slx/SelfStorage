import sqlite3


from globals import USER_NOT_FOUND, ACCESS_DENIED, ACCESS_ALLOWED



def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


con = sqlite3.connect("database.db", check_same_thread=False)
con.row_factory = dict_factory


#Пример работы с БД

def get_example(user_id):
    cur: sqlite3.Cursor = con.execute(f'select * from orders where client_id="{user_id}"')
    row = cur.fetchone()
    cur.close()
    return row

example = get_example(933137433)

print(example)
print(example['client_address'])

def get_user_by_chat_id(chat_id):
    cur: sqlite3.Cursor = con.execute(f'select *  from users where tg_user_id={chat_id}')
    row = cur.fetchone()
    cur.close()
    return row


def check_user_access(tg_name=None, tg_user_id=None):
    '''проверяет наличие доступа к системе у пользователя с указанным именем.
    (имеется ввиду имя пользователя в Telegram)
    Возвращает кортеж (а, б), где а=-1 - пользователя нет в БД.
    а=0 - пользователь есть в БД, но нет доступа
    а=1 - пользователь есть в БД и обладает доступом
    б - код группы пользователя (0-админы, 1-клиенты)
    '''
    cur: sqlite3.Cursor = con.execute(f"select access, user_group "
                                      f"from users where tg_name='{tg_name if tg_name else 0}' or "
                                      f"tg_user_id={tg_user_id if tg_user_id else 0}"
                                      )
    row = cur.fetchone()
    cur.close()
    if not row:
        return (USER_NOT_FOUND, None)
    elif row['access']:
        return (ACCESS_ALLOWED, row['user_group'])
    else:
        return (ACCESS_DENIED, row['user_group'])



def add_new_user(name, phone, tg_name, tg_user_id, user_group=1, access=1):
    data = (name, phone, tg_name, tg_user_id, user_group, access)
    cur = con.execute(
        'insert into users '
        '(name, phone, tg_name, tg_user_id, user_group, access) '
        'values( ?, ?, ?, ?, ?, ?)', data)
    con.commit()
    cur.close()
    return cur.lastrowid