import os
import logging
import django
import datetime
from dateutil.parser import parse
from asgiref.sync import sync_to_async
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

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_dashboard.settings')
django.setup()

from django.conf import settings  # noqa: E402
from django.db.models import Q  # noqa: E402
from django.contrib.gis.geos import Point  # noqa: E402

from web_dashboard.logistics.models import Departure, Crew  # noqa: E402
from web_dashboard.search_requests.models import SearchRequest   # noqa: E402
from web_dashboard.users.models import CustomUser  # noqa: E402
from web_dashboard.bot_api.models import TelegramUser  # noqa E402

logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
setup_logging_config(settings.DEBUG)
logging.getLogger("httpcore").setLevel(logging.INFO)
logging.getLogger("telegram").setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)
logger.info(f'Start logging: {logger.getEffectiveLevel()}')

(
    SHOWING,
    SELECT_ACTION,
    STOPPING,

    INFO,
    HELP,

    CREW_CREATION,
    CREW_UPDATE,

    LIST_ITEM,
    DISPLAY_ITEM,
    SELECT_ITEM_ACTION,

    CREW_TITLE,
    CREW_LOCATION,
    CREW_CAPACITY,
    CREW_DEPARTURE_TIME,
    CREW_SELECT_ACTION,

    SELECT,
    BACK,
    START_OVER,  # TODO: Is it really required???
) = map(chr, range(18))

END = ConversationHandler.END


def get_allowed_users() -> set:
    """Return a set of allowed_users."""
    return set(CustomUser.objects.values_list('telegram_id', flat=True))


def get_formated_dtime(dtime: datetime.datetime) -> str:
    return dtime.strftime('%H:%M - %d.%m.%Y')


allowed_users = get_allowed_users()
filter_users = filters.User(user_id=allowed_users)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcoming a user at the joining."""
    msg = "I'm a Volunteer Rescue Bot!"

    user_id = update.effective_user.id

    # TODO: something is wrong with update
    await TelegramUser.objects.aupdate_or_create(
        user_id=user_id,
        last_action=datetime.datetime.now(datetime.UTC)
    )

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

        keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
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

    user_id = update.effective_user.id
    user = await CustomUser.objects.only('id').aget(telegram_id=user_id)
    context.user_data['user'] = user

    crews = Crew.objects.filter(status=Crew.StatusVerbose.AVAILABLE)
    user_crews = crews.filter(driver=user)
    context.user_data['user_crews'] = user_crews

    msg = f"Total number of crews: {await crews.acount()}"

    if await user_crews.aexists():
        lines = [
            get_formated_dtime(crew.pickup_datetime) + ": "
            + await sync_to_async(crew.__str__)()

            async for crew in user_crews.only('pickup_datetime')
            .order_by("pickup_datetime")
        ]

        msg += f"\n\nYour crews: {await user_crews.acount()}\n"
        msg += ('\n').join(lines)

    msg += "\n\nI'm a Volunteer Rescue Bot!\nWhat do you want to do?"

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

    if query:
        await query.answer()
        await query.edit_message_text(msg, reply_markup=keyboard)
    else:
        await update.message.reply_text(msg, reply_markup=keyboard)

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

    crews = await Crew.objects.filter(
        status=Crew.StatusVerbose.AVAILABLE
    ).acount()

    msg = (
        f'\n\n{SearchRequest._meta.verbose_name_plural}: {search_requests}'
        f'\n{Departure._meta.verbose_name_plural}: {departures}'
        f'\n{Crew._meta.verbose_name_plural}: {crews}'
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data=str(END))],
    ])

    if query:
        await query.answer()
        await query.edit_message_text(msg, reply_markup=keyboard)
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
        return END

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

    context.user_data['departures'] = departures
    context.user_data['dep_keyboards'] = keyboard

    await query.edit_message_text(
        f"Total number of departures: {len(departures)}\n"
        "Let's create a crew! Please choose Departure.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return DISPLAY_ITEM


async def display_departure(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display detailed information of the chosen departure with buttons."""
    query = update.callback_query
    await query.answer()

    index = int(query.data)
    dep = context.user_data['departures'][index]
    context.user_data['departure'] = dep

    # Display detailed information about the selected departure with buttons
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
        """
        # raw json:\n{dep.__dict__}\n
        # raw search_request:\n{dep.search_request.__dict__}\n
        # raw tasks:\n{dep.tasks.__dict__}
        #         """
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

    return SELECT_ITEM_ACTION


async def get_crew_keyboard(crew: Crew,
                            field: str = None) -> ReplyKeyboardMarkup:
    """Return keyboard for crew creation/edit steps."""
    value = getattr(crew, field)
    if isinstance(value, datetime.datetime):
        value = get_formated_dtime(value)
    elif isinstance(value, Point):
        value = f"{value.x}, {value.y}"

    buttons = {
        True: [[str(value)], ['/cancel']],
        False: [['/cancel']],
    }.get(bool(crew))
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


async def receive_departure(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> int:
    """ Display the selected departure and request to enter a crew name."""
    query = update.callback_query
    await query.answer()
    await query.delete_message()

    dep = context.user_data["departure"]
    crew = context.user_data.get('crew')

    if crew:
        msg = "Please edit the title of the crew or move to /next step:\n"\
            + crew.title

    else:
        context.user_data["crew"] = Crew()
        msg = (
                "You selected Departure:\n"
                f'ID {dep.pk} {dep.search_request.full_name}\n'
                f'Created at {get_formated_dtime(dep.created_at)}\n'

                "Please enter the title of the crew:"
        )
    keyboard = await get_crew_keyboard(crew, 'title')
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=msg,
                                   reply_markup=keyboard)
    return CREW_TITLE


async def receive_crew_title(update: Update,
                             context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Display the crew title and request to enter a pickup location.
    """
    crew = context.user_data["crew"]
    crew.title = update.message.text

    msg = f"Crew title: {crew.title}\n"\
          "Great! Now, please share the location of the crew"\
          " (e.g., address or coordinates)."
    if crew.pickup_location:
        msg += '\n' + crew.pickup_location

    keyboard = await get_crew_keyboard(crew, 'pickup_location')
    await update.message.reply_text(msg, reply_markup=keyboard)
    return CREW_LOCATION


async def receive_crew_location(update: Update,
                                context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Display the location and request to enter a crew capacity.
    """
    crew = context.user_data["crew"]
    # TODO: Validation or error message
    # Try and return back step if not working
    crew.pickup_location = Point(
        *list(map(float, update.message.text.split(',')))
    )

    msg = f"Location: {crew.pickup_location}\n"\
          "Awesome! How many passengers could you take:"
    if crew.passengers_max:
        msg += '\n' + str(crew.passengers_max)

    keyboard = await get_crew_keyboard(crew, 'passengers_max')
    await update.message.reply_text(msg, reply_markup=keyboard)
    return CREW_CAPACITY


async def receive_crew_capacity(update: Update,
                                context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Display crew capacity and request to enter a crew departure datetime.
    """
    crew = context.user_data["crew"]
    crew.passengers_max = update.message.text
    msg = f"Max passengers: {crew.passengers_max}\n"\
        "Finally! Set up pickup date, time & tz:"

    # TODO: Display available formats
    if crew.pickup_datetime:
        msg += '\n' + get_formated_dtime(crew.pickup_datetime)

    keyboard = await get_crew_keyboard(crew, 'pickup_datetime')
    await update.message.reply_text(msg, reply_markup=keyboard)
    return CREW_DEPARTURE_TIME


async def receive_crew_departure_datetime(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Display entered summary and next action buttons."""
    crew = context.user_data["crew"]
    msg = (
        f"Departure {crew.departure}\n\n"
        f"Crew title: '{crew.title}'!\n"
        f"Max passengers: {crew.passengers_max}\n"
        f"Pickup Location: {crew.pickup_location.coords}\n"
        f"Pickup datetime: {crew.pickup_datetime}\n\n"

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
    await query.delete_message()

    global SELECT, BACK, END

    try:
        user = await CustomUser.objects.aget(
            Q(telegram_id=user_id) & Q(has_car=True)
        )
    except CustomUser.DoesNotExist:
        msg = "You are not found in database or don't have a car."\
              "Please update your profile or contact Operator."
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=msg)
        logging.warning(f'TG_id={user_id}, User is not found in DB.')
        return END

    match answer:
        case str(SELECT):
            try:

                crew = context.user_data["crew"]
                crew.driver = user
                crew.status = Crew.StatusVerbose.AVAILABLE
                await crew.asave()
                msg = "Crew is created."

            except Exception as e:
                msg = "Unexpected error. Crew is NOT created."""
                logger.warning(e)

            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=msg)
            return END

        case str(BACK):
            return SHOWING

        case str(END):
            return END

        case _:
            return END


async def stop_nested(update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> int:
    """End nested conversation by command."""
    msg = "Canceled. Return back to /start_conversation."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    context.user_data.clear()
    return STOPPING


async def list_crews(update: Update,
                     context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display a list of all available crews."""
    query = update.callback_query
    await query.answer()

    crews = context.user_data['user_crews']

    if not await crews.aexists():
        await update.message.reply_text(
            "There are no available Crews to edit."
        )
        return END

    buttons = [
        [InlineKeyboardButton(
            f"{get_formated_dtime(crew.pickup_datetime)}: "
            f"{await sync_to_async(crew.__str__)()}",
            callback_data=str(crew.id)
        )]

        async for crew in crews.only('pickup_datetime')
    ]

    keyboard = InlineKeyboardMarkup(buttons)

    msg = f"Total number of existing crews: {await crews.acount()}\n\n"\
          "Please choose Crew to update:"

    await query.edit_message_text(msg, reply_markup=keyboard)
    return DISPLAY_ITEM


async def display_crew(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display detailed information of the chosen crew with buttons."""
    query = update.callback_query
    await query.answer()

    pk = int(query.data)
    crew = await context.user_data['user_crews']\
        .select_related('departure', 'departure__search_request').aget(pk=pk)

    context.user_data['crew'] = crew

    passengers = '\n'.join([
        f"{ps.full_name} {ps.phone_number} @{ps.telegram_id}"
        async for ps in crew.passengers.all()
    ])

    # Display detailed information about the selected crew with buttons
    dep = crew.departure
    context.user_data['departure'] = dep
    tasks = '\n'.join([
        f'* {task.title} - {task.coordinates.coords}:\n{task.description}'
        async for task in dep.tasks.all()
    ])

    sreq = dep.search_request

    msg = (
        f"""
Crew ID: {crew.id}
Crew Title: {crew.title}
Crew passengers:
{passengers}

Missing person: {sreq.full_name}
Diasappearance date: {sreq.disappearance_date}
Location: {sreq.city}
PSN: {sreq.location.coords}

Number of crews: {await dep.crews.acount()}

Tasks ({await crew.departure.tasks.acount()}):
{tasks}
        """
        # raw json:\n{dep.__dict__}\n
        # raw search_request:\n{dep.search_request.__dict__}\n
        # raw tasks:\n{dep.tasks.__dict__}
        #         """
    )

    buttons = [
        [
            InlineKeyboardButton("Edit", callback_data=str(SELECT)),
            InlineKeyboardButton("Back", callback_data=str(BACK)),
            InlineKeyboardButton("Cancel", callback_data=str(END)),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)

    return SELECT_ITEM_ACTION


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
                                           pattern="^" + str(BACK) + "$")],

            CREW_TITLE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receive_crew_title
                ),
            ],
            CREW_LOCATION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receive_crew_location
                ),
            ],
            CREW_CAPACITY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receive_crew_capacity
                ),
            ],
            CREW_DEPARTURE_TIME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_crew_departure_datetime
                ),
            ],

            CREW_SELECT_ACTION: [CallbackQueryHandler(crew_select_action)],
        },
        fallbacks=[CommandHandler("cancel", stop_nested)],
        map_to_parent={
            STOPPING: STOPPING
        },
    )

    crew_selection_handlers = [
        crew_action_handler,
        CallbackQueryHandler(list_departures, pattern=f"^{BACK}$"),
        CallbackQueryHandler(stop_nested, pattern=f"^{END}$")
    ]

    crew_update_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            list_crews, pattern=f"^{CREW_UPDATE}$"
        )],

        states={
            DISPLAY_ITEM: [CallbackQueryHandler(display_crew)],
            SELECT_ITEM_ACTION: crew_selection_handlers,
        },

        fallbacks=[CommandHandler("cancel", stop_nested)],
        map_to_parent={
            STOPPING: END
        },
    )

    crew_creation_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            list_departures, pattern=f"^{CREW_CREATION}$")],

        states={
            DISPLAY_ITEM: [CallbackQueryHandler(display_departure)],
            SELECT_ITEM_ACTION: crew_selection_handlers,
        },

        fallbacks=[CommandHandler("cancel", stop_nested)],
        map_to_parent={
            STOPPING: END
        },
    )

    selection_handlers = [
        crew_creation_handler,
        crew_update_handler,
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
