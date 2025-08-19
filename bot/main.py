import datetime
import logging
import os
import telebot
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from telebot import types
from flask import Flask, request

from sqlalchemy import create_engine, func, case
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

load_dotenv()

TOKEN = os.getenv("TOKEN")
DB_NAME = os.getenv("DB_NAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", default="localhost")
DB_PORT = os.getenv("DB_PORT")
USER = os.getenv("USER")

# для отправки сообщений при отмене в общий чат
# ограничение использование бота только пользователями чата
CHAT_ID = -1002737626417

# для отправки сообщений при отмене в топик чата (подгруппу)
MESSAGE_THREAD_ID = 2

# количество доступных дней для бронирования
DAY = 3



bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db' #f'mysql+pymysql://{USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# POOL_RECYCLE ограничено 30с на beget
POOL_RECYCLE = 28
POOL_PRE_PING = True
POOL_TIMEOUT = 20

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('appbot.log', mode='a', encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
telebot.logger.addHandler(file_handler)


logger.info("Бот запущен")

engine = create_engine(
    app.config['SQLALCHEMY_DATABASE_URI'],
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=POOL_PRE_PING,
    pool_timeout=POOL_TIMEOUT,
    echo=False,
)

# Используем собственный SessionLocal, связанный с engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Инициализация SQLAlchemy с кастомным двигателем
db = SQLAlchemy(app, engine_options={
    'pool_recycle': POOL_RECYCLE,
    'pool_pre_ping': POOL_PRE_PING,
    'pool_timeout': POOL_TIMEOUT
})

# Обёртка для выполнения запросов с попыткой переподключения при ошибках
def query_with_reconnect(query_func):
    session = SessionLocal()
    try:
        return query_func(session)
    except OperationalError as e:
        if hasattr(e.orig, 'args') and e.orig.args[0] in (2006, 2013):  # MySQL server has gone away / Lost connection
            logger.warning("Переподключение к БД из-за ошибки: " + str(e))
            session.rollback()
            session.close()
            engine.dispose()  # сброс соединений в пуле
            session = SessionLocal()
            return query_func(session)
        else:
            raise
    finally:
        session.close()


def create_db():
    with app.app_context():
        db.create_all()

class BookKort(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(80), nullable=False)
    user_id = db.Column(db.String(80), nullable=False)
    time_create = db.Column(db.DateTime, default=datetime.datetime.now)
    time_start = db.Column(db.DateTime, nullable=False)
    time_finish = db.Column(db.DateTime, nullable=False)
    time_update = db.Column(db.DateTime, default=datetime.datetime.now)
    canseled = db.Column(db.Boolean , default=False)


#Раскомментировать при использовании WEBHOOK

# @app.route(f'/{TOKEN}', methods=['POST'])
# def twebhook():
#     logger.info("Отправка webhook")
#     json_string = request.stream.read().decode('utf-8')
#     update = telebot.types.Update.de_json(json_string)
#     bot.process_new_updates([update])
#     return '', 200
#
#
# @app.route('/app/')
# def index():
#     logger.info("Отправка app")
#     return 'This test flask'

days = {
    1: "Понедельник",
    2: "Вторник",
    3: "Среда",
    4: "Четверг",
    5: "Пятница",
    6: "Суббота",
    7: "Воскресенье"
}


def create_time(during_timer, timer_start, day):
    day, month, year = map(int, day.split("."))
    hour, minute = map(int, timer_start.split(':'))
    time_start = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=0)
    minutes_add = {'00:30': 30, '01:00': 60, '01:30': 90, '02:00': 120}
    time_finish = time_start + datetime.timedelta(minutes=minutes_add[during_timer])
    return time_start, time_finish


def start_menu(user_id, member):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Посмотреть расписание', callback_data=f'list_{user_id}'))
    markup.add(types.InlineKeyboardButton('Забронировать корт', callback_data=f'book_{user_id}'))
    markup.add(types.InlineKeyboardButton('Отменить бронь', callback_data=f'delete_{user_id}'))
    if member.status in ['administrator', 'creator'] or member.user.id == 1055012806:
        markup.add(types.InlineKeyboardButton('Статистика', callback_data=f'statistic_{user_id}'))
    return markup


def get_list_day(user_id, isInfo):
    markup = types.InlineKeyboardMarkup()
    today = datetime.date.today()
    for i in range(DAY):
        day_num = datetime.datetime.isoweekday(today)
        day_name = days[day_num]
        date_str = today.strftime("%d.%m.%Y")
        markup.add(types.InlineKeyboardButton(f'{date_str} ({day_name})',
                                              callback_data=f'day_{date_str}_{user_id}_{isInfo}'))
        today += datetime.timedelta(days=1)
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{user_id}'))
    return markup


def get_time_book(choice_day):
    day, month, year = map(int, choice_day.split('.'))
    time_start = datetime.datetime(year=year, month=month, day=day, hour=0, minute=0, second=0)
    if time_start < datetime.datetime.now():
        time_start = datetime.datetime.now()
    time_finish = datetime.datetime(year=year, month=month, day=day, hour=23, minute=0, second=0)

    def db_query(session):
        notes = session.query(BookKort).filter(
            BookKort.time_finish > time_start,
            BookKort.time_finish <= time_finish,
            BookKort.canseled == False
        )
        db_list_game = notes.order_by(BookKort.time_start).all()
        time_book = set()
        if db_list_game:
            for column in db_list_game:
                start = column.time_start
                finish = column.time_finish
                while start < finish:
                    time_book.add(start.time().strftime("%H:%M"))
                    start += datetime.timedelta(minutes=30)
        return time_book

    try:
        return query_with_reconnect(db_query)
    except Exception as e:
        with app.app_context():
            db.session.rollback()
            logger.error(f"При попытке получить забронированное время возникла ошибка {e}")
            return set()


def get_list_time(day, user_id):
    markup = types.InlineKeyboardMarkup(row_width=3)
    time_book = get_time_book(day)
    today = int(datetime.date.today().strftime('%d'))
    start_hour = 6
    start_minute = 0
    if (int(day.split(".")[0]) == today) and (datetime.datetime.now().hour > 6):
        start_hour = datetime.datetime.now().hour
        start_minute = datetime.datetime.now().minute
    buttons = []
    for hour in range(start_hour, 23):
        if f'{hour:02d}:00' not in time_book:
            if start_minute < 30 and hour == start_hour:
                buttons.append(types.InlineKeyboardButton(f'{hour}:00', callback_data=f'time_{hour}:00_{day}_{user_id}'))
            if hour != start_hour:
                buttons.append(
                    types.InlineKeyboardButton(f'{hour}:00', callback_data=f'time_{hour}:00_{day}_{user_id}'))
        if f'{hour:02d}:30' not in time_book:
            buttons.append(types.InlineKeyboardButton(f'{hour}:30', callback_data=f'time_{hour}:30_{day}_{user_id}'))
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{user_id}'))
    return markup


def get_free_time(timer_start, day, user_id):
    markup = types.InlineKeyboardMarkup()
    time_book = get_time_book(day)
    time_book.update(("23:00", "23:30"))
    markup.add(types.InlineKeyboardButton(f'30 минут', callback_data=f'during_00:30_{timer_start}_{day}_{user_id}'))
    time_start, time_check = create_time('00:30', timer_start, day)
    if time_check.time().strftime("%H:%M") not in time_book:
        markup.add(types.InlineKeyboardButton(f'1 час', callback_data=f'during_01:00_{timer_start}_{day}_{user_id}'))
    else:
        markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{day}_{user_id}'))
        return markup
    time_start, time_check = create_time('01:00', timer_start, day)
    if time_check.time().strftime("%H:%M") not in time_book and timer_start != '22:30':
        markup.add(
            types.InlineKeyboardButton(f'1 час 30 минут', callback_data=f'during_01:30_{timer_start}_{day}_{user_id}'))
    else:
        markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{day}_{user_id}'))
        return markup
    # time_start, time_check = create_time('01:30', timer_start, day)
    # if time_check.time().strftime("%H:%M") not in time_book and timer_start != '22:00':
    #     markup.add(types.InlineKeyboardButton(f'2 часа', callback_data=f'during_02:00_{timer_start}_{day}_{user_id}'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{day}_{user_id}'))
    return markup


def confirm_keys(during_timer, timer_start, day, user_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f'Да', callback_data=f'confirm_{during_timer}_{timer_start}_{day}_{user_id}'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{timer_start}_{day}_{user_id}'))
    return markup


def get_list_own_game(res, user_id):
    markup = types.InlineKeyboardMarkup()
    for column in res:
        game_id = column.id
        day = column.time_start.date().strftime("%d.%m.%Y")
        time_start = column.time_start.time().strftime("%H:%M")
        time_finish = column.time_finish.time().strftime("%H:%M")
        markup.add(types.InlineKeyboardButton(f'{day} c {time_start} до {time_finish}',
                                              callback_data=f'own game is_{game_id}_{user_id}'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{user_id}'))
    return markup


def confirm_delete_keys(game_id, user_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f'Да', callback_data=f'complited delete_{game_id}_{user_id}'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back delete_{user_id}'))
    return markup


def get_list_all_game(res):
    text = ''
    count = 0
    for column in res:
        count += 1
        user = column.user
        time_start = column.time_start.time().strftime("%H:%M")
        time_finish = column.time_finish.time().strftime("%H:%M")
        text += f'{count}. С {time_start} до {time_finish} ({user})\n'

    return text

def get_list_statistic(res):
    lines = []
    header = f'{"№":<4}|{"Имя пользователя":<20}|{"всего":>5}|{"отм.":>5}'
    separator = '-' * (4 + 1 + 20 + 1 + 5 + 1 + 5)
    lines.append(header)
    lines.append(separator)
    for i, (user, total, canceled) in enumerate(res, 1):
        lines.append(f'{i:<4} {user:<20} {total:>5} {canceled:>5}')
    table_text = '\n'.join(lines)
    return f'```\n{table_text}\n```'

@bot.message_handler(commands=['start'])
def main(message):
    # раскомментировать при первом запуске чтобы узнать id чата и топика
    # if message.from_user.first_name == "ARSENI":
    #     logger.info(f"{message.chat.id}")
    #     logger.info(f"{message.message_thread_id}")
    member = bot.get_chat_member(chat_id=CHAT_ID, user_id=message.from_user.id)
    if message.chat.type == "private":
        if member.status == 'member':
            user_id = message.from_user.id
            bot.send_message(message.chat.id, "Привет! Вот чем я могу тебе помочь: ",
                             reply_markup=start_menu(user_id, member), protect_content=True)
        elif member.status in ['administrator', 'creator'] or member.user.id == 1055012806:
            user_id = message.from_user.id
            bot.send_message(message.chat.id, "Привет! Вот чем я могу тебе помочь: ",
                             reply_markup=start_menu(user_id, member))
        else:
            bot.send_message(message.chat.id, "Привет! Вы не состоите в группе 'Tennis🎾_BIG_Цнянка'."
                                              "Добавьтесь пожалуйста в группу для возможности бронирования корта",
                             protect_content=True)
            logger.info(f"Попытка воспользоваться ботом незарегистрированному пользователю по имени"
                        f"{message.chat.first_name} {message.chat.last_name}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('book_'))
def book(callback):
    user_id = callback.data.split("_")[1]
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text="Выбери день:",
                          reply_markup=get_list_day(user_id=user_id, isInfo=False))
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('day_') and call.data.endswith('False'))
def timedate(callback):
    day = callback.data.split("_")[1]
    day_date = datetime.date(*list(map(int, day.split('.')[::-1])))
    user_id = callback.data.split("_")[2]

    def get_own_games(session):
        # today = datetime.datetime.now()
        notes = session.query(BookKort).filter(
            # BookKort.time_finish > today,
            func.DATE(BookKort.time_start) == day_date,
            BookKort.user_id == user_id,
            BookKort.canseled == False
        )
        return notes.all()

    try:
        new_note = query_with_reconnect(get_own_games)

        if new_note:
            logger.info(f"Попытка сделать вторую бронь в один день ")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{user_id}'))
            bot.edit_message_text(chat_id=callback.message.chat.id,
                                  message_id=callback.message.message_id,
                                  text="У вас уже есть бронь в этот день.",
                                  reply_markup=markup)

        else:
            bot.edit_message_text(chat_id=callback.message.chat.id,
                                  message_id=callback.message.message_id,
                                  text=f"{day} вы можете начать с:",
                                  reply_markup=get_list_time(day, user_id))
        bot.answer_callback_query(callback.id)

    except Exception as e:
        logger.error(f"При попытке забронировать корт возникла ошибка: {e}")
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              text="Произошла ошибка при чтении записей.\nПопробуйте ещё раз.")
        bot.answer_callback_query(callback.id)




@bot.callback_query_handler(func=lambda call: call.data.startswith('time_'))
def free_time(callback):
    name, timer_start, day, user_id = callback.data.split("_")
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text=f"Вы можете забронировать корт на:",
                          reply_markup=get_free_time(timer_start, day, user_id))
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('during_'))
def confirm_insert(callback):
    name, during_timer, timer_start, day, user_id = callback.data.split("_")
    during_dict = {'00:30': '30 минут', '01:00': '1 час', '01:30': '1 час 30 минут', '02:00': '2 часа'}
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text=f"Вы хотите {day} с {timer_start} забронировать корт на {during_dict[during_timer]}?",
                          reply_markup=confirm_keys(during_timer, timer_start, day, user_id))
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def complited_insert(callback):
    name, during_timer, timer_start, day, user_id = callback.data.split("_")
    if callback.message.chat.username:
        user = f'@{callback.message.chat.username}'
    else:
        user = f'{callback.message.chat.first_name} '
        last_name = callback.message.chat.last_name
        if last_name:
            user += last_name
    time_start, time_finish = create_time(during_timer, timer_start, day)
    time_book = get_time_book(day)
    timer_curr = time_start
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{user_id}'))
    while timer_curr < time_finish:
        if timer_curr.time().strftime("%H:%M") in time_book:
            bot.edit_message_text(chat_id=callback.message.chat.id,
                                  message_id=callback.message.message_id,
                                  text="Корт успели забронировать чуть раньше вас",
                                  reply_markup=markup)
            bot.answer_callback_query(callback.id)
            return  # Выходим из функции, т.к. бронирование невозможно
        timer_curr += datetime.timedelta(minutes=30)

    def insert_record(session):
        new_note = BookKort(user=user, user_id=user_id, time_start=time_start, time_finish=time_finish)
        session.add(new_note)
        session.commit()
        return new_note

    try:
        new_note = query_with_reconnect(insert_record)
        time_start_str = time_start.time().strftime("%H:%M")
        time_finish_str = time_finish.time().strftime("%H:%M")
        logger.info(f"Корт был забронирован пользователем {user}")
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              text=f"Вы забронировали корт {day} c {time_start_str} до {time_finish_str}.",
                              reply_markup=markup)
        bot.answer_callback_query(callback.id)
        bot.send_message(
            chat_id=CHAT_ID,
            text=f"📝 Бронь {day} c {time_start_str} до {time_finish_str}. ({user})",
            message_thread_id=MESSAGE_THREAD_ID  # возможно понадобится если в группе есть topic
        )
    except Exception as e:
        logger.error(f"При попытке забронировать корт возникла ошибка: {e}")
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              text="Произошла ошибка добавления записи.\nПопробуйте ещё раз.")
        bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('delete'))
def delete(callback):
    user_id = callback.data.split("_")[1]

    def get_own_games(session):
        notes = session.query(BookKort).filter(
            BookKort.time_finish > datetime.datetime.now(),
            BookKort.user_id == user_id,
            BookKort.canseled == False
        )
        return notes.order_by(BookKort.time_start).all()

    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{user_id}'))
        own_game = query_with_reconnect(get_own_games)

        if own_game:
            bot.edit_message_text(chat_id=callback.message.chat.id,
                                  message_id=callback.message.message_id,
                                  text="Выберите игру из списка:",
                                  reply_markup=get_list_own_game(own_game, user_id))
        else:
            bot.edit_message_text(chat_id=callback.message.chat.id,
                                  message_id=callback.message.message_id,
                                  text="У вас нет забронированных игр.",
                                  reply_markup=markup)

        bot.answer_callback_query(callback.id)

    except Exception as e:
        logger.error(f"При попытке отображения списка своих игр пользователем {user_id} возникла ошибка {e}")
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              text="Произошла ошибка при чтении данных.\nПопробуйте ещё раз.")
        bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('own game is'))
def confirm_delete(callback):
    game_id = callback.data.split("_")[1]
    user_id = callback.data.split("_")[2]
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text=f"Вы действительно хотите отменить эту бронь?",
                          reply_markup=confirm_delete_keys(game_id, user_id))
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('complited delete'))
def completed_delete(callback):

    game_id = callback.data.split("_")[1]
    user_id = callback.data.split("_")[2]

    def delete_game(session):
        game = session.query(BookKort).filter_by(id=game_id).first()
        if not game:
            raise ValueError(f"Игра с id={game_id} не найдена")
        game.canseled = True
        game.time_update = datetime.datetime.now()
        session.commit()
        return {
            "user": game.user,
            "time_start": game.time_start,
            "time_finish": game.time_finish
        }

    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{user_id}'))
        game = query_with_reconnect(delete_game)

        logger.info(f"{game['user']} отменил игру {game_id}")

        bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text="Вы отменили игру",
            reply_markup=markup
        )
        bot.answer_callback_query(callback.id)

        day = game['time_start'].date().strftime("%d.%m.%Y")
        time_start = game['time_start'].time().strftime("%H:%M")
        time_finish = game['time_finish'].time().strftime("%H:%M")

        bot.send_message(
            chat_id=CHAT_ID,
            text=f"❌ Отменена брони {day} c {time_start} до {time_finish}",
            message_thread_id=MESSAGE_THREAD_ID  # возможно понадобится если в группе есть topic
        )

    except Exception as e:
        logger.error(f"При попытке удаления игры {game_id} возникла ошибка: {e}")
        bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text="Произошла ошибка при удалении данных.\nПопробуйте ещё раз."
        )
        bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('list'))
def list_book(callback):
    user_id = callback.data.split("_")[1]
    bot.edit_message_text(chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              text="Выбери день:",
                              reply_markup=get_list_day(user_id=user_id, isInfo=True))
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('day_') and call.data.endswith('True'))
def list_book_day(callback):
    markup = types.InlineKeyboardMarkup()
    choice_day = callback.data.split("_")[1]
    user_id = callback.data.split("_")[2]
    day, month, year = map(int, choice_day.split('.'))
    time_start = datetime.datetime(year=year, month=month, day=day, hour=0, minute=0, second=0)
    if time_start < datetime.datetime.now():
        time_start = datetime.datetime.now()
    time_finish = datetime.datetime(year=year, month=month, day=day, hour=23, minute=0, second=0)

    def fetch_games(session):
        return session.query(BookKort).filter(
            BookKort.time_finish > time_start,
            BookKort.time_finish <= time_finish,
            BookKort.canseled == False
        ).order_by(BookKort.time_start).all()

    try:
        db_list_game = query_with_reconnect(fetch_games)

        if db_list_game:
            text = f"{choice_day} корт забронирован в следующее время: \n\n" + get_list_all_game(db_list_game)
        else:
            text = f"{choice_day} пока корт никто не бронировал"

        markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{user_id}_{day}'))
        bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text=text,
            reply_markup=markup
        )
        bot.answer_callback_query(callback.id)

    except Exception as e:
        logger.error(f"При попытке отображения списка игр возникла ошибка: {e}")
        bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text="Произошла ошибка при чтении данных.\nПопробуйте ещё раз."
        )
        bot.answer_callback_query(callback.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('statistic_'))
def statistica(callback):
    user_id = callback.data.split("_")[1]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{user_id}'))
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text="Введите период (ДД:ММ:ГГГГ-ДД:ММ:ГГГГ)")
    bot.answer_callback_query(callback.id)
    bot.register_next_step_handler(callback.message, check_date, user_id)

def check_date(message, user_id):

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{user_id}'))

    try:
        start, finish =  message.text.split('-')
        start = datetime.datetime.strptime(start, '%d:%m:%Y')
        finish = datetime.datetime.strptime(finish, '%d:%m:%Y')
        if finish < start:
            raise ValueError
        if finish.year < 2025 or start.year < 2025:
            raise ValueError

        def get_statistic(session):
            result = (
                session.query(
                    BookKort.user,
                    func.count(BookKort.id).label('total_count'),
                    func.sum(case((BookKort.canseled == True, 1), else_=0)).label('canceled_count')
                )
                .filter(BookKort.time_finish >= start, BookKort.time_finish <= finish)
                .group_by(BookKort.user_id)
                .all()
            )
            return result

        try:
            db_list_game = query_with_reconnect(get_statistic)
            text = (f"Статистика с {start.date().strftime('%d.%m.%Y')} до {finish.date().strftime('%d.%m.%Y')}: \n\n"
                    + get_list_statistic(db_list_game))

            bot.send_message(
                chat_id=message.chat.id,
                text=text,
                parse_mode='Markdown',
                reply_markup=markup
            )

        except Exception as e:
            logger.error(f"При попытке отображения списка игр возникла ошибка: {e}")
            bot.send_message(
                chat_id=message.chat.id,
                text="Произошла ошибка при чтении данных.\nПопробуйте ещё раз."
            )

    except ValueError:
        bot.send_message(chat_id=message.chat.id,
                         text='Введена не корректная дата. Для повторного ввода вернитесь "назад" ',
                         reply_markup=markup
                         )



@bot.callback_query_handler(func=lambda call: call.data.startswith('back'))
def back(callback):
    if callback.message.text in {"Выбери день:",
                                 'Выберите игру из списка:',
                                 'Вы отменили игру',
                                 "У вас нет забронированных игр.",
                                 'Введена не корректная дата. Для повторного ввода вернитесь "назад"'
                                 }:
        user_id = callback.data.split("_")[1]
        member = bot.get_chat_member(chat_id=CHAT_ID, user_id=callback.message.chat.id)
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              text="Привет! Вот чем я могу тебе помочь: ",
                              reply_markup=start_menu(user_id, member))
        bot.answer_callback_query(callback.id)
    if callback.message.text.startswith("Статистика с"):
        user_id = callback.data.split("_")[1]
        member = bot.get_chat_member(chat_id=CHAT_ID, user_id=callback.message.chat.id)
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              text="Привет! Вот чем я могу тебе помочь: ",
                              reply_markup=start_menu(user_id, member))
        bot.answer_callback_query(callback.id)
    if callback.message.text.endswith(("можете начать с:",
                                       "Корт успели забронировать чуть раньше вас",
                                       "есть бронь в этот день.")):
        book(callback)
    if callback.message.text.startswith("Вы забронировали корт"):
        book(callback)
    if callback.message.text.endswith("забронировать корт на:"):
        timedate(callback)
    if callback.message.text.startswith("Вы хотите "):
        free_time(callback)
    if callback.message.text.endswith("отменить эту бронь?"):
        delete(callback)
    if "корт забронирован в следующее время" in callback.message.text:
        list_book(callback)
    if "пока корт никто не бронировал" in callback.message.text:
        list_book(callback)

# раскомментировать при работе через WEBHHOK
# if __name__ == '__main__':
#     WEBHOOK_URL = 'https://' + TOKEN
#     bot.remove_webhook()
#     bot.set_webhook(url=WEBHOOK_URL)
#     app.run(host='0.0.0.0', port=5000)

"""Установка WEBHOOK почему-то не получалась. Задал через браузер при помощи API - telegram"""

bot.polling(none_stop=True) # закомментировать при работе через WEBHOOK

# раскомментировать при первом запуске для создания БД
# if __name__ == "__main__":
#     create_db()
#     app.run(debug=True)

