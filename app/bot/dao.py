from datetime import datetime

from sqlalchemy import func, desc, delete, and_, case
from sqlalchemy.orm import selectinload, joinedload

from app.dao.base import BaseDAO
from app.bot.models import User, BookKort, BlackList
from app.database import async_session_maker
from sqlalchemy.future import select


class UserDAO(BaseDAO):
    model = User


class BlackListDAO(BaseDAO):
    model = BlackList

    @classmethod
    async def find_all_with_user(cls, order_by_field=None, *filter_expressions):

        async with async_session_maker() as session:
            query = select(cls.model).options(selectinload(cls.model.user))
            if filter_expressions:
                query = query.filter(and_(*filter_expressions))
            if order_by_field is not None:
                query = query.order_by(order_by_field)
            result = await session.execute(query)
            return result.scalars().all()

    @classmethod
    async def update_one_by_id(cls, data_id: int):

        async with async_session_maker() as session:
            result = await session.get(cls.model, data_id)
            if not result:
                raise ValueError(f"Запись с id={data_id} не найдена")
            result.canceled = True
            result.time_update = datetime.now()
            res_dic = { "user": result.user_id}
            await session.commit()
            return res_dic


class BookKortDAO(BaseDAO):
    model = BookKort

    @classmethod
    async def find_all_with_user(cls, order_by_field=None, *filter_expressions):

        async with async_session_maker() as session:
            query = select(cls.model).options(selectinload(cls.model.user))
            if filter_expressions:
                query = query.filter(and_(*filter_expressions))
            if order_by_field is not None:
                query = query.order_by(order_by_field)
            result = await session.execute(query)
            return result.scalars().all()

    @classmethod
    async def update_one_by_id(cls, data_id: int):

        async with async_session_maker() as session:
            result = await session.get(cls.model, data_id)
            if not result:
                raise ValueError(f"Игра с id={data_id} не найдена")
            result.canceled = True
            result.time_update = datetime.now()
            res_dic = {"user": result.user_id,
                       "time_start": result.time_start,
                       "time_finish": result.time_finish}
            await session.commit()
            return res_dic

    @classmethod
    async def get_statistic(cls, *filter_expressions):

        async with async_session_maker() as session:
            query = (
                select(User.username.label('username'),
                       User.full_name.label('full_name'),
                       cls.model.user_id,
                       func.count(cls.model.bookkort_id).label('total_count'),
                       func.sum(case((cls.model.canceled == True, 1), else_=0)).label('canceled_count')
                       )
                .join(User, User.telegram_id == cls.model.user_id)
                .filter(and_(*filter_expressions))
                .group_by(cls.model.user_id, User.username, User.full_name)
                .order_by(func.count(cls.model.bookkort_id).desc())
            )
            result = await session.execute(query)
            return result.all()