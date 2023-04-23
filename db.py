import sqlite3

from globals import USER_NOT_FOUND, ACCESS_DENIED, ACCESS_ALLOWED


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


con = sqlite3.connect("database.db", check_same_thread=False)
con.row_factory = dict_factory


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
    cur: sqlite3.Cursor = con.execute(f"select name "
                                      f"from users where tg_user_id={tg_user_id if tg_user_id else 0} or "
                                      f"tg_name='{tg_name if tg_name else 0}'"
                                      )
    row = cur.fetchone()
    cur.close()
    if not row:
        data = (name, phone, tg_name, tg_user_id, user_group, access)
        cur = con.execute(
            'insert into users '
            '(name, phone, tg_name, tg_user_id, user_group, access) '
            'values( ?, ?, ?, ?, ?, ?)', data)
        con.commit()
        cur.close()
        return cur.lastrowid


def get_number_box(type):
    cur: sqlite3.Cursor
    if type == 'Бокс':
        for i in range(500, 900):
            cur = con.execute(f'select box_number from orders where box_number={i}')
            row = cur.fetchone()
            cur.close()
            if not row:
                return i
    else:
        for i in range(100, 400):
            cur = con.execute(f'select box_number from orders where box_number={i}')
            row = cur.fetchone()
            cur.close()
            if not row:
                return i


def add_order(client_id, client_phone, client_address, agreement, value, weight, shelf_life, date_reg,
              date_end, status, inventory, price, box_number):
    data = (client_id, client_phone, client_address, agreement, value, weight, shelf_life, date_reg,
            date_end, status, inventory, price, box_number)
    cur = con.execute(
        'insert into orders '
        '(client_id, client_phone, client_address, agreement, value, weight, shelf_life, date_reg,'
        'date_end, status, inventory, price, box_number)'
        'values( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', data)
    con.commit()
    cur.close()
    return cur.lastrowid


def get_user_orders(chat_id):
    cur: sqlite3.Cursor = con.execute(
        f'''SELECT orders.order_id, users.name,  orders.client_phone, orders.client_address, 
        orders.inventory, orders.date_reg, orders.status
        FROM users JOIN orders ON users.tg_user_id = orders.client_id
        WHERE orders.status IN ("1", "2", "3", "4") AND orders.client_id = "{chat_id}"'''
    )
    rows = cur.fetchall()

    cur.close()
    return rows


def get_first_order_by_status(status):
    cur: sqlite3.Cursor = con.execute(f'select *  from orders where status={status}')
    row = cur.fetchone()
    cur.close()

    return row


def convert_dict(dictionary):
    string = ''
    for item, value in dictionary.items():
        part = f"{item} = '{value}', "
        string += part
    return string[:-2]


def change_status(order_id, status):
    cur = con.execute(f'UPDATE orders SET status = {status} WHERE order_id LIKE "{order_id}"')
    con.commit()
    cur.close()
    return cur.lastrowid



def change_group(order_id, group):
    cur = con.execute(f'UPDATE orders SET group = {group} WHERE order_id LIKE "{order_id}"')
    con.commit()
    cur.close()
    return cur.lastrowid



def change_delyvery_data(order_id, phone, address):
    cur = con.execute(f'UPDATE orders SET client_phone = "{phone}", client_address = "{address}" '
                      f'WHERE order_id LIKE "{order_id}"')
    con.commit()
    cur.close()
    return cur.lastrowid


def get_order(order_id):
    order_id = int(order_id)
    cur: sqlite3.Cursor = con.execute(f'select * from orders where order_id="{order_id}"')
    row = cur.fetchone()
    cur.close()
    return row


def get_orders_by_status(status):
    cur: sqlite3.Cursor = con.execute(f'select * from orders where status={status}')
    row = cur.fetchall()
    cur.close()
    return row


def update_order_by_order_id(order_id, data):
    order = get_order(order_id)
    order.update(data)
    order = convert_dict(order)
    cur = con.execute(
        f"update orders set {order} where order_id={order_id}"
        )

    con.commit()
    cur.close()
    return cur.lastrowid


def get_orders_count():
    cur: sqlite3.Cursor = con.execute(f'select * from orders')
    row = cur.fetchall()
    cur.close()
    return len(row)

def get_date_end_active_orders():
    cur: sqlite3.Cursor = con.execute(f'select order_id, client_id, date_end, inventory from orders where status=1')
    rows = cur.fetchall()
    cur.close()
    return rows
