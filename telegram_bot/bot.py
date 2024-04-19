import logging
import asyncio
import os

from telegram import Update
from telegram.ext import (
    filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes,
)

from dotenv import load_dotenv

# Load local enviroment .env
load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcoming a user at a joining."""
    welcome_msg = "I'm a Volunteer Rescue Bot, please talk to me!"
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=welcome_msg)


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echo user message as reply."""
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=update.message.text)


async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Caps a command given argument."""
    text_caps = ' '.join(context.args).upper()
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=text_caps)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return unknown command message if a command is not found."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I didn't understand that command."
    )


if __name__ == '__main__':
    application = ApplicationBuilder().token(
        os.getenv('TELEGRAM_BOT_TOKEN')
    ).build()

    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    caps_handler = CommandHandler('caps', caps)
    unknown_handler = MessageHandler(filters.COMMAND, unknown)

    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    application.add_handler(caps_handler)

    # last one
    application.add_handler(unknown_handler)

    application.run_polling()
