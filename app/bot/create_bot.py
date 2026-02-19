from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeAllGroupChats, \
    BotCommandScopeChatAdministrators
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings


bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


async def set_commands(bot: Bot):
    commands_private = [
        BotCommand(command="start", description="Запустить бота"),
    ]
    await bot.set_my_commands(commands_private, scope=BotCommandScopeDefault())
    await bot.set_my_commands([], scope=BotCommandScopeAllGroupChats())
    await bot.set_my_commands([], scope=BotCommandScopeChatAdministrators(chat_id=settings.CHAT_ID))



async def start_bot():
    try:
        await bot.send_message(settings.ADMIN_ID, f'Я запущен🥳.')
    except:
        pass


async def stop_bot():
    try:
        await bot.send_message(settings.ADMIN_ID, 'Бот остановлен. За что?😔')
    except:
        pass

