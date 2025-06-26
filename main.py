import datetime
import telebot
from telebot import types

from database import add_note, get_my_game, delete_note

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


@bot.message_handler(commands=['start'])
def main(message):
    bot.send_message(message.chat.id, "Привет! Вот чем я могу тебе помочь: ", reply_markup=start_menu())


@bot.callback_query_handler(func=lambda call: call.data =='book')
def book(callback):
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text="Выбери день:",
                          reply_markup=get_list_day())
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('day_'))
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
                          text=f"Сколько вы хотите играть?",
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
    add_note(user, time_start, time_finish)
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text=f"Вы забронировали корт. Если хотите начать сначала введите команду /start")
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data =='delete')
def delete(callback):
    print(callback.data)
    user = callback.message.chat.username
    own_game = get_my_game(user)
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


@bot.callback_query_handler(func=lambda call: call.data.startswith('own game is'))
def confirm_delete(callback):
    print(callback.data)
    game_id = callback.data.split("_")[1]
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text=f"Вы действительно хотите отменить эту бронь?",
                          reply_markup=confirm_delete_keys(game_id))
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('complited delete'))
def completed_delete(callback):
    print(callback.data)
    game_id = callback.data.split("_")[1]
    delete_note(game_id)
    bot.edit_message_text(chat_id=callback.message.chat.id,
                          message_id=callback.message.message_id,
                          text=f"Вы отменили игру. Если хотите начать сначала введите команду /start")
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
    if callback.message.text.endswith("вы хотите играть?"):
        timedate(callback)
    if callback.message.text.startswith("Вы хотите "):
        free_time(callback)
    if callback.message.text.endswith("отменить эту бронь?"):
        delete(callback)

bot.polling(none_stop=True)


