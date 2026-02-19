from datetime import date, datetime, timedelta
import logging

from aiogram import Router, F, types
from aiogram.filters import CommandStart, JOIN_TRANSITION, ChatMemberUpdatedFilter
from aiogram.types import Message, ChatMemberUpdated
from sqlalchemy import func

from app.bot.admin_router import administration, black
from app.bot.create_bot import bot
from app.bot.dao import UserDAO, BookKortDAO, BlackListDAO
from app.bot.kbs import main_keyboard, get_list_day, kb_back, get_list_time, get_free_time, confirm_keys, \
    get_list_own_game, confirm_delete_keys
from app.bot.models import BookKort, BlackList
from app.bot.utils import get_time_book, create_time, get_list_all_game
from app.config import settings

MEMBER_EXCEPTION = {}

MESSAGE_THREAD_ID = 2

user_router = Router()


@user_router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def bot_added_to_group(event: ChatMemberUpdated):
    chat = event.chat
    logging.info(f"Бот был добавлен в группу: {chat.title}, ID чата: {chat.id}")
    await bot.send_message(
        settings.ADMIN_ID,
        f"Бот был добавлен в группу:\nНазвание: {chat.title}\nID чата: {chat.id}"
    )

@user_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    Обрабатывает команду /start.
    """
    # logging.info(f"{message.message_thread_id}")
    # logging.info(f"{message.chat.id}")
    member = await bot.get_chat_member(chat_id=settings.CHAT_ID, user_id=message.from_user.id)
    if message.chat.type == "private":
        if member.status in ['administrator', 'creator', 'member'] or member.user.id in MEMBER_EXCEPTION:
            try:
                user = await UserDAO.find_one_or_none(telegram_id=message.from_user.id)

                if not user:
                    logging.info(f"Добавлен новый участник: {message.from_user.full_name}")
                    await UserDAO.add(
                        telegram_id=message.from_user.id,
                        full_name=message.from_user.full_name,
                        username=message.from_user.username
                    )

                black_set = set()
                try:
                    notes = await BlackListDAO.find_all_filter(None,
                                                               BlackList.time_finish > datetime.now(),
                                                               BlackList.canceled == False)
                    if notes:
                        for note in notes:
                            black_set.add(note.user_id)

                    if member.status in ['administrator', 'creator'] or member.user.id == 1055012806:
                        await message.answer("Привет! Вот чем я могу тебе помочь: ",
                                             reply_markup=main_keyboard(member, black_set))
                    else:
                        await message.answer("Привет! Вот чем я могу тебе помочь: ",
                                             reply_markup=main_keyboard(member, black_set), protect_content=True)
                except Exception as e:
                    logging.error(f"При попытке загрузить чёрный список возникла ошибка: {e}")
                    await message.answer("Произошла ошибка при вхождении.\n Попробуйте ещё раз.")

            except Exception as e:
                logging.error(f"При попытке зарегистрироваться возникла ошибка: {e}")
                await message.answer("Произошла ошибка при вхождении.\n Попробуйте ещё раз.")

        else:
            logging.info(f"Попытка воспользоваться ботом незарегистрированному пользователю "
                         f"по имени {message.from_user.full_name}")
            await message.answer("Привет! Вы не состоите в группе 'Tennis🎾_BIG_Цнянка'."
                                              "Добавьтесь пожалуйста в группу для возможности бронирования корта",
                                 protect_content=True)


@user_router.callback_query(F.data.startswith('book'))
async def book(callback: types.CallbackQuery):
    """
        Обрабатывает кнопку "Забронировать корт"
    """
    await callback.message.edit_text(text="Выбери день:", reply_markup=get_list_day(isInfo=False))
    await callback.answer()


@user_router.callback_query(F.data.startswith('day_') and F.data.endswith('False'))
async def timedate(callback: types.CallbackQuery):
    day = callback.data.split("_")[1]
    day_date = date(*list(map(int, day.split('.')[::-1])))

    try:
        new_note = await BookKortDAO.find_all_filter(None,
                                                     func.DATE(BookKort.time_start) == day_date,
                                                     BookKort.user_id == callback.from_user.id,
                                                     BookKort.canceled == False
                                                     )
        if new_note:
            logging.info(f"Попытка сделать вторую бронь в один день ")
            await callback.message.edit_text(text="У вас уже есть бронь в этот день.",
                                             reply_markup=kb_back())
        else:
            time_book = await get_time_book(day)
            if time_book is None:
                await callback.message.edit_text(text='При попытке получить забронированное время возникла ошибка.'
                                                      '\nПопробуйте ещё раз.')
            else:
                await callback.message.edit_text(text=f"{day} вы можете начать с:",
                                                 reply_markup=get_list_time(day,time_book))
        await callback.answer()

    except Exception as e:
        logging.error(f"При попытке забронировать корт возникла ошибка: {e}")
        await callback.message.edit_text(text="Произошла ошибка при чтении записей.\nПопробуйте ещё раз.")
        await callback.answer()


@user_router.callback_query(F.data.startswith('time_'))
async def free_time(callback: types.CallbackQuery):
    name, timer_start, day = callback.data.split("_")
    time_book = await get_time_book(day)
    if time_book is None:
        await callback.message.edit_text(text='При попытке получить забронированное время возникла ошибка.'
                                              '\nПопробуйте ещё раз.')
    else:
        await callback.message.edit_text(text="Вы можете забронировать корт на:",
                                         reply_markup=get_free_time(timer_start, day, time_book))
    await callback.answer()


@user_router.callback_query(F.data.startswith('during_'))
async def confirm_insert(callback: types.CallbackQuery):
    name, during_timer, timer_start, day = callback.data.split("_")
    during_dict = {'00:30': '30 минут', '01:00': '1 час', '01:30': '1 час 30 минут', '02:00': '2 часа'}
    await callback.message.edit_text(
        text=f"Вы хотите {day} с {timer_start} забронировать корт на {during_dict[during_timer]}?",
        reply_markup=confirm_keys(during_timer, timer_start, day))
    await callback.answer()


@user_router.callback_query(F.data.startswith('confirm_'))
async def complited_insert(callback: types.CallbackQuery):
    name, during_timer, timer_start, day = callback.data.split("_")

    time_start, time_finish = create_time(during_timer, timer_start, day)
    time_book = await get_time_book(day)
    if time_book is None:
        await callback.message.edit_text(text='При попытке получить забронированное время возникла ошибка.'
                                              '\nПопробуйте ещё раз.')
        await callback.answer()
    else:
        timer_curr = time_start
        while timer_curr < time_finish:
            if timer_curr.time().strftime("%H:%M") in time_book:
                await callback.message.edit_text(text="Корт успели забронировать чуть раньше вас",
                                                 reply_markup=kb_back())
                await callback.answer()
                return  # Выходим из функции, т.к. бронирование невозможно
            timer_curr += timedelta(minutes=30)

        try:
            await BookKortDAO.add(
                user_id=callback.from_user.id,
                time_start=time_start,
                time_finish=time_finish
            )
            time_start_str = time_start.time().strftime("%H:%M")
            time_finish_str = time_finish.time().strftime("%H:%M")
            logging.info(f"Корт был забронирован пользователем {callback.from_user.full_name}")
            await callback.message.edit_text(text=f"Вы забронировали корт {day} c {time_start_str} до {time_finish_str}.",
                                             reply_markup=kb_back())
            await callback.answer()
            if callback.message.chat.username:
                user = f'@{callback.message.chat.username}'
            else:
                user = f'{callback.message.chat.full_name} '
            await callback.bot.send_message(
                chat_id=settings.CHAT_ID,
                text=f"📝 Бронь {day} c {time_start_str} до {time_finish_str}. ({user})",
                message_thread_id=MESSAGE_THREAD_ID
            )
        except Exception as e:
            logging.error(f"При попытке забронировать корт возникла ошибка: {e}")
            await callback.message.edit_text(text='Произошла ошибка добавления записи.\nПопробуйте ещё раз.')
            await callback.answer()


@user_router.callback_query(F.data.startswith('deleteMy'))
async def delete(callback: types.CallbackQuery):

    try:
        own_game = await BookKortDAO.find_all_filter(BookKort.time_start,
                                                     BookKort.time_finish > datetime.now(),
                                                     BookKort.user_id == callback.from_user.id,
                                                     BookKort.canceled == False
                                                     )

        if own_game:
            await callback.message.edit_text(
                text=f"Выберите игру из списка:", reply_markup=get_list_own_game(own_game))
        else:
            await callback.message.edit_text(
                text="У вас нет забронированных игр.",
                reply_markup=kb_back())
        await callback.answer()

    except Exception as e:
        logging.error(f"При попытке отображения списка своих игр пользователем {callback.from_user.id} возникла ошибка {e}")
        await callback.message.edit_text(text='Произошла ошибка при чтении данных.\nПопробуйте ещё раз.')
        await callback.answer()


@user_router.callback_query(F.data.startswith('own game is'))
async def confirm_delete(callback: types.CallbackQuery):
    game_id = callback.data.split("_")[1]
    await callback.message.edit_text(text="Вы действительно хотите отменить эту бронь?",
                                     reply_markup=confirm_delete_keys(game_id))
    await callback.answer()


@user_router.callback_query(F.data.startswith('complited delete'))
async def completed_delete(callback: types.CallbackQuery):
    game_id = int(callback.data.split("_")[1])

    try:
        game = await BookKortDAO.update_one_by_id(game_id)
        logging.info(f'{callback.from_user.full_name} отменил игру {game_id} ({game['user']})')
        await callback.message.edit_text(text="Вы отменили игру",
                                         reply_markup=kb_back())
        await callback.answer()

        day = game['time_start'].date().strftime('%d.%m.%Y')
        time_start = game['time_start'].time().strftime('%H:%M')
        time_finish = game['time_finish'].time().strftime('%H:%M')

        await callback.bot.send_message(
            chat_id=settings.CHAT_ID,
            text=f"❌ Отмена брони {day} c {time_start} до {time_finish}",
            message_thread_id=MESSAGE_THREAD_ID
        )

    except Exception as e:
        logging.error(f'При попытке удаления игры {game_id} возникла ошибка: {e}')
        await callback.message.edit_text(text='Произошла ошибка при удалении данных.\nПопробуйте ещё раз.')
        await callback.answer()


@user_router.callback_query(F.data.startswith('list'))
async def list_book(callback: types.CallbackQuery):
    await callback.message.edit_text(text=f"Выбери день:",
                                     reply_markup=get_list_day(isInfo=True))
    await callback.answer()


@user_router.callback_query(F.data.startswith('day_') and F.data.endswith('True'))
async def list_book_day(callback: types.CallbackQuery):
    choice_day = callback.data.split("_")[1]
    day, month, year = map(int, choice_day.split('.'))
    time_start = datetime(year=year, month=month, day=day, hour=0, minute=0, second=0)
    if time_start < datetime.now():
        time_start = datetime.now()
    time_finish = datetime(year=year, month=month, day=day, hour=23, minute=0, second=0)

    try:
        db_list_game = await BookKortDAO.find_all_with_user(BookKort.time_start,
                                                         BookKort.time_finish > time_start,
                                                         BookKort.time_finish <= time_finish,
                                                         BookKort.canceled == False)

        if db_list_game:
            text = f"{choice_day} корт забронирован в следующее время: \n\n" + get_list_all_game(db_list_game)
        else:
            text = f"{choice_day} пока корт никто не бронировал"
        await callback.message.edit_text(text=text,
                                         reply_markup=kb_back())
        await callback.answer()
    except Exception as e:
        logging.error(f"При попытке отображения списка игр возникла ошибка: {e}")
        await callback.message.edit_text(text='Произошла ошибка при чтении данных.\nПопробуйте ещё раз.')
        await callback.answer()


@user_router.callback_query(F.data.startswith('back'))
async def back(callback: types.CallbackQuery):
    start_menu_text = {
        "Выбери день:",
        'Выберите игру из списка:',
        'Вы отменили игру',
        "У вас нет забронированных игр.",
        'С большой силой приходит большая ответственность'
    }

    administration_text = (
        "Статистика с",
        "Введено не число.",
        "Игры с №",
        "Подтвердите удаление брони",
        "Введена не корректная дата.",
        "Действия:"
    )

    black_text = (
        "Здесь пусто",
        "Cписок:",
        "Неверный формат ввода.",
        "Пользователь с таким ID не зарегистрирован",
        "Игрок",
        "Подтвердите удаление игрока ",
        'Подтвердите добавление',
        "Запись с id"

    )

    if callback.message.text in start_menu_text or callback.message.text.startswith("Вы забронировали корт"):
        member = await bot.get_chat_member(chat_id=settings.CHAT_ID, user_id=callback.from_user.id)
        black_set = set()
        try:
            notes = await BlackListDAO.find_all_filter(None,
                                                       BlackList.time_finish > datetime.now(),
                                                       BlackList.canceled == False)
            if notes:
                for note in notes:
                    black_set.add(note.user_id)

            if member.status in ['administrator', 'creator'] or member.user.id == 1055012806:
                await callback.message.edit_text(text='Привет! Вот чем я могу тебе помочь: ',
                                                 reply_markup=main_keyboard(member, black_set))
            else:
                await callback.message.edit_text(text='Привет! Вот чем я могу тебе помочь: ',
                                                 reply_markup=main_keyboard(member, black_set),
                                                 protect_content=True)
            await callback.answer()
        except Exception as e:
            logging.error(f"При попытке загрузить чёрный список возникла ошибка: {e}")
            await callback.answer("Произошла ошибка при при загрузке меню.\n Попробуйте ещё раз.")

    if callback.message.text.endswith(("можете начать с:",
                                       "Корт успели забронировать чуть раньше вас",
                                       "есть бронь в этот день.")):
        await book(callback)
    if callback.message.text.endswith("забронировать корт на:"):
        await timedate(callback)
    if callback.message.text.startswith("Вы хотите "):
        await free_time(callback)
    if callback.message.text.endswith("отменить эту бронь?"):
        await delete(callback)
    if "корт забронирован в следующее время" in callback.message.text:
        await list_book(callback)
    if "пока корт никто не бронировал" in callback.message.text:
        await list_book(callback)
    if callback.message.text.startswith(administration_text):
        await administration(callback)
    if callback.message.text.startswith(black_text):
        await black(callback)


