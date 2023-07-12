import telebot
import psycopg2

bot = telebot.TeleBot('token')
commands = [
    telebot.types.BotCommand('start', 'запустить бота'),
    telebot.types.BotCommand('create_table', 'создать таблицу')]
bot.set_my_commands(commands)
columns = {}
connect_text = {}
table_name = {}

@bot.message_handler(commands=['start'])
def start(message):
    user_name = message.from_user.first_name
    bot.reply_to(message, 'привет, {0}'.format(user_name) + '\nотправь мне данные для создания таблицы, \nи она появится в твоей базе данных postgreSQL')
    bot.send_message(message.chat.id, 'введите название базы данных:')
    bot.register_next_step_handler(message, get_db_name)

def get_db_name(message):
    connect_text['dbname'] = message.text
    bot.send_message(message.chat.id, 'введите имя пользователя:')
    bot.register_next_step_handler(message, get_username)

def get_username(message):
    connect_text['user'] = message.text
    bot.send_message(message.chat.id, 'введите пароль:')
    bot.register_next_step_handler(message, get_password)

def get_password(message):
    connect_text['password'] = message.text
    bot.send_message(message.chat.id, 'введите адрес хоста:')
    bot.register_next_step_handler(message, get_host)

def get_host(message):
    connect_text['host'] = message.text

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
        bot.send_message(message.chat.id, 'некорректное количество колонок. попробуйте еще раз:')
        bot.register_next_step_handler(message, get_column_names)
        return
    bot.send_message(message.chat.id, 'введите название и тип данных для колонки 1 (через пробел):')
    bot.register_next_step_handler(message, get_column_info, 1, num_columns)

def get_column_info(message, column_num, num_columns):
    column_info = message.text.split()
    if len(column_info) != 2:
        bot.send_message(message.chat.id, 'некорректный ввод. попробуйте еще раз:')
        bot.register_next_step_handler(message, get_column_info, column_num, num_columns)
        return
    columns[column_info[0]] = column_info[1]
    if column_num < num_columns:
        bot.send_message(message.chat.id, f'введите название и тип данных для колонки {column_num+1} (через пробел):')
        bot.register_next_step_handler(message, get_column_info, column_num+1, num_columns)
    else:
        db_name = connect_text.get('dbname', '...')
        user_name = connect_text.get('user', '...')
        password = connect_text.get('password', '...')
        host = connect_text.get('host', '...')
        tableName = table_name.get('t_name', '...')
        conn = psycopg2.connect(dbname=db_name, user=user_name, password=password, host=host)
        if conn.closed == 0:
            bot.send_message(message.chat.id, 'соединение установлено!')
        else:
            bot.send_message(message.chat.id, 'соединение не установлено((')
        querry = f"CREATE TABLE {tableName} ({', '.join([f'{col} {columns[col]}' for col in columns])})"
        cur = conn.cursor()
        cur.execute(querry)
        conn.commit()
        bot.send_message(message.chat.id, 'таблица успешно создана!')

bot.polling()