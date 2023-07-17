import telebot
import psycopg2

TOKEN = ''
bot = telebot.TeleBot(TOKEN)

connect_text = {}
table_name = {}
columns = {}

commands = [
    telebot.types.BotCommand('start', 'запустить бота'),
    telebot.types.BotCommand('create_table', 'создать таблицу'),
    telebot.types.BotCommand('insert_data', 'вставить данные в таблицу'),
    telebot.types.BotCommand('delete_row', 'удалить данные из таблицы')]
bot.set_my_commands(commands)

def open_database_connection():
    db_name = connect_text.get('dbname', '...')
    user_name = connect_text.get('user', '...')
    password = connect_text.get('password', '...')
    tableName = table_name.get('t_name', '...')
    conn = psycopg2.connect(dbname=db_name, user=user_name, password=password, host='127.0.0.1')
    cur = conn.cursor()
    return conn, cur

@bot.message_handler(commands=['start'])
def start(message):
    user_name = message.from_user.first_name
    bot.reply_to(message, 'привет, {0}'.format(user_name) + '\nотправь мне данные для создания таблицы, \nи она появится в твоей базе данных PostgreSQL')
    bot.send_message(message.chat.id, 'введите название базы данных:')
    bot.register_next_step_handler(message, get_dbname)

def get_dbname(message):
    connect_text['dbname'] = message.text
    bot.send_message(message.chat.id, 'введите имя пользователя:')
    bot.register_next_step_handler(message, get_username)

def get_username(message):
    connect_text['user'] = message.text
    bot.send_message(message.chat.id, 'введите пароль:')
    bot.register_next_step_handler(message, get_password)

def get_password(message):
    connect_text['password'] = message.text
    conn, cur = open_database_connection()
    if conn.closed == 0:
        bot.send_message(message.chat.id, 'соединение установлено!')
    else:
        bot.send_message(message.chat.id, 'соединение не установлено((')
    cur.close()
    conn.close()

@bot.message_handler(commands=['create_table'])
def named_table(message):
    bot.send_message(message.chat.id, 'введите название таблицы:')
    bot.register_next_step_handler(message, create_table)

def create_table(message):
    table_name['t_name'] = message.text
    bot.send_message(message.chat.id, 'введите количество колонок:')
    bot.register_next_step_handler(message, get_column_names)

def get_column_names(message):
    try:
        num_columns = int(message.text)
    except ValueError:
        bot.send_message(message.chat.id, 'некорректное количество колонок. попробуйте еще раз.')
        bot.register_next_step_handler(message, get_column_names)
        return
    bot.send_message(message.chat.id, 'введите название и тип данных для колонки 1 (через пробел):')
    bot.register_next_step_handler(message, get_column_info, 1, num_columns, [])

def get_column_info(message, column_num, num_columns, column_names):
    column_info = message.text.split()
    if len(column_info) != 2:
        bot.send_message(message.chat.id, 'некорректный ввод. попробуйте еще раз.')
        bot.register_next_step_handler(message, get_column_info, column_num, num_columns, column_names)
        return
    columns[column_info[0]] = column_info[1]
    column_names.append(column_info[0])
    if column_num < num_columns:
        bot.send_message(message.chat.id, f'введите название и тип данных для колонки {column_num+1} (через пробел):')
        bot.register_next_step_handler(message, get_column_info, column_num+1, num_columns, column_names)
    else:
        conn, cur = open_database_connection()
        querry = f"CREATE TABLE {table_name['t_name']} ({', '.join([f'{col} {columns[col]}' for col in columns])})"
        cur.execute(querry)
        conn.commit()
        column_names_str = ' | '.join(column_names)
        bot.send_message(message.chat.id, f'ваша таблица {table_name["t_name"]} выглядит вот так:\n{column_names_str}')
        cur.close()
        conn.close()

@bot.message_handler(commands=['insert_data'])
def get_column_values(message):
    conn, cur = open_database_connection()
    cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name['t_name']}'")
    rows = cur.fetchall()
    column_names = [row[0] for row in rows]
    global column_names_str
    column_names_str = ", ".join(column_names)
    bot.send_message(message.chat.id, f'введите данные для всех столбцов через пробел ({column_names_str}):')
    cur.close()
    conn.close()
    bot.register_next_step_handler(message, insert_data, column_names)

def insert_data(message, column_names):
    conn, cur = open_database_connection()
    values = message.text.strip().split()
    if len(values) != len(column_names):
        bot.send_message(message.chat.id, f'неверное количество значений. введите данные для всех {len(column_names)} столбцов.')
        bot.register_next_step_handler(message, insert_data, column_names)
        return
    values_str = ', '.join([f"'{value}'" for value in values])
    cur.execute(f"INSERT INTO {table_name['t_name']} ({column_names_str}) VALUES ({values_str})")
    conn.commit()
    bot.send_message(message.chat.id, f'данные "{values_str}" успешно добавлены в столбцы {column_names_str}\nхотите добавить что-то еще? (y/n)')
    cur.close()
    conn.close()
    bot.register_next_step_handler(message, get_answer, column_names)

def get_answer(message, column_names):
    answer = message.text
    if answer == 'y':
        conn, cur = open_database_connection()
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name['t_name']}'")
        rows = cur.fetchall()
        column_names = [row[0] for row in rows]
        cur.close()
        conn.close()
        bot.send_message(message.chat.id, f'введите данные для всех столбцов через пробел ({", ".join(column_names)}):')
        bot.register_next_step_handler(message, insert_data, column_names)
    else:
        bot.send_message(message.chat.id, 'хорошо, рад был помочь')

@bot.message_handler(commands=['delete_row'])
def delete_row(message):
    bot.send_message(message.chat.id, 'введите номер строки для удаления:')
    bot.register_next_step_handler(message, delete_row_by_number)

def delete_row_by_number(message):
    try:
        row_num = int(message.text)
    except ValueError:
        bot.send_message(message.chat.id, 'некорректный номер строки. попробуйте еще раз.')
        return

    conn, cur = open_database_connection()
    querry = f"DELETE FROM {table_name['t_name']} WHERE ctid IN (SELECT ctid FROM {table_name['t_name']} LIMIT 1 OFFSET {row_num-1})"
    cur.execute(querry)
    conn.commit()

    if cur.rowcount == 0:
        bot.send_message(message.chat.id, 'строка с таким номером не найдена.')
    else:
        bot.send_message(message.chat.id, f'строка {row_num} удалена')
    cur.close()
    conn.close()

if __name__ == '__main__':
    bot.infinity_polling(none_stop=True)
