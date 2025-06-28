import datetime
import telebot
from flask_sqlalchemy import SQLAlchemy
from telebot import types

from flask import Flask, request

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://arsenyfk_telebot:book56&78kort@localhost/arsenyfk_telebot'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()
db.init_app(app)

def create_db():
    with app.app_context():
        db.create_all()

class BookKort(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(80), nullable=False)
    time_create = db.Column(db.DateTime, default=datetime.datetime.now)
    time_start = db.Column(db.DateTime, nullable=False)
    time_finish = db.Column(db.DateTime, nullable=False)

bot  = telebot.TeleBot('7812640866:AAEfsK7ftuOjvib5Pb6S8mW0gRivdnyZKYg')

@app.route('/' + '7812640866:AAEfsK7ftuOjvib5Pb6S8mW0gRivdnyZKYg', methods=['POST'])
def telegram_webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return '!', 200


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
    minutes_add = {'00:30':30, '01:00':60, '01:30':90, '02:00':120}
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
    query = db.session.query(BookKort).filter(time_start < BookKort.time_finish < time_finish)
    db_list_game = query.order_by(BookKort.time_start).all()
    time_book = set()
    if db_list_game:
        for column in db_list_game:
            time_start = datetime.datetime.strptime(column['time_start'], "%Y-%m-%d %H:%M:%S")
            time_finish = datetime.datetime.strptime(column['time_finish'], "%Y-%m-%d %H:%M:%S")
            while time_start < time_finish:
                time_book.add(time_start.time().strftime("%H:%M"))
                time_start += datetime.timedelta(minutes=30)

    return time_book


def get_list_time(day):
    markup = types.InlineKeyboardMarkup(row_width=3)
    time_book = get_time_book(day)
    start_hour = datetime.datetime.now().hour
    if start_hour < 6:
        start_hour = 6
    buttons = []
    for hour in range(start_hour, 22):
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
    time_book.update(("22:00", "22:30", "23:00"))
    markup.add(types.InlineKeyboardButton(f'30 минут', callback_data=f'during_00:30_{timer_start}_{day}'))
    time_start, time_check = create_time('00:30', timer_start, day)
    if time_check.time().strftime("%H:%M") not in time_book:
        markup.add(types.InlineKeyboardButton(f'1 час', callback_data=f'during_01:00_{timer_start}_{day}'))
    time_start, time_check = create_time('01:00', timer_start, day)
    if time_check.time().strftime("%H:%M") not in time_book:
        markup.add(types.InlineKeyboardButton(f'1 час 30 минут', callback_data=f'during_01:30_{timer_start}_{day}'))
    time_start, time_check = create_time('01:30', timer_start, day)
    if time_check.time().strftime("%H:%M") not in time_book:
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
        game_id = column['id']
        dt = datetime.datetime.strptime(column['time_start'], "%Y-%m-%d %H:%M:%S")
        day = dt.date().strftime("%d.%m.%Y")
        time_start = dt.time().strftime("%H:%M")
        dt = datetime.datetime.strptime(column['time_finish'], "%Y-%m-%d %H:%M:%S")
        time_finish = dt.time().strftime("%H:%M")
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
        user = column['user']
        time_start = datetime.datetime.strptime(column['time_start'], "%Y-%m-%d %H:%M:%S")
        time_start = time_start.time().strftime("%H:%M")
        time_finish = datetime.datetime.strptime(column['time_finish'], "%Y-%m-%d %H:%M:%S")
        time_finish = time_finish.time().strftime("%H:%M")
        text += f'{count}. {user} забронировал корт с {time_start} до {time_finish} \n'

    text += "\nЕсли хотите начать сначала введите команду /start"

    return text


@bot.message_handler(commands=['start'])
def main(message):
    bot.send_message(message.chat.id, "Привет! Вот чем я могу тебе помочь: ", reply_markup=start_menu())


@bot.callback_query_handler(func=lambda call: call.data =='book')
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
    during_dict = {'00:30':'30 минут', '01:00': '1 час', '01:30': '1 час 30 минут', '02:00': '2 часа'}
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text=f"Вы хотите {day} с {timer_start} забронировать корт на {during_dict[during_timer]}?",
                          reply_markup=confirm_keys(during_timer, timer_start, day))
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def complited_insert(callback):
    name, during_timer, timer_start, day = callback.data.split("_")
    user = callback.message.chat.username
    time_start, time_finish = create_time(during_timer, timer_start, day)
    try:
        new_note = BookKort(user=user, time_start=time_start, time_finish=time_finish)
        db.session.add(new_note)
        db.session.commit()
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              text=f"Вы забронировали корт. Если хотите начать сначала введите команду /start")
    except:
        db.session.rollback()
        print("Ошибка добавление в БД")
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              text=f"Произошла ошибка добавления записи.\n Попробуйте ещё раз.")
    finally:
        bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data =='delete')
def delete(callback):
    user = callback.message.chat.username
    try:
        query = db.session.query(BookKort).filter(BookKort.time_start > datetime.datetime.now, BookKort.user == user)
        own_game = query.order_by(BookKort.time_start).all()
        if own_game:
            bot.edit_message_text(chat_id=callback.message.chat.id,
                                  message_id=callback.message.message_id,
                                  text="Выберите игру из списка:",
                                  reply_markup=get_list_own_game(own_game))
        else:
            bot.edit_message_text(chat_id=callback.message.chat.id,
                                  message_id=callback.message.message_id,
                                  text="У вас нет забронированных игр. Если хотите начать сначала введите команду /start")
    except:
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              text="Произошла ошибка при чтении данных.\nПопробуйте ещё раз. ")
    finally:
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
        game = db.session.query(BookKort).filter_by(id=game_id).first()
        db.session.delete(game)
        db.session.commit()
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              text=f"Вы отменили игру. Если хотите начать сначала введите команду /start")
    except:
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              text=f"Произошла ошибка при удалении данных.\nПопробуйте ещё раз. ")
    finally:
        bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data =='list')
def list_book(callback):
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text="Выбери день:",
                          reply_markup=get_list_day(isInfo=True))
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('day_') and call.data.endswith('True'))
def list_book_day(callback):
    choice_day = callback.data.split("_")[1]
    day, month, year = map(int, choice_day.split('.'))
    time_start = datetime.datetime(year=year, month=month, day=day, hour=0, minute=0, second=0)
    if time_start < datetime.datetime.now():
        time_start = datetime.datetime.now()
    time_finish = datetime.datetime(year=year, month=month, day=day, hour=23, minute=0, second=0)
    try:
        query = db.session.query(BookKort).filter(time_start < BookKort.time_finish < time_finish)
        db_list_game = query.order_by(BookKort.time_start).all()
        if db_list_game:
            text = f"{choice_day} корт забронирован в следующее время: \n\n" + get_list_all_game(db_list_game)
        else:
            text = f"{choice_day} пока корт никто не бронировал \nЕсли хотите начать сначала введите команду /start"
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              text=text)
    except:
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              text="Произошла ошибка при чтении данных.\nПопробуйте ещё раз. ")
    finally:
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

bot.polling(none_stop=True)


if __name__ == "__main__":
    create_db()
    app.run(debug=True)

