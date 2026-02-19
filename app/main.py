import asyncio
import logging

from contextlib import asynccontextmanager
from app.bot.create_bot import bot, dp, stop_bot, start_bot, set_commands
from app.bot.user_router import user_router
from app.bot.admin_router import admin_router
from app.config import settings
from aiogram.types import Update
from fastapi import FastAPI, Request


logging.basicConfig(filename='app/app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Starting bot setup...")
    dp.include_router(user_router)
    dp.include_router(admin_router)
    await start_bot()
    await set_commands(bot)
    webhook_url = settings.get_webhook_url()
    await bot.set_webhook(url=webhook_url,
                          allowed_updates=dp.resolve_used_update_types(),
                          drop_pending_updates=True)
    logging.info(f"Webhook set to {webhook_url}")
    yield
    logging.info("Shutting down bot...")
    await bot.delete_webhook()
    await stop_bot()
    logging.info("Webhook deleted")


app = FastAPI(lifespan=lifespan, root_path="/tennis")


@app.post("/webhook")
async def webhook(request: Request) -> None:
    # logging.info("Received webhook request")
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    # logging.info("Update processed")


# закомментировать при работе через WEBHOOK

# async def main():
#     dp.include_router(user_router)
#     dp.include_router(admin_router)
#     await dp.start_polling(bot)
#
# if __name__ == "__main__":
#     asyncio.run(main())