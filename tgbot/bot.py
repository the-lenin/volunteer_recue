import os
import logging
import django
from tgbot.logging_config import setup_logging_config
from asgiref.sync import sync_to_async

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

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_dashboard.settings')
django.setup()

from django.conf import settings  # noqa: E402

from web_dashboard.logistics.models import Departure, Crew  # noqa: E402
from web_dashboard.search_requests.models import SearchRequest   # noqa: E402
from web_dashboard.users.models import CustomUser  # noqa: E402

setup_logging_config(settings.DEBUG)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
logger.info(settings.DEBUG)

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
    CREW_SELECT_ACTION,

    SELECT,
    BACK,
    START_OVER,
) = map(chr, range(17))

END = ConversationHandler.END


def get_allowed_users() -> set:
    """Return a set of allowed_users."""
    return set(CustomUser.objects.values_list('telegram_id', flat=True))


allowed_users = get_allowed_users()
filter_users = filters.User(user_id=allowed_users)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcoming a user at the joining."""
    msg = "I'm a Volunteer Rescue Bot!"

    user_id = update.effective_user.id

    global allowed_users
    if user_id not in allowed_users:
        msg = f'Here is your Telegram ID: {user_id}'
        await context.bot.send_message(text=msg,
                                       chat_id=update.effective_chat.id)
    else:
        msg = '/start_conversation'
        buttons = [
            ['/cancel']
        ]

        keyboard = ReplyKeyboardMarkup(buttons)
        await context.bot.send_message(text=msg,
                                       chat_id=update.effective_chat.id,
                                       reply_markup=keyboard)


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manually restart a list of allowed users."""
    try:
        global allowed_users, filter_users
        updated_users = await sync_to_async(get_allowed_users)()
        added_users = updated_users - allowed_users
        removed_users = allowed_users - updated_users

        logger.debug(f'{added_users=}\n{removed_users=}')

        if added_users:
            filter_users.add_user_ids(added_users)
        if removed_users:
            filter_users.remove_user_ids(removed_users)

        allowed_users = updated_users
        logger.info('Restarted allowed_users:\n'
                    f'{filter_users=}\n{update.effective_user.id=}')

        msg = 'Restarted'
        await context.bot.send_message(text=msg,
                                       chat_id=update.effective_chat.id)
    except Exception as e:
        msg = 'Failed'
        await context.bot.send_message(text=msg,
                                       chat_id=update.effective_chat.id)
        logger.warning(e)


async def restrict(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Restrict any unathorised user from any further action."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Unathorised access."
    )


async def start_conversation(update: Update,
                             context: ContextTypes.DEFAULT_TYPE) -> int:
    """Welcoming a user at the joining."""
    query = update.callback_query
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

    if query and context.user_data.get(START_OVER):
        await query.answer()
        await query.edit_message_text("What is next?", reply_markup=keyboard)
    else:
        await update.message.reply_text(msg, reply_markup=keyboard)

    context.user_data[START_OVER] = False
    return SELECT_ACTION


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display present number of the open SearchRequest and Departures."""
    query = update.callback_query

    search_requests = await SearchRequest.objects.filter(
        status=SearchRequest.StatusVerbose.OPEN
    ).acount()

    departures = await Departure.objects.filter(
            status=Departure.StatusVerbose.OPEN
    ).acount()

    msg = (
        f'\n\n{SearchRequest._meta.verbose_name_plural}: {search_requests}'
        f'\n{Departure._meta.verbose_name_plural}: {departures}'
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data=str(END))],
    ])

    if query:
        await query.answer()
        await query.edit_message_text(msg, reply_markup=keyboard)
        context.user_data[START_OVER] = True
        return SHOWING
    else:
        await update.message.reply_text(msg)


async def help_command(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display help message."""
    query = update.callback_query

    msg = (
        "/start_conversation - start conversation and show available actions\n"
        "/info - display current status of activities\n"
        "/help - display this message\n"
        "/cancel - cancel conversation\n"
        "/restart - reset Telegram ID to the chosen one in the user profile"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data=str(END))],
    ])

    if query:
        await query.answer()
        await query.edit_message_text(msg, reply_markup=keyboard)
        context.user_data[START_OVER] = True
        return SHOWING
    else:
        await update.message.reply_text(msg)


async def stop(update: Update,
               context: ContextTypes.DEFAULT_TYPE) -> int:
    """End conversation by command."""
    msg = "Canceled. Return back to /start_conversation."
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

    # TODO: If the pagination required, keyboard / index will be remembered
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
    """
    Display the selected departure and request to enter a crew name.
    """
    query = update.callback_query
    await query.answer()
    await query.delete_message()

    pk, ind = context.user_data["departure"].values()
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
    """
    Display the crew name and request to enter a pickup location.
    """
    crew_name = update.message.text
    context.user_data["crew_name"] = crew_name
    msg = (f"Crew name: {crew_name}\n"
           "Great! Now, please share the location of the crew"
           " (e.g., address or coordinates).")

    await update.message.reply_text(msg)
    return CREW_LOCATION


async def receive_crew_location(update: Update,
                                context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Display the location and request to enter a crew capacity.
    """
    crew_location = update.message.text
    context.user_data["crew_location"] = crew_location
    await update.message.reply_text(
        f"Location: {crew_location=}\n"
        "Awesome! How many passengers could you take:"
    )
    return CREW_CAPACITY


async def receive_crew_capacity(update: Update,
                                context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Display entered summary and next action buttons.
    """
    departure = context.user_data["departure"]
    crew_name = context.user_data["crew_name"]
    crew_location = context.user_data["crew_location"]
    crew_capacity = update.message.text
    context.user_data['crew_capacity'] = crew_capacity

    msg = (
        f"Departure {departure}\n"
        f"Crew '{crew_name}' created successfully!\n"
        f"Location: {crew_location}\n"
        f"Capacity: {crew_capacity}\n\n"
        "Please select the next action."
    )

    buttons = [
        [
            InlineKeyboardButton("Save", callback_data=str(SELECT)),
            InlineKeyboardButton("Edit", callback_data=str(BACK)),
            InlineKeyboardButton("Cancel", callback_data=str(END))
        ],
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(msg, reply_markup=keyboard)
    return CREW_SELECT_ACTION


async def crew_select_action(update: Update,
                             context: ContextTypes.DEFAULT_TYPE) -> int:
    """Redirect to other action or validate crew creation."""
    query = update.callback_query
    await query.answer()

    answer = query.data
    user_id = query.from_user.id

    query.delete_message()

    global SELECT, BACK, END

    try:
        user = await CustomUser.objects.aget(telegram_id=user_id)
        # TODO: Is user driver? has_car=True
    except Exception as e:
        msg = 'You are not found in database. Please contact Operator.\n'\
                + str(e)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=msg)
    finally:
        return END

    match answer:
        case str(SELECT):
            try:
                await Crew.objects.acreate(
                    departure=context.user_data["departure"],
                    title=context.user_data["crew_name"],
                    driver=user.id,
                    phone_number=user.phone_number,
                    status=Crew.StatusVerbose.OPEN,
                )

                msg = "Crew is created."
            except Exception:  # TODO: Specify error
                msg = "Unexpected error. Crew is NOT created."""
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=msg)
            return END
        case str(BACK):
            return SHOWING
        case str(END):
            return END
    pass


async def stop_nested(update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> int:
    """End nested conversation by command."""
    msg = "Canceled. Return back to /start_conversation."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    context.user_data.clear()
    return STOPPING


def main() -> None:
    """Run the bot."""
    application = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()

    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    start_handler = CommandHandler('start', start)
    restart_handler = CommandHandler('restart', restart)
    restrict_handler = MessageHandler(
        ~ filter_users, restrict
    )

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
            CREW_SELECT_ACTION: [CallbackQueryHandler(crew_select_action)],
        },
        fallbacks=[CommandHandler("cancel", stop_nested)],
    )

    departure_selction_handlers = [
        crew_action_handler,
        CallbackQueryHandler(list_departures, pattern="^" + str(BACK) + "$"),
        CallbackQueryHandler(stop_nested, pattern="^" + str(END) + "$")
    ]

    departure_action_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            # TODO: Split actions for Creation and Update
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
        entry_points=[
            CommandHandler("start_conversation", start_conversation)
        ],
        states={
            SHOWING: [CallbackQueryHandler(start_conversation,
                                           pattern="^" + str(END) + "$")],
            SELECT_ACTION: selection_handlers,
            STOPPING: [CommandHandler("stop", start_conversation)],
        },
        fallbacks=[CommandHandler("cancel", stop)],
    )

    application.add_handler(start_handler)
    application.add_handler(restart_handler)
    application.add_handler(restrict_handler)

    application.add_handler(info_handler)
    application.add_handler(help_handler)
    application.add_handler(action_handler)

    # unknown_handler has to be the last one
    application.add_handler(unknown_handler)

    application.run_polling()


if __name__ == '__main__':
    main()
