import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.enums import ParseMode
from sqlalchemy import select
from app.models.Tenant import Tenant

from app.core.config import settings
from app.core.auth import hash_api_key
from app.core.database import AsyncSessionLocal
from app.repositories import tenant as tenant_repo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def handle_start(message: types.Message):
    await message.answer(
        "Привет! \n\n"
        "Я бот EventPulse для уведомлений об алертах.\n\n"
        "Для привязки аккаунта используй:\n"
        "<code>/link твой_api_ключ</code>\n\n"
        "Проверить привязку: /status", parse_mode="HTML"
    )


@dp.message(Command("link"))
async def handle_link(message: types.Message, command: CommandObject):
    api_key = command.args

    if not api_key:
        await message.answer(
            "Укажи API-ключ:\n"
            "<code>/link твой_api_ключ</code>", parse_mode="HTML")
        return

    key_hash = hash_api_key(api_key.strip())

    async with AsyncSessionLocal() as session:
        tenant = await tenant_repo.find_by_api_key_hash(key_hash, session)

        if not tenant:
            await message.answer(
                "Ключ не найден. Проверь правильность API-ключа.", parse_mode="HTML")
            return

        await tenant_repo.set_telegram_chat_id(
            tenant,
            str(message.chat.id),
            session, )

    await message.answer(
        f"Привязка успешна!\n\n"
        f"Алерты для <b>{tenant.name}</b> будут приходить в этот чат.", parse_mode="HTML")

    logger.info(
        "Tenant %s linked to chat %s",
        tenant.id,
        message.chat.id, )


@dp.message(Command("status"))
async def handle_status(message: types.Message):
    chat_id = str(message.chat.id)

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Tenant).where(Tenant.telegram_chat_id == chat_id))
        tenant = result.scalar_one_or_none()

    if not tenant:
        await message.answer("Этот чат не привязан ни к одному аккаунту.")
        return

    await message.answer(
        f"Привязан аккаунт: <b>{tenant.name}</b>\n"
        f"Тариф: {tenant.plan.value}",
    parse_mode = "HTML")

    async def main():
        logger.info("Bot starting")
        await dp.start_polling(bot)

    if __name__ == "__main__":
        asyncio.run(main())
