"""Telegram bot on python-telegram-bot. Run: `python -m src.bot`."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def handle_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    open_app_button = InlineKeyboardButton("Открыть приложение", url=settings.app_url)
    await update.message.reply_text(
        "Привет! Нажми кнопку, чтобы открыть приложение.",
        reply_markup=InlineKeyboardMarkup([[open_app_button]]),
    )


def run_bot() -> None:
    if not settings.tg_bot_token:
        raise SystemExit("TG_BOT_TOKEN is not set")
    application = Application.builder().token(settings.tg_bot_token).build()
    application.add_handler(CommandHandler("start", handle_start))
    application.run_polling()


if __name__ == "__main__":
    run_bot()
