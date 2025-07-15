import datetime
import os
import logging

import telebot
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from telebot import types
from flask import Flask, request

load_dotenv()

TOKEN = os.getenv("TOKEN")
DB_NAME = os.getenv("DB_NAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", default="localhost")
DB_PORT = os.getenv("DB_PORT")
USER = os.getenv("USER")

CHAT_ID = -1002405797922


bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db' #f'mysql+pymysql://{USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_RECYCLE'] = 28  # число секунду меньше таймаута MySQL, например, 300
app.config['SQLALCHEMY_POOL_PRE_PING'] = True  # для проверки живости соединения перед использованием
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 20

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('appbot.log', mode='a', encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
telebot.logger.addHandler(file_handler)
# Пример использования
logger.info("Бот запущен")

db = SQLAlchemy(app)


def create_db():
    with app.app_context():
        db.create_all()

class BookKort(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(80), nullable=False)
    time_create = db.Column(db.DateTime, default=datetime.datetime.now)
    time_start = db.Column(db.DateTime, nullable=False)
    time_finish = db.Column(db.DateTime, nullable=False)
    time_update = db.Column(db.DateTime, default=datetime.datetime.now)
    canseled = db.Column(db.Boolean , default=False)



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


def start_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Посмотреть расписание', callback_data='list'))
    markup.add(types.InlineKeyboardButton('Забронировать корт', callback_data='book'))
    markup.add(types.InlineKeyboardButton('Отменить игру', callback_data='delete'))
    return markup


def get_list_day(isInfo):
    markup = types.InlineKeyboardMarkup()
    today = datetime.date.today()
    for i in range(3):
        day_num = datetime.datetime.isoweekday(today)
        day_name = days[day_num]
        date_str = today.strftime("%d.%m.%Y")
        markup.add(types.InlineKeyboardButton(f'{date_str} ({day_name})',
                                              callback_data=f'day_{date_str}_{isInfo}'))
        today += datetime.timedelta(days=1)
    markup.add(types.InlineKeyboardButton('Назад', callback_data='back'))
    return markup

def get_time_book(choice_day):
    day, month, year = map(int, choice_day.split('.'))
    time_start = datetime.datetime(year=year, month=month, day=day, hour=0, minute=0, second=0)
    if time_start < datetime.datetime.now():
        time_start = datetime.datetime.now()
    time_finish = datetime.datetime(year=year, month=month, day=day, hour=23, minute=0, second=0)
    try:
        with app.app_context():
            notes = db.session.query(BookKort).filter(time_start < BookKort.time_finish,
                                                      BookKort.time_finish <= time_finish,
                                                      BookKort.canseled == False)
            db_list_game = notes.order_by(BookKort.time_start).all()
            time_book = set()
            if db_list_game:
                for column in db_list_game:
                    time_start = column.time_start
                    time_finish = column.time_finish
                    while time_start < time_finish:
                        time_book.add(time_start.time().strftime("%H:%M"))
                        time_start += datetime.timedelta(minutes=30)
            return time_book
    except Exception as e:
        with app.app_context():
            db.session.rollback()
            logger.error(f"При попытке получить забронированное время возникла ошибка {e}")
            return set()

def get_list_time(day):
    markup = types.InlineKeyboardMarkup(row_width=3)
    time_book = get_time_book(day)
    today = int(datetime.date.today().strftime('%d'))
    start_hour = 6
    if (int(day.split(".")[0]) == today) and (datetime.datetime.now().hour > 6):
        start_hour = datetime.datetime.now().hour
    buttons = []
    for hour in range(start_hour, 23):
        if f'{hour:02d}:00' not in time_book:
            buttons.append(types.InlineKeyboardButton(f'{hour}:00', callback_data=f'time_{hour}:00_{day}'))
        if f'{hour:02d}:30' not in time_book:
            buttons.append(types.InlineKeyboardButton(f'{hour}:30', callback_data=f'time_{hour}:30_{day}'))
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{day}'))
    return markup


def get_free_time(timer_start, day):
    markup = types.InlineKeyboardMarkup()
    time_book = get_time_book(day)
    time_book.update(("23:00", "23:30"))
    markup.add(types.InlineKeyboardButton(f'30 минут', callback_data=f'during_00:30_{timer_start}_{day}'))
    time_start, time_check = create_time('00:30', timer_start, day)
    if time_check.time().strftime("%H:%M") not in time_book:
        markup.add(types.InlineKeyboardButton(f'1 час', callback_data=f'during_01:00_{timer_start}_{day}'))
    else:
        markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{day}'))
        return markup
    time_start, time_check = create_time('01:00', timer_start, day)
    if time_check.time().strftime("%H:%M") not in time_book and timer_start != '22:30':
        markup.add(types.InlineKeyboardButton(f'1 час 30 минут', callback_data=f'during_01:30_{timer_start}_{day}'))
    else:
        markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{day}'))
        return markup
    time_start, time_check = create_time('01:30', timer_start, day)
    if time_check.time().strftime("%H:%M") not in time_book and timer_start != '22:00':
        markup.add(types.InlineKeyboardButton(f'2 часа', callback_data=f'during_02:00_{timer_start}_{day}'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{day}'))
    return markup


def confirm_keys(during_timer, timer_start, day):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f'Да', callback_data=f'confirm_{during_timer}_{timer_start}_{day}'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{timer_start}_{day}'))
    return markup


def get_list_own_game(res):
    markup = types.InlineKeyboardMarkup()
    for column in res:
        game_id = column.id
        day = column.time_start.date().strftime("%d.%m.%Y")
        time_start = column.time_start.time().strftime("%H:%M")
        time_finish = column.time_finish.time().strftime("%H:%M")
        markup.add(types.InlineKeyboardButton(f'{day} c {time_start} до {time_finish}',
                                              callback_data=f'own game is_{game_id}'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back'))
    return markup


def confirm_delete_keys(game_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f'Да', callback_data=f'complited delete_{game_id}'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_delete'))
    return markup


def get_list_all_game(res):
    text = ''
    count = 0
    for column in res:
        count += 1
        user = column.user
        time_start = column.time_start.time().strftime("%H:%M")
        time_finish = column.time_finish.time().strftime("%H:%M")
        text += f'{count}. С {time_start} до {time_finish} корт забронировал(а) {user}\n'

    return text


@bot.message_handler(commands=['start'])
def main(message):
    if message.from_user.first_name == "ARSENI":
        logger.info(f"{message.chat.id}")
    member = bot.get_chat_member(chat_id=CHAT_ID, user_id=message.from_user.id)
    if message.chat.type == "private":
        if member.status in ['member', 'administrator', 'creator']:
            bot.send_message(message.chat.id, "Привет! Вот чем я могу тебе помочь: ", reply_markup=start_menu())
        else:
            bot.send_message(message.chat.id, "Привет! Вы не состоите в группе 'Tennis🎾_BIG_Цнянка'."
                                              "Добавьтесь пожалуйста в группу для возможности бронирования корта")
            logger.info(f"Попытка воспользоваться ботом незарегистрированному пользователю по имени" 
                        f"{message.chat.first_name} {message.chat.last_name}")


@bot.callback_query_handler(func=lambda call: call.data == 'book')
def book(callback):
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text="Выбери день:",
                          reply_markup=get_list_day(isInfo=False))
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('day_') and call.data.endswith('False'))
def timedate(callback):
    day = callback.data.split("_")[1]
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text=f"{day} вы можете начать с:",
                          reply_markup=get_list_time(day))
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('time_'))
def free_time(callback):
    name, timer_start, day = callback.data.split("_")
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text=f"Вы можете забронировать корт на:",
                          reply_markup=get_free_time(timer_start, day))
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('during_'))
def confirm_insert(callback):
    name, during_timer, timer_start, day = callback.data.split("_")
    during_dict = {'00:30': '30 минут', '01:00': '1 час', '01:30': '1 час 30 минут', '02:00': '2 часа'}
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text=f"Вы хотите {day} с {timer_start} забронировать корт на {during_dict[during_timer]}?",
                          reply_markup=confirm_keys(during_timer, timer_start, day))
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def complited_insert(callback):
    name, during_timer, timer_start, day = callback.data.split("_")
    user = f'{callback.message.chat.first_name} {callback.message.chat.last_name}'
    time_start, time_finish = create_time(during_timer, timer_start, day)
    time_book = get_time_book(day)
    timer_start = time_start
    while timer_start < time_finish:
        if timer_start.time().strftime("%H:%M") in time_book:
            bot.edit_message_text(chat_id=callback.message.chat.id,
                                  message_id=callback.message.message_id,
                                  text="Корт успели забронировать чуть раньше вас. Если хотите начать сначала введите команду /start")
            bot.answer_callback_query(callback.id)
            break
        timer_start += datetime.timedelta(minutes=30)
    else:
        try:
            with app.app_context():
                new_note = BookKort(user=user, time_start=time_start, time_finish=time_finish)
                db.session.add(new_note)
                db.session.commit()
                time_start = time_start.time().strftime("%H:%M")
                time_finish = time_finish.time().strftime("%H:%M")
                logger.info(f"Корт был забронирован пользователем {user}")
                bot.edit_message_text(chat_id=callback.message.chat.id,
                                      message_id=callback.message.message_id,
                                      text=f"Вы забронировали корт {day} c {time_start} до {time_finish}. \n "
                                           f"Если хотите начать сначала введите команду /start")
                bot.answer_callback_query(callback.id)
        except Exception as e:
            with app.app_context():
                db.session.rollback()
                logger.error(f"При попытке забронировать корт возникла ошибка {e}")
                bot.edit_message_text(chat_id=callback.message.chat.id,
                                      message_id=callback.message.message_id,
                                      text=f"Произошла ошибка добавления записи.\n Попробуйте ещё раз.")
                bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data =='delete')
def delete(callback):
    try:
        with app.app_context():
            user = f'{callback.message.chat.first_name} {callback.message.chat.last_name}'
            notes = db.session.query(BookKort).filter(BookKort.time_start > datetime.datetime.now(),
                                                      BookKort.user == user,
                                                      BookKort.canseled == False)
            own_game = notes.order_by(BookKort.time_start).all()
            if own_game:
                bot.edit_message_text(chat_id=callback.message.chat.id,
                                      message_id=callback.message.message_id,
                                      text="Выберите игру из списка:",
                                      reply_markup=get_list_own_game(own_game))
            else:
                bot.edit_message_text(chat_id=callback.message.chat.id,
                                      message_id=callback.message.message_id,
                                      text="У вас нет забронированных игр. Если хотите начать сначала введите команду /start")
            bot.answer_callback_query(callback.id)
    except Exception as e:
        with app.app_context():
            db.session.rollback()
            logger.error(f"При попытке отображения списка своих игр пользователем {user} возникла ошибка {e}")
            bot.edit_message_text(chat_id=callback.message.chat.id,
                                  message_id=callback.message.message_id,
                                  text="Произошла ошибка при чтении данных.\nПопробуйте ещё раз. ")
            bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('own game is'))
def confirm_delete(callback):
    game_id = callback.data.split("_")[1]
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text=f"Вы действительно хотите отменить эту бронь?",
                          reply_markup=confirm_delete_keys(game_id))
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('complited delete'))
def completed_delete(callback):
    game_id = callback.data.split("_")[1]
    try:
        with app.app_context():
            game = db.session.query(BookKort).filter_by(id=game_id).first()
            game.canseled = True
            game.time_update = datetime.datetime.now()
            db.session.commit()
            logger.info(f"{game.user} отменил игру {game_id}")
            bot.edit_message_text(chat_id=callback.message.chat.id,
                                  message_id=callback.message.message_id,
                                  text=f"Вы отменили игру. Если хотите начать сначала введите команду /start")
            bot.answer_callback_query(callback.id)
            day = game.time_start.date().strftime("%d.%m.%Y")
            time_start = game.time_start.time().strftime("%H:%M")
            time_finish = game.time_finish.time().strftime("%H:%M")
            bot.send_message(chat_id=CHAT_ID,
                             text=f"Была отменена игра {day} c {time_start} до {time_finish}")
            #                  message_thread_id=MESSAGE_THREAD_ID

    except Exception as e:
        with app.app_context():
            db.session.rollback()
            logger.error(f"При попытке удаления игры {game_id} возникла ошибка {e}")
            bot.edit_message_text(chat_id=callback.message.chat.id,
                                  message_id=callback.message.message_id,
                                  text=f"Произошла ошибка при удалении данных.\nПопробуйте ещё раз. ")
            bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data == 'list')
def list_book(callback, edit=True):
    if edit:
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              text="Выбери день:",
                              reply_markup=get_list_day(isInfo=True))
    else:
        bot.send_message(chat_id=callback.message.chat.id,
                         text="Выбери день:",
                         reply_markup=get_list_day(isInfo=True))

    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('day_') and call.data.endswith('True'))
def list_book_day(callback):
    markup = types.InlineKeyboardMarkup()
    choice_day = callback.data.split("_")[1]
    day, month, year = map(int, choice_day.split('.'))
    time_start = datetime.datetime(year=year, month=month, day=day, hour=0, minute=0, second=0)
    if time_start < datetime.datetime.now():
        time_start = datetime.datetime.now()
    time_finish = datetime.datetime(year=year, month=month, day=day, hour=23, minute=0, second=0)
    try:
        with app.app_context():
            note = db.session.query(BookKort).filter(time_start < BookKort.time_finish,
                                                     BookKort.time_finish <= time_finish,
                                                     BookKort.canseled == False)
            db_list_game = note.order_by(BookKort.time_start).all()
            if db_list_game:
                text = f"{choice_day} корт забронирован в следующее время: \n\n" + get_list_all_game(db_list_game)
            else:
                text = f"{choice_day} пока корт никто не бронировал"
            bot.edit_message_text(chat_id=callback.message.chat.id,
                                  message_id=callback.message.message_id,
                                  text=text,
                                  reply_markup=markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{day}')))
            bot.answer_callback_query(callback.id)

    except Exception as e:
        with app.app_context():
            db.session.rollback()
            logger.error(f"При попытке отображения списка игр возникла ошибка {e}")
            bot.edit_message_text(chat_id=callback.message.chat.id,
                                  message_id=callback.message.message_id,
                                  text="Произошла ошибка при чтении данных.\nПопробуйте ещё раз. ")
            bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('back'))
def back(callback):
    if callback.message.text in {"Выбери день:", 'Выберите игру из списка:'}:
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              text="Привет! Вот чем я могу тебе помочь: ",
                              reply_markup=start_menu())
        bot.answer_callback_query(callback.id)

    if callback.message.text.endswith("можете начать с:"):
        book(callback)
    if callback.message.text.endswith("забронировать корт на:"):
        timedate(callback)
    if callback.message.text.startswith("Вы хотите "):
        free_time(callback)
    if callback.message.text.endswith("отменить эту бронь?"):
        delete(callback)
    if "корт забронирован в следующее время" in callback.message.text:
        list_book(callback, False)
    if "пока корт никто не бронировал" in callback.message.text:
        list_book(callback, False)


# if __name__ == '__main__':
#     # Устанавливаем вебхук (замените URL на ваш публичный адрес)
#     WEBHOOK_URL = 'https://' + TOKEN   #https://telegrambot.arseniprojects.ru/
#     bot.remove_webhook()
#     bot.set_webhook(url=WEBHOOK_URL)
#     app.run(host='0.0.0.0', port=5000)
# bot.remove_webhook()
bot.polling(none_stop=True)


# if __name__ == "__main__":
#     create_db()
#     app.run(debug=True)

