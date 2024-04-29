import logging
import os
import asyncio  # noqa: F401
import aiohttp

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

HOST = os.getenv('HOST')
PORT = os.getenv('PORT')
TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN')
DJANGO_TG_TOKEN = os.getenv('DJANGO_TG_TOKEN')

if not all((HOST, PORT, TG_BOT_TOKEN, DJANGO_TG_TOKEN)):
    raise Exception(
        'Please set up the following variables in ".env" file '
        'in the root of the project:\n'
        'HOST, PORT, TG_BOT_TOKEN, DJANGO_TG_TOKEN'
    )

LOCAL_URL = f"http://{os.getenv('HOST')}:{os.getenv('PORT')}/json/"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcoming a user at a joining."""
    welcome_msg = "I'm a Volunteer Rescue Bot, please talk to me!"
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=welcome_msg)


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display basic information."""
    header = {'Authorization': f'access_token {DJANGO_TG_TOKEN}'}
    async with aiohttp.ClientSession() as session:
        async with session.get(LOCAL_URL, headers=header) as resp:
            msg = await resp.text()
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=msg)


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return 'Ok' msg if connection is working with Django."""
    header = {'Authorization': f'access_token {DJANGO_TG_TOKEN}'}

    async with aiohttp.ClientSession() as session:
        async with session.get(LOCAL_URL, headers=header) as resp:
            msg = await resp.text()
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=msg)


# async def create_crew(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Send json to django."""
#     msg_in = update.message.text
#     print(msg_in)
#     print(context.args)
#     response = requests.post(LOCAL_URL, data=msg_in)
#     print(response.__dict__)
#     msg_out = response.json()
#     await context.bot.send_message(chat_id=update.effective_chat.id,
#                                    text=msg_out)


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
    application = ApplicationBuilder().token(TG_BOT_TOKEN).build()

    start_handler = CommandHandler('start', start)
    test_handler = CommandHandler('test', test)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    caps_handler = CommandHandler('caps', caps)
    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    info_handler = CommandHandler('info', info)
#     create_crew_handler = CommandHandler('create_crew', create_crew)

    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    application.add_handler(caps_handler)
    application.add_handler(info_handler)
    application.add_handler(test_handler)
#    application.add_handler(create_crew_handler)

    # last one
    application.add_handler(unknown_handler)

    application.run_polling()
