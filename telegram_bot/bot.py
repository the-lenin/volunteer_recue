import logging
import os
import asyncio  # noqa: F401
import aiohttp

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes,
    ConversationHandler,  # RegexHandler,
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


# reply_keyboard = [
#     ['Info', 'Help'],
#     ['Create crew'],
#     ['Update crew'],
# ]
# markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcoming a user at a joining."""
    welcome_msg = "I'm a Volunteer Rescue Bot, please talk to me!"
    # await update.message.reply_text(welcome_msg, reply_markup=markup)
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

# CREW CREATION
CREW_NAME, CREW_LOCATION, CREW_CAPACITY, CHOOSE_ACTION = range(4)


async def start_crew_creation(update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Let's create a crew! Please send the name of the crew."
    )
    return CREW_NAME


async def receive_crew_name(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["crew_name"] = update.message.text
    await update.message.reply_text(
        "Great! Now, please share the location of the crew"
        " (e.g., address or coordinates)."
    )
    return CREW_LOCATION


async def receive_crew_location(update: Update,
                                context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["crew_location"] = update.message.text
    await update.message.reply_text(
        "Awesome! Lastly, please specify the capacity of the crew."
    )
    return CREW_CAPACITY


async def receive_crew_capacity(update: Update,
                                context: ContextTypes.DEFAULT_TYPE) -> int:
    crew_name = context.user_data["crew_name"]
    crew_location = context.user_data["crew_location"]
    crew_capacity = update.message.text

    # Perform crew creation logic here, e.g., save to database
    # Then, provide feedback to the user
    reply_message = (
        f"Crew '{crew_name}' created successfully!\n"
        f"Location: {crew_location}\n"
        f"Capacity: {crew_capacity}\n\n"
    )

    keyboard = [
        ["Change Name", "Change Location", "Change Capacity"],
        ["Done", "Cancel"],
    ]

    await update.message.reply_text(
        reply_message + "What would you like to do?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
    )
    return CHOOSE_ACTION


async def cancel_crew_creation(update: Update,
                               context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Crew creation canceled.",
                                    reply_markup=ReplyKeyboardRemove())

    # Clear user data after canceling the conversation
    context.user_data.clear()
    return ConversationHandler.END


async def handle_action(update: Update,
                        context: ContextTypes.DEFAULT_TYPE) -> int:
    action = update.message.text

    match action:
        case "Done":
            await update.message.reply_text(
                "Saving crew to Database...",
                reply_markup=ReplyKeyboardRemove()
            )
            context.user_data.clear()
            return ConversationHandler.END

        case "Change Name":
            await update.message.reply_text(
                "Please send the new name of the crew."
            )
            return CREW_NAME

        case "Change Location":
            await update.message.reply_text(
                "Please send the new location of the crew."
            )
            return CREW_LOCATION

        case "Change Capacity":
            await update.message.reply_text(
                "Please specify the new capacity of the crew."
            )
            return CREW_CAPACITY

        case "Cancel":
            return await cancel_crew_creation(update, context)

        case _:
            await update.message.reply_text(
                "Invalid action. Please choose from the options."
            )
            return CHOOSE_ACTION


def main() -> None:
    """Run the bot."""
    application = ApplicationBuilder().token(TG_BOT_TOKEN).build()

    start_handler = CommandHandler('start', start)
    test_handler = CommandHandler('test', test)
    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    info_handler = CommandHandler('info', info)

    # Define conversation handler with states
    crew_creation_handler = ConversationHandler(
        entry_points=[CommandHandler("createcrew", start_crew_creation)],
        states={
            CREW_NAME: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, receive_crew_name
            )],
            CREW_LOCATION: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, receive_crew_location
            )],
            CREW_CAPACITY: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, receive_crew_capacity
            )],
            CHOOSE_ACTION: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, handle_action
            )],
        },
        fallbacks=[CommandHandler("cancel", cancel_crew_creation)],
    )

    application.add_handler(start_handler)
    application.add_handler(info_handler)
    application.add_handler(test_handler)
    application.add_handler(crew_creation_handler)
    application.add_handler(unknown_handler)  # last one

    application.run_polling()


if __name__ == '__main__':
    main()
