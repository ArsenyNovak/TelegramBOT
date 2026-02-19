import logging
from datetime import datetime, date, timedelta

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from app.bot.dao import UserDAO, BookKortDAO, BlackListDAO
from app.bot.kbs import admin_menu, kb_back, confirm_delete_keys, black_menu, kb_complited
from app.bot.models import BookKort, BlackList
from app.bot.utils import get_list_statistic, get_black_list, check_username

admin_router = Router()


class Form(StatesGroup):
    waiting_for_date = State()
    waiting_for_gameID = State()
    waiting_for_userID = State()
    waiting_for_blacklistID = State()


@admin_router.callback_query(F.data.startswith('admin'))
async def administration(callback: types.CallbackQuery):
    await callback.message.edit_text(text="С большой силой приходит большая ответственность",
                                     reply_markup=admin_menu())
    await callback.answer()


@admin_router.callback_query(F.data.startswith('statistic'))
async def statistica(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(text="Введите период (ДД.ММ.ГГГГ-ДД.ММ.ГГГГ)")
    await state.set_state(Form.waiting_for_date)
    await callback.answer()


@admin_router.message(Form.waiting_for_date)
async def check_date(message: types.Message, state: FSMContext):

    try:
        start, finish =  message.text.split('-')
        start = datetime.strptime(start, '%d.%m.%Y')
        finish = datetime.strptime(finish, '%d.%m.%Y')
        if finish < start:
            raise ValueError
        if finish.year < 2025 or start.year < 2025:
            raise ValueError

        try:
            list_game = await BookKortDAO.get_statistic(BookKort.time_finish >= start,
                                                        BookKort.time_finish <= finish)
            text = (f"Статистика с {start.date().strftime('%d.%m.%Y')} до {finish.date().strftime('%d.%m.%Y')}: \n\n"
                    + get_list_statistic(list_game))
            await message.answer(text=text, parse_mode='Markdown',reply_markup=kb_back())

        except Exception as e:
            logging.error(f'При попытке отображения списка игр возникла ошибка: {e}')
            await message.answer(text='Произошла ошибка при чтении данных.\nПопробуйте ещё раз.')

    except ValueError:
        await message.answer(text='Введена не корректная дата. Для повторного ввода вернитесь "назад"',
                            reply_markup=kb_back())

    finally:
        await state.clear()


@admin_router.callback_query(F.data.startswith('deleteID'))
async def deleteID(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(text="Введите номер игры ")
    await state.set_state(Form.waiting_for_gameID)
    await callback.answer()


@admin_router.message(Form.waiting_for_gameID)
async def deleteID_searsh(message: types.Message, state: FSMContext):
    game_id =  message.text
    try:
        if not game_id.isdigit():
            raise ValueError

        try:
            game = await BookKortDAO.find_all_with_user(None,
                                                        BookKort.bookkort_id==int(game_id),
                                                        BookKort.time_finish > datetime.now(),
                                                        BookKort.canceled == False
                                                        )
            if game:
                game = game[0]
                day = game.time_start.date().strftime('%d.%m.%Y')
                time_start = game.time_start.time().strftime('%H:%M')
                time_finish = game.time_finish.time().strftime('%H:%M')
                user = game.user.username
                if not user:
                    user = game.user.full_name
                text = f'Подтвердите удаление брони {day} c {time_start} до {time_finish} ({user})'
                await message.answer(text=text, reply_markup=confirm_delete_keys(game_id))

            else:
                await message.answer(text=f'Игры с №{game_id} не существует', reply_markup=kb_back())

        except Exception as e:
            logging.error(f'При попытке админа запросить игру возникла ошибка: {e}')
            await message.answer(text='Произошла ошибка при чтении данных.\nПопробуйте ещё раз.')

    except ValueError:
        await message.answer(text='Введено не число. Для повторного ввода вернитесь "назад"',
                             reply_markup=kb_back())
    finally:
        await state.clear()


@admin_router.callback_query(F.data.startswith('black_'))
async def black(callback: types.CallbackQuery):
    await callback.message.edit_text(text='Действия:', reply_markup=black_menu())
    await callback.answer()


@admin_router.callback_query(F.data.startswith('black show'))
async def blacklist(callback: types.CallbackQuery):
    try:
        db_blacklist = await BlackListDAO.find_all_with_user(BlackList.time_finish,
                                                             BlackList.time_finish > datetime.now(),
                                                             BlackList.canceled == False)
        if db_blacklist:
            text = get_black_list(db_blacklist)
        else:
            text = "Здесь пусто"
        await callback.message.edit_text(text=text, parse_mode='Markdown', reply_markup=kb_back())
        await callback.answer()

    except Exception as e:
        logging.error(f'При попытке отображения чёрного списка пользователей возникла ошибка: {e}')
        await callback.message.edit_text(text='Произошла ошибка при чтении данных.\nПопробуйте ещё раз.')
        await callback.answer()


@admin_router.callback_query(F.data.startswith('black add'))
async def blackadd(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(text='Введите ID игрока и количество дней через пробел:')
    await state.set_state(Form.waiting_for_userID)
    await callback.answer()


@admin_router.message(Form.waiting_for_userID)
async def blackadd_searsh(message: types.Message, state: FSMContext):

    try:
        black_id, black_day =  message.text.split(" ")
        if not black_id.isdigit():
            raise ValueError("ID пользователя не число")
        if not black_day.isdigit():
            raise ValueError("Колличество дней не число")

        try:
            db_user = await UserDAO.find_one_or_none(telegram_id=int(black_id))
            if db_user:
                user = check_username(db_user.username, db_user.full_name)
                black_day_str = str(black_day)
                if black_day_str == '1':
                    black_day_str += ' день'
                elif black_day_str in {'2', '3', '4'}:
                    black_day_str += ' дня'
                else:
                    black_day_str += ' дней'
                await message.answer(text=f'Подтвердите добавление {user} в чёрный список на {black_day_str}.',
                                     reply_markup=kb_complited('complited blackadd', black_id, black_day))
            else:
                await message.answer(text='Пользователь с таким ID не зарегистрирован',
                                     reply_markup=kb_back())

        except Exception as e:
            logging.error(f'При попытке админа найти пользователя по ID возникла ошибка: {e}')
            await message.answer(text=f'Произошла ошибка при чтении данных.\nПопробуйте ещё раз.')

    except ValueError:
        await message.answer(text='Введено не число. Для повторного ввода вернитесь "назад"',
                             reply_markup=kb_back())
    finally:
        await state.clear()


@admin_router.callback_query(F.data.startswith('complited blackadd'))
async def completed_blackadd(callback: types.CallbackQuery):
    _, black_id, black_day = callback.data.split("_")
    black_id = int(black_id)
    black_day = int(black_day)
    time_finish = date.today() + timedelta(days=black_day)

    try:
        await BlackListDAO.add(user_id=black_id, time_finish=time_finish)
        db_user = await UserDAO.find_one_or_none(telegram_id=black_id)
        user = check_username(db_user.username, db_user.full_name)
        logging.info(f'В чёрный список был занесён {user} на {black_day} дней админом {callback.from_user.id})')
        await callback.message.edit_text(text=f'Игрок {user} был занесён в чёрный список.',
                                         reply_markup=kb_back())
        await callback.answer()

    except Exception as e:
        logging.error(f'При попытке добавить игрока в чёрный список возникла ошибка: {e}')
        await callback.message.edit_text(text=f'Произошла ошибка при добавлении игрока в чёрный список.'
                                              f'\nПопробуйте ещё раз.')
        await callback.answer()


@admin_router.callback_query(F.data.startswith('black delete'))
async def blackdelete(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(text='Введите номер записи:')
    await state.set_state(Form.waiting_for_blacklistID)
    await callback.answer()


@admin_router.message(Form.waiting_for_blacklistID)
async def blackdelete_searsh(message: types.Message, state: FSMContext):

    try:
        black_id =  message.text
        if not black_id.isdigit():
            raise ValueError("Номер записи не число")

        try:
            black_note = await BlackListDAO.find_all_filter(None,
                                                         BlackList.blacklist_id == int(black_id),
                                                         BlackList.time_finish > datetime.now(),
                                                         BlackList.canceled == False)
            if black_note:
                db_user = await UserDAO.find_one_or_none(telegram_id=black_note[0].user_id)
                user = check_username(db_user.username, db_user.full_name)
                await message.answer(text=f'Подтвердите удаление игрока {user} из чёрного списка.',
                                     reply_markup=kb_complited('complited blackdelete', black_id))
            else:
                await message.answer(text=f'Запись с id={black_id} не найдена',
                                     reply_markup=kb_back())

        except Exception as e:
            logging.error(f'При попытке найти пользователя в чёрном списке возникла ошибка: {e}')
            await message.answer(text=f'Произошла ошибка при чтении данных.\nПопробуйте ещё раз.')

    except ValueError:
        await message.answer(text='Введено не число. Для повторного ввода вернитесь "назад"',
                             reply_markup=kb_back())
    finally:
        await state.clear()


@admin_router.callback_query(F.data.startswith('complited blackdelete'))
async def completed_blackdelete(callback: types.CallbackQuery):
    black_id = int(callback.data.split("_")[1])

    try:
        note = await BlackListDAO.update_one_by_id(black_id)
        db_user = await UserDAO.find_one_or_none(telegram_id=note['user'])
        user = check_username(db_user.username, db_user.full_name)
        logging.info(f'Игрок {user} был убран админом {callback.from_user.id} из чёрного списка)')
        await callback.message.edit_text(text=f'Игрок {user} был убран из чёрного списка.',
                                         reply_markup=kb_back())
        await callback.answer()

    except Exception as e:
        logging.error(f'При попытке удалить игрока из чёрный список возникла ошибка: {e}')
        await callback.message.edit_text(text=f'Произошла ошибка при удалении игрока из чёрного списка.\n'
                                              f'Попробуйте ещё раз.')
        await callback.answer()

