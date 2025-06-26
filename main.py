import datetime
import telebot
import sqlite3
from telebot import types

days = {
    1: "Понедельник",
    2: "Вторник",
    3: "Среда",
    4: "Четверг",
    5: "Пятница",
    6: "Суббота",
    7: "Воскресенье"
}

bot  = telebot.TeleBot('7812640866:AAEfsK7ftuOjvib5Pb6S8mW0gRivdnyZKYg')

def start_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Посмотреть расписание', callback_data='list'))
    markup.add(types.InlineKeyboardButton('Забронировать корт', callback_data='book'))
    markup.add(types.InlineKeyboardButton('Отменить игру', callback_data='delete'))
    return markup

def get_list_day():
    markup = types.InlineKeyboardMarkup()
    today = datetime.date.today()
    for i in range(3):
        day_num = datetime.datetime.isoweekday(today)
        day_name = days[day_num]
        date_str = today.strftime("%d.%m.%Y")
        markup.add(types.InlineKeyboardButton(f'{date_str} ({day_name})', callback_data=f'day_{date_str}'))
        today += datetime.timedelta(days=1)
    markup.add(types.InlineKeyboardButton('Назад', callback_data='back'))
    return markup


def get_list_time(day):
    markup = types.InlineKeyboardMarkup()
    for hour in range(6, 22):
        btn1 = types.InlineKeyboardButton(f'{hour}:00', callback_data=f'time_{hour}:00_{day}')
        btn2 = types.InlineKeyboardButton(f'{hour}:30', callback_data=f'time_{hour}:30_{day}')
        markup.row(btn1, btn2)
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{day}'))
    return markup

def get_free_time(timer_start, day):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f'30 минут', callback_data=f'during_00:30_{timer_start}_{day}'))
    markup.add(types.InlineKeyboardButton(f'1 час', callback_data=f'during_01:00_{timer_start}_{day}'))
    markup.add(types.InlineKeyboardButton(f'1 час 30 минут', callback_data=f'during_01:30_{timer_start}_{day}'))
    markup.add(types.InlineKeyboardButton(f'2 часа', callback_data=f'during_02:00_{timer_start}_{day}'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{day}'))
    return markup

def confirm_keys(during_timer, timer_start, day):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f'Да', callback_data=f'confirm_{during_timer}_{timer_start}_{day}'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'back_{timer_start}_{day}'))
    return markup

@bot.message_handler(commands=['start'])
def main(message):
    bot.send_message(message.chat.id, "Привет! Вот чем я могу тебе помочь: ", reply_markup=start_menu())

@bot.callback_query_handler(func=lambda call: call.data =='book')
def book(callback):
    bot.send_message(callback.message.chat.id, "Выбери день:", reply_markup=get_list_day())

@bot.callback_query_handler(func=lambda call: call.data.startswith('day_'))
def timedate(callback):
    day = callback.data.split("_")[1]
    bot.send_message(callback.message.chat.id, f"{day} вы можете начать с:", reply_markup=get_list_time(day))

@bot.callback_query_handler(func=lambda call: call.data.startswith('time_'))
def free_time(callback):
    name, timer_start, day = callback.data.split("_")
    bot.send_message(callback.message.chat.id, f"Сколько вы хотите играть?", reply_markup=get_free_time(timer_start, day))

@bot.callback_query_handler(func=lambda call: call.data.startswith('during_'))
def during(callback):
    name, during_timer, timer_start, day = callback.data.split("_")
    bot.send_message(callback.message.chat.id, f"Вы хотите {day} с {timer_start} забронировать корт на {during_timer}?",
                     reply_markup=confirm_keys(during_timer, timer_start, day))

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def confirm(callback):
    bot.send_message(callback.message.chat.id, f"Вы забронировали корт. Если хотите начать сначала введите команду /start")


@bot.callback_query_handler(func=lambda call: call.data.startswith('back'))
def back(callback):
    if callback.message.text == "Выбери день:":
        main(callback.message)
    if callback.message.text.endswith("можете начать с:"):
        book(callback)
    if callback.message.text.endswith("вы хотите играть?"):
        timedate(callback)
    if callback.message.text.startswith("Вы хотите "):
        free_time(callback)






bot.polling(none_stop=True)

# conn = sqlite3.connect('tennis.sqlite3')
# cur = conn.cursor()
# cur.execute('CREATE TABLE IF NOT EXISTS bookKORT(id INT AUTO_INCREMENT PRIMARY KEY, \
#                                 user VARCHAR(30), \
#                                 time_create DATETIME,\
#                                 time_start DATETIME,\
#                                 time_finish DATETIME)')
# conn.commit()
# cur.close()
# conn.close()



# print(callback.from_user.username)
#
# conn = sqlite3.connect('tennis.sqlite3')
# cur = conn.cursor()
# cur.execute(
#     f'INSERT INTO bookKORT VALUES (COUNT(), "arseni", CURRENT_TIMESTAMP, "2025-03-11 11-20", "2025-03-11 13-20")')
# conn.commit()
# cur.close()
# conn.close()

def hours_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=6)
    buttons = [types.InlineKeyboardButton(text=str(h), callback_data=f"hour_{h}") for h in range(24)]
    markup.add(*buttons)
    return markup

def minutes_keyboard(selected_hour):
    markup = types.InlineKeyboardMarkup(row_width=4)
    minutes = [0, 15, 30, 45]
    buttons = [types.InlineKeyboardButton(text=f"{m:02}", callback_data=f"minute_{selected_hour}_{m}") for m in minutes]
    markup.add(*buttons)
    return markup

@bot.message_handler(commands=['time'])
def choose_time(message):
    bot.send_message(message.chat.id, "Выберите час:", reply_markup=hours_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('hour_'))
def choose_minutes(call):
    hour = int(call.data.split('_')[1])
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=f"Выбран час: {hour}. Выберите минуты:",
                          reply_markup=minutes_keyboard(hour))
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('minute_'))
def confirm_time(call):
    _, hour, minute = call.data.split('_')
    time_str = f"{int(hour):02}:{int(minute):02}"
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=f"Вы выбрали время: {time_str}")
    bot.answer_callback_query(call.id)