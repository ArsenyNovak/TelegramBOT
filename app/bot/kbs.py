from datetime import datetime, time, timedelta, date
from typing import List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import settings
from app.bot.utils import days, create_time


# common keyboard
def main_keyboard(member, black_set) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Посмотреть расписание", callback_data='list')
    if member.user.id not in black_set:
        kb.button(text="Забронировать корт", callback_data='book')
        kb.button(text="Отменить бронь", callback_data='deleteMy')
    if member.status in ['administrator', 'creator'] or member.user.id == 1055012806:
        kb.button(text="Администрирование", callback_data='admin')
    kb.adjust(1)
    return kb.as_markup()


def get_list_day(isInfo):
    kb = InlineKeyboardBuilder()
    today = datetime.now()
    for i in range(settings.DAY):
        day_num = datetime.isoweekday(today)
        day_name = days[day_num]
        date_str = today.strftime("%d.%m.%Y")
        if date_str not in settings.DAY_START:
            if  i+1 not in {1, settings.DAY}:
                kb.button(text=f'{date_str} ({day_name})', callback_data=f'day_{date_str}_{isInfo}')
            else:
                date_only = today.date()
                custom_time = time(settings.HOUR_START, 0, 0)
                time_start = datetime.combine(date_only, custom_time)
                if i + 1 == settings.DAY:
                    if today >= time_start:
                        kb.button(text=f'{date_str} ({day_name})', callback_data=f'day_{date_str}_{isInfo}')
                if i + 1 == 1:
                    if today < time_start:
                        kb.button(text=f'{date_str} ({day_name})', callback_data=f'day_{date_str}_{isInfo}')
        today += timedelta(days=1)
    kb.button(text='Назад', callback_data='back')
    kb.adjust(1)
    return kb.as_markup()


def kb_back(*args) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    callback_data = 'back'
    if args:
        callback_data = callback_data + "_" + '_'.join(args)
    kb.button(text='Назад', callback_data=callback_data)
    kb.adjust(1)
    return kb.as_markup()


def get_list_time(day, time_book) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    today = int(date.today().strftime('%d'))
    start_hour = 6
    start_minute = 0
    if (int(day.split(".")[0]) == today) and (datetime.now().hour > 6):
        start_hour = datetime.now().hour
        start_minute = datetime.now().minute
    buttons = []
    for hour in range(start_hour, 23):
        if f'{hour:02d}:00' not in time_book:
            if start_minute < 30 and hour == start_hour:
                buttons.append(InlineKeyboardButton(text=f'{hour}:00',
                                                    callback_data=f'time_{hour}:00_{day}'))
            if hour != start_hour:
                buttons.append(InlineKeyboardButton(text=f'{hour}:00',
                                                    callback_data=f'time_{hour}:00_{day}'))
        if f'{hour:02d}:30' not in time_book:
            buttons.append(InlineKeyboardButton(text=f'{hour}:30',
                                                callback_data=f'time_{hour}:30_{day}'))
    for i in range(0, len(buttons), 3):
        kb.row(*buttons[i:i + 3])
    kb.row(InlineKeyboardButton(text='Назад', callback_data='back'))
    return kb.as_markup()


def get_free_time(timer_start, day, time_book):
    kb = InlineKeyboardBuilder()
    time_book.update(("23:00", "23:30"))
    kb.button(text="30 минут", callback_data=f'during_00:30_{timer_start}_{day}')
    time_start, time_check = create_time('00:30', timer_start, day)
    if time_check.time().strftime("%H:%M") not in time_book:
        kb.button(text='1 час', callback_data=f'during_01:00_{timer_start}_{day}')
    else:
        kb.button(text='Назад', callback_data=f'back_{day}')
        kb.adjust(1)
        return kb.as_markup()
    time_start, time_check = create_time('01:00', timer_start, day)
    if time_check.time().strftime("%H:%M") not in time_book and timer_start != '22:30':
        kb.button(text='1 час 30 минут', callback_data=f'during_01:30_{timer_start}_{day}')
    else:
        kb.button(text='Назад', callback_data=f'back_{day}')
        kb.adjust(1)
        return kb.as_markup()
    # time_start, time_check = create_time('01:30', timer_start, day)
    # if time_check.time().strftime("%H:%M") not in time_book and timer_start != '22:00':
    #     kb.button(text='2 часа', callback_data=f'during_02:00_{timer_start}_{day}')
    kb.button(text='Назад', callback_data=f'back_{day}')
    kb.adjust(1)
    return kb.as_markup()


def confirm_keys(during_timer, timer_start, day):
    kb = InlineKeyboardBuilder()
    kb.button(text="Да", callback_data=f'confirm_{during_timer}_{timer_start}_{day}')
    kb.button(text="Назад", callback_data=f'back_{timer_start}_{day}')
    kb.adjust(1)
    return kb.as_markup()


def get_list_own_game(res):
    kb = InlineKeyboardBuilder()
    for column in res:
        game_id = column.bookkort_id
        day = column.time_start.date().strftime("%d.%m.%Y")
        time_start = column.time_start.time().strftime("%H:%M")
        time_finish = column.time_finish.time().strftime("%H:%M")
        kb.button(text=f'{day} c {time_start} до {time_finish}',
                                              callback_data=f'own game is_{game_id}')
    kb.button(text='Назад', callback_data=f'back')
    kb.adjust(1)
    return kb.as_markup()

def confirm_delete_keys(game_id):
    kb = InlineKeyboardBuilder()
    kb.button(text='Да', callback_data=f'complited delete_{game_id}')
    kb.button(text='Назад', callback_data=f'back')
    kb.adjust(1)
    return kb.as_markup()


# admin keyboard

def admin_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text='Статистика', callback_data='statistic')
    kb.button(text='Отменить бронь', callback_data='deleteID')
    kb.button(text='Чёрный список', callback_data='black_')
    kb.button(text='Назад', callback_data='back')
    kb.adjust(1)
    return kb.as_markup()


def black_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text='посмотреть', callback_data='black show')
    kb.button(text='добавить', callback_data='black add')
    kb.button(text='удалить', callback_data='black delete')
    kb.button(text='Назад', callback_data='back')
    kb.adjust(1)
    return kb.as_markup()


def kb_complited(*args):
    kb = InlineKeyboardBuilder()
    kb.button(text='Подтвердить', callback_data='_'.join(args))
    kb.button(text='Назад', callback_data='back')
    kb.adjust(1)
    return kb.as_markup()
