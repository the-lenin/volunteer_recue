import logging
import os
import asyncio  # noqa: F401
import aiohttp

from telegram import Update
from telegram.ext import (
    filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes,
    # RegexHandler, ConversationHandler
)
from dotenv import load_dotenv


# Load local enviroment .env
load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

HOST = os.getenv('HOST')
PORT = os.getenv('PORT')
TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN')
DJANGO_TG_TOKEN = os.getenv('DJANGO_TG_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

if not all((HOST, PORT, TG_BOT_TOKEN, DJANGO_TG_TOKEN, WEBHOOK_URL)):
    raise Exception(
        'Please set up the following variables in ".env" file '
        'in the root of the project:\n'
        'HOST, PORT, TG_BOT_TOKEN, DJANGO_TG_TOKEN, WEBHOOK_URL'
    )

LOCAL_URL = f"http://{os.getenv('HOST')}:{os.getenv('PORT')}/{WEBHOOK_URL}/"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcoming a user at a joining."""
    welcome_msg = "I'm a Volunteer Rescue Bot, please talk to me!"
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=welcome_msg)


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return 'Ok' msg if connection is working with Django."""
    header = {'Authorization': f'access_token {DJANGO_TG_TOKEN}'}

    async with aiohttp.ClientSession() as session:
        async with session.get(LOCAL_URL, headers=header) as resp:
            response_data = await resp.text()
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=response_data)


async def post_wh(update: Update,
                  context: ContextTypes.DEFAULT_TYPE,
                  payload: dict) -> None:
    """Post payload to webhook."""
    header = {'Authorization': f'access_token {DJANGO_TG_TOKEN}'}

    async with aiohttp.ClientSession() as session:
        async with session.post(LOCAL_URL,
                                headers=header,
                                json=payload) as resp:

            response_data = await resp.json()

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=response_data)


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display present number of the open SearchRequest and Departures."""
    payload = {'action': 'info'}
    await post_wh(update, context, payload)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return unknown command message if a command is not found."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I didn't understand that command."
    )


def main() -> None:
    """Run the bot."""
    application = ApplicationBuilder().token(TG_BOT_TOKEN).build()

    start_handler = CommandHandler('start', start)
    test_handler = CommandHandler('test', test)
    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    info_handler = CommandHandler('info', info)

    application.add_handler(start_handler)
    application.add_handler(info_handler)
    application.add_handler(test_handler)
    application.add_handler(unknown_handler)  # last one

    application.run_polling()


if __name__ == '__main__':
    main()
