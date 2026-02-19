import logging
from datetime import datetime, timedelta

from app.bot.dao import BookKortDAO
from app.bot.models import BookKort

days = {
    1: "Понедельник",
    2: "Вторник",
    3: "Среда",
    4: "Четверг",
    5: "Пятница",
    6: "Суббота",
    7: "Воскресенье"
}


def check_username(username, fullname):
    if username:
        return '@' + username
    else:
        return fullname


def create_time(during_timer, timer_start, day):
    day, month, year = map(int, day.split("."))
    hour, minute = map(int, timer_start.split(':'))
    time_start = datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=0)
    minutes_add = {'00:30': 30, '01:00': 60, '01:30': 90, '02:00': 120}
    time_finish = time_start + timedelta(minutes=minutes_add[during_timer])
    return time_start, time_finish


async def get_time_book(choice_day):
    day, month, year = map(int, choice_day.split('.'))
    time_start = datetime(year=year, month=month, day=day, hour=0, minute=0, second=0)
    if time_start < datetime.now():
        time_start = datetime.now()
    time_finish = datetime(year=year, month=month, day=day, hour=23, minute=0, second=0)

    try:
        notes = await BookKortDAO.find_all_filter(BookKort.time_start,
                                                   BookKort.time_finish > time_start,
                                                  BookKort.time_finish <= time_finish,
                                                   BookKort.canceled == False)
        time_book = set()
        if notes:
            for column in notes:
                start = column.time_start
                finish = column.time_finish
                while start < finish:
                    time_book.add(start.time().strftime("%H:%M"))
                    start += timedelta(minutes=30)
        return time_book

    except Exception as e:
        logging.error(f"При попытке получить забронированное время возникла ошибка {e}")


def get_list_all_game(res):
    text = ''
    count = 0
    for column in res:
        count += 1
        user = check_username(column.user.username, column.user.full_name)
        time_start = column.time_start.time().strftime("%H:%M")
        time_finish = column.time_finish.time().strftime("%H:%M")
        game_id = column.bookkort_id
        text += f'{count}. С {time_start} до {time_finish} ({user}) ({game_id})\n'
    return text


def get_list_statistic(res):
    lines = []
    header = f'{"№":<4}|{"Имя пользователя":<20}|{"ID":<15}|{"всего":>5}|{"отм.":>5}'
    separator = '-' * (4 + 1 + 20 + 15 + 1 + 5 + 1 + 5)
    lines.append(header)
    lines.append(separator)
    for i, (username, full_name, user_id, total, canceled) in enumerate(res, 1):
        user = check_username(username, full_name)
        lines.append(f'{i:<4} {user:<20} {user_id:<15} {total:>5} {canceled:>5}')
    table_text = '\n'.join(lines)
    return f'```\n{table_text}\n```'


def get_black_list(res):
    lines = ['Cписок:',]
    header = f'{"№":<4}|{"Имя":<20}|{"ID":<12}|{"начало":>10}|{"конец":>10}|'
    separator = '-' * (4 + 1 + 20 + 12 + 1 + 10 + 1 + 10)
    lines.append(header)
    lines.append(separator)
    for column in res:
        user = check_username(column.user.username, column.user.full_name)
        lines.append(f'{column.blacklist_id:<4} {user:<20} {column.user_id:<12} '
                     f'{column.time_start.strftime("%d.%m.%Y"):>5} '
                     f'{column.time_finish.strftime("%d.%m.%Y"):>5}')
    table_text = '\n'.join(lines)
    return f'```\n{table_text}\n```'
