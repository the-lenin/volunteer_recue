import os
import logging
import django
from tgbot.logging_config import setup_logging_config


from telegram import (
    Update,
    ReplyKeyboardMarkup,
    # ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from telegram.ext import (
    filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
)

setup_logging_config()
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_dashboard.settings')
django.setup()

from django.conf import settings  # noqa: E402
from web_dashboard.logistics.models import Departure  # noqa: E402
from web_dashboard.search_requests.models import SearchRequest   # noqa: E402


(
    SHOWING,
    SELECT_ACTION,
    STOPPING,

    INFO,
    HELP,

    CREW_CREATION,
    CREW_UPDATE,

    LIST_DEPARTURES,
    DISPLAY_DEPARTURE,
    SELECT_DEPARTURE_ACTION,

    CREW_NAME,
    CREW_LOCATION,
    CREW_CAPACITY,
    CREW_VALIDATE_ACTION,

    SELECT,
    BACK,
    START_OVER,
) = map(chr, range(17))

END = ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Welcoming a user at the joining."""
    msg = "I'm a Volunteer Rescue Bot!\nWhat do you want to do?"

    buttons = [
        [
            InlineKeyboardButton('Info', callback_data=str(INFO)),
            InlineKeyboardButton('Help', callback_data=str(HELP)),
        ],
        [
            InlineKeyboardButton('Create crew',
                                 callback_data=str(CREW_CREATION)),
            InlineKeyboardButton('Update crew',
                                 callback_data=str(CREW_UPDATE)),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)

    if context.user_data.get(START_OVER):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("What is next?", reply_markup=keyboard)
    else:
        await update.message.reply_text(msg, reply_markup=keyboard)

    context.user_data[START_OVER] = False
    return SELECT_ACTION


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display present number of the open SearchRequest and Departures."""
    query = update.callback_query
    await query.answer()

    search_requests = await SearchRequest.objects.filter(
        status=SearchRequest.StatusVerbose.OPEN
    ).acount()

    departures = await Departure.objects.filter(
            status=Departure.StatusVerbose.OPEN
    ).acount()

    msg = (
        f'{SearchRequest._meta.verbose_name_plural}: {search_requests}\n'
        f'{Departure._meta.verbose_name_plural}: {departures}'
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data=str(END))],
    ])

    await query.edit_message_text(msg, reply_markup=keyboard)
    context.user_data[START_OVER] = True
    return SHOWING


async def help_command(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display help message."""
    query = update.callback_query
    await query.answer()

    msg = (
        "/start - start conversation and display all available actions\n"
        "/info - display current status of activities\n"
        "/help - display this message\n"
        "/cancel- cancel conversation"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data=str(END))],
    ])

    # await context.bot.send_message(chat_id=update.effective_chat.id,
    #                                text=msg)
    await query.edit_message_text(msg, reply_markup=keyboard)
    context.user_data[START_OVER] = True
    return SHOWING


async def stop(update: Update,
               context: ContextTypes.DEFAULT_TYPE) -> int:
    """End conversation by command."""
    msg = "Canceled. Return back to /start."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    context.user_data.clear()
    return END


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return unknown command message if a command is not found."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I didn't understand that command."
    )


async def list_departures(update: Update,
                          context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display a list of all departures with open status."""
    query = update.callback_query
    await query.answer()
    # crew_action = query.data
    # context.user_data['crew_action'] = crew_action

    departures = Departure.objects.filter(status=Departure.StatusVerbose.OPEN)\
        .select_related('search_request')

    if not await departures.aexists():
        await update.message.reply_text(
            "There are no available Departures, please try later."
        )
        return ConversationHandler.END

    departures = [dep async for dep in departures]
    keyboard = []

    for ind, dep in enumerate(departures):
        keyboard.append([
            InlineKeyboardButton(
                f"{ind}. {dep.search_request.full_name} - "
                f"{dep.search_request.city} "
                f"(Crews: {await dep.crews.acount()})",
                callback_data=str(ind)
            )
        ])

    # TODO: Why to keep keyboard???
    context.user_data['departures'] = list(zip(departures, keyboard))

    await query.edit_message_text(
        f"Total number of departures: {len(departures)}\n"
        "Let's create a crew! Please choose Departure.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return DISPLAY_DEPARTURE


async def display_departure(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display detailed information of the chosen departure with buttons."""
    query = update.callback_query
    await query.answer()

    index = int(query.data)
    departure = context.user_data['departures'][index]

    # Display detailed information about the selected departure with buttons
    dep = departure[0]
    tasks = '\n'.join([
        f'* {task.title} - {task.coordinates.coords}:\n{task.description}'
        async for task in dep.tasks.all()
    ])

    msg = (
        f"""
Departure ID: {dep.id}
Number of crews: {await dep.crews.acount()}

Missing person: {dep.search_request.full_name}
Diasappearance date: {dep.search_request.disappearance_date}
Location: {dep.search_request.city}
PSN: {dep.search_request.location.coords}

Tasks ({await dep.tasks.acount()}):
{tasks}

raw json:\n{dep.__dict__}\n
raw search_request:\n{dep.search_request.__dict__}\n
raw tasks:\n{dep.tasks.__dict__}
        """
    )

    buttons = [
        [
            InlineKeyboardButton("Select", callback_data=str(SELECT)),
            InlineKeyboardButton("Back", callback_data=str(BACK)),
            InlineKeyboardButton("Cancel", callback_data=str(END)),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)

    context.user_data['departure'] = {'pk': dep.pk, 'index': index}
    return SELECT_DEPARTURE_ACTION


async def receive_departure(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.delete_message()

    pk, ind = context.user_data["departure"].values()
    logger.info(f'{context.user_data=},\n{pk=}, {ind=}')
    msg = (
            "You selected Departure:\n"
            f'{ind}: ID {pk}\n'
            f'{context.user_data["departures"][ind]}\n\n'

            "Please enter the name of the crew:"
    )

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=msg)
    return CREW_NAME


async def receive_crew_name(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> int:
    crew_name = update.message.text
    context.user_data["crew_name"] = crew_name
    msg = (f"Crew name: {crew_name}\n"
           "Great! Now, please share the location of the crew"
           " (e.g., address or coordinates).")

    await update.message.reply_text(msg)
    return CREW_LOCATION


async def receive_crew_location(update: Update,
                                context: ContextTypes.DEFAULT_TYPE) -> int:
    crew_location = update.message.text
    context.user_data["crew_location"] = crew_location
    await update.message.reply_text(
        f"Location: {crew_location=}\n"
        "Awesome! Lastly, please specify the capacity of the crew."
    )
    return CREW_CAPACITY


async def receive_crew_capacity(update: Update,
                                context: ContextTypes.DEFAULT_TYPE) -> int:
    departure = context.user_data["departure"]
    crew_name = context.user_data["crew_name"]
    crew_location = context.user_data["crew_location"]
    crew_capacity = update.message.text

    # TODO: Perform crew creation logic here, e.g., save to database
    # Then, provide feedback to the user
    reply_message = (
        f"Departure {departure}\n"
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
    # TODO: Inlinekeyboard, SAVE, EDIT, CANCEL
    return SELECT_ACTION


async def crew_validate(update: Update,
                        context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display actions before creation of the crew."""
    pass


async def stop_nested(update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> int:
    """End nested conversation by command."""
    msg = "Canceled. Return back to /start."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    context.user_data.clear()
    return STOPPING


def main() -> None:
    """Run the bot."""
    application = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()

    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    info_handler = CommandHandler('info', info)
    help_handler = CommandHandler('help', help_command)

    crew_action_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            receive_departure, pattern="^" + str(SELECT) + "$"
        )],

        states={
            SHOWING: [CallbackQueryHandler(receive_departure,
                                           pattern="^" + str(END) + "$")],

            CREW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND,
                                       receive_crew_name)],
            CREW_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND,
                                           receive_crew_location)],
            CREW_CAPACITY: [MessageHandler(filters.TEXT & ~filters.COMMAND,
                                           receive_crew_capacity)],
            CREW_VALIDATE_ACTION: [CallbackQueryHandler(crew_validate)],
        },
        fallbacks=[CommandHandler("cancel", stop)],
    )

    departure_selction_handlers = [
        crew_action_handler,
        CallbackQueryHandler(list_departures, pattern="^" + str(BACK) + "$"),
        CallbackQueryHandler(stop_nested, pattern="^" + str(END) + "$")
    ]

    departure_action_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            list_departures, pattern=f"^{CREW_CREATION}|{CREW_UPDATE}$"
        )],

        states={
            DISPLAY_DEPARTURE: [CallbackQueryHandler(display_departure)],
            SELECT_DEPARTURE_ACTION: departure_selction_handlers,
        },

        # TODO: works only as command, END stay at the present level
        fallbacks=[CommandHandler("cancel", stop_nested)],
        map_to_parent={
            STOPPING: END
        },
    )

    selection_handlers = [
        departure_action_handler,
        CallbackQueryHandler(info, pattern="^" + str(INFO) + "$"),
        CallbackQueryHandler(help_command, pattern="^" + str(HELP) + "$"),
    ]

    action_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SHOWING: [CallbackQueryHandler(start,
                                           pattern="^" + str(END) + "$")],
            SELECT_ACTION: selection_handlers,
            STOPPING: [CommandHandler("stop", start)],
        },
        fallbacks=[CommandHandler("cancel", stop)],
    )

    application.add_handler(info_handler)
    application.add_handler(help_handler)
    application.add_handler(action_handler)

    # unknown_handler hast to be the last one
    application.add_handler(unknown_handler)

    application.run_polling()


if __name__ == '__main__':
    main()
