import os
import logging
import django
import datetime as dt
from dateutil.parser import parse
from asgiref.sync import sync_to_async

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    # ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    error
)

from telegram.ext import (
    filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
)

from tgbot.logging_config import setup_logging_config

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_dashboard.settings')
django.setup()

from django.conf import settings  # noqa: E402
# from django.db.models import Q  # noqa: E402
from django.contrib.gis.geos import Point  # noqa: E402
from django.utils import timezone  # noqa: E402

from web_dashboard.logistics.models import Departure, Crew  # noqa: E402
from web_dashboard.search_requests.models import SearchRequest   # noqa: E402
from web_dashboard.users.models import CustomUser  # noqa: E402
from web_dashboard.users.forms import TZOffsetHandler  # noqa: E402
from web_dashboard.bot_api.models import TelegramUser  # noqa E402

logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
setup_logging_config(settings.DEBUG)
logging.getLogger("httpcore").setLevel(logging.INFO)
logging.getLogger("telegram").setLevel(logging.INFO)
logging.getLogger("pudb").setLevel(logging.WARNING)
# logger.setLevel(logging.DEBUG)
logger.info(f'Start logging: {logger.getEffectiveLevel()}')


class ConversationStates:
    (
        SHOWING,
        SELECT_ACTION,
        STOPPING,

        INFO,
        HELP,
        SETTINGS,

        CHANGE_CAR_STATUS,
        CHANGE_LANGUAGE,
        CHANGE_TZ,

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

        DELETE,
        DEPART,
    ) = map(chr, range(23))

    END = ConversationHandler.END


CS = ConversationStates


def get_allowed_users() -> set:
    """Return a set of allowed_users."""
    return set(CustomUser.objects.values_list('telegram_id', flat=True))


def get_formated_dtime(dtime: dt.datetime) -> str:
    return dtime.strftime('%H:%M - %d.%m.%Y')


allowed_users = get_allowed_users()
filter_users = filters.User(user_id=allowed_users)


async def get_keyboard_cancel() -> ReplyKeyboardMarkup:
    """Return ReplyKeyboardMarkup with only /cancel button."""
    buttons = [
        ['/cancel']
    ]

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


async def get_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    extra_fields: set[str] = set()
) -> CustomUser:
    """Return user instance and record it to context if not present."""
    fields = {'id', 'telegram_id', 'timezone'}.union(extra_fields)

    if not extra_fields:
        if user := context.user_data.get('user'):
            return user

    user_id = update.effective_user.id
    user = await CustomUser.objects.only(*fields).aget(telegram_id=user_id)
    context.user_data['user'] = user
    return user


# Authorization
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcoming a user at the joining."""
    msg = "I'm a Volunteer Rescue Bot!"

    user_id = update.effective_user.id

    # TODO: something is wrong with update
    await TelegramUser.objects.aupdate_or_create(
        user_id=user_id,
        last_action=dt.datetime.now(dt.UTC)
    )

    global allowed_users
    if user_id not in allowed_users:
        msg = f'Here is your Telegram ID: {user_id}'
        await context.bot.send_message(text=msg,
                                       chat_id=update.effective_chat.id)
    else:
        msg = '/start_conversation'
        await context.bot.send_message(
            text=msg,
            chat_id=update.effective_chat.id,
            reply_markup=await get_keyboard_cancel()
        )


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


# Start of conversation
async def start_conversation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Welcoming a user at the joining."""
    query = update.callback_query

    user = await get_user(update, context)
    crews = Crew.objects.exclude(status=Crew.StatusVerbose.COMPLETED)
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

        msg += f"\n\nYour crews: {await user_crews.acount()}\n\t"
        msg += ('\n\t').join(lines)

    msg += "\n\nI'm a Volunteer Rescue Bot!\nWhat do you want to do?"

    buttons = [
        [
            InlineKeyboardButton('Info', callback_data=CS.INFO),
            InlineKeyboardButton('Help', callback_data=CS.HELP),
        ],
        [
            InlineKeyboardButton('Settings', callback_data=CS.SETTINGS),
        ],
        [
            InlineKeyboardButton('Create crew',
                                 callback_data=CS.CREW_CREATION),
            InlineKeyboardButton('Update crew',
                                 callback_data=CS.CREW_UPDATE),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)

    if query:
        await query.answer()
        await query.edit_message_text(msg, reply_markup=keyboard)
    else:
        await update.message.reply_text(msg, reply_markup=keyboard)

    return CS.SELECT_ACTION


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
        [InlineKeyboardButton("Back", callback_data=str(CS.END))],
    ])

    if query:
        await query.answer()
        await query.edit_message_text(msg, reply_markup=keyboard)
        return CS.SHOWING
    else:
        await update.message.reply_text(msg)


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
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
        [InlineKeyboardButton("Back", callback_data=str(CS.END))],
    ])

    if query:
        await query.answer()
        await query.edit_message_text(msg, reply_markup=keyboard)
        return CS.SHOWING
    else:
        await update.message.reply_text(msg)


async def settings_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Display settings menu."""
    query = update.callback_query
    await query.answer()
    user = await get_user(
        update,
        context,
        {
            'first_name',
            'last_name',
            'patronymic_name',
            'has_car',
            'telegram_id',
            'timezone',
        }
    )

    # TODO: Feature to display language
    # TZ for a user
    msg = f"""
Full name: {user.full_name}
Car: {'Yes' if user.has_car else 'No'}
Language:
Time zone: {user.tz}

Please select what you want to change:
    """

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "Car status", callback_data=CS.CHANGE_CAR_STATUS
        )],
        [InlineKeyboardButton(
            "Language", callback_data=CS.CHANGE_LANGUAGE
        )],
        [InlineKeyboardButton(
            "Time zone", callback_data=CS.CHANGE_TZ
        )],
        [InlineKeyboardButton(
            "Back", callback_data=CS.SHOWING
        )],
    ])

    await query.answer()
    await query.edit_message_text(msg, reply_markup=keyboard)
    return CS.SETTINGS


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End conversation by command."""
    msg = "Canceled. Return back to /start_conversation."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    context.user_data.clear()
    return CS.END


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return unknown command message if a command is not found."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I didn't understand that command."
    )


# Crew creation
async def list_departures(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Display a list of all departures with open status."""
    query = update.callback_query
    await query.answer()

    departures = Departure.objects.filter(status=Departure.StatusVerbose.OPEN)\
        .select_related('search_request')

    if not await departures.aexists():
        await update.message.reply_text(
            "There are no available Departures, please try later."
        )
        return CS.END

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
    return CS.DISPLAY_ITEM


async def display_departure(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Display detailed information of the chosen departure with buttons."""
    query = update.callback_query
    await query.answer()

    index = int(query.data)
    dep = context.user_data['departures'][index]
    context.user_data['departure'] = dep

    # Display detailed information about the selected departure with buttons
    tasks = '\n'.join([
        f'* {task.title} - {task.coordinates.coords}:\n\t\t{task.description}'
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
            InlineKeyboardButton("Select", callback_data=CS.SELECT),
            InlineKeyboardButton("Back", callback_data=CS.BACK),
            InlineKeyboardButton("Cancel", callback_data=str(CS.END)),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)

    return CS.SELECT_ITEM_ACTION


# Crew creation & update
async def get_keyboard_crew(
    crew: Crew,
    field: str = None
) -> ReplyKeyboardMarkup:
    """Return keyboard for crew creation/edit steps."""
    value = getattr(crew, field)
    buttons = {
        True: [['>>> Next >>>'], ['/cancel']],
        False: [['/cancel']],
    }.get(bool(value))

    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )


async def receive_departure(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """ Display the selected departure and request to enter a crew name."""
    query = update.callback_query
    await query.answer()
    await query.delete_message()

    crew = context.user_data.get('crew', Crew())

    if getattr(crew, 'title'):
        msg = "Please edit the title of the crew:\n"\
            + crew.title

    else:
        crew.departure = context.user_data["departure"]
        context.user_data["crew"] = crew
        msg = f"""
Selected Departure:
    ID {crew.departure.pk} {crew.departure.search_request.full_name}
    Created at {get_formated_dtime(crew.departure.created_at)}

Please enter the title of the crew:
        """
        if title := getattr(crew, 'title'):
            msg += '\n' + title
    keyboard = await get_keyboard_crew(crew, 'title')
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=msg,
                                   reply_markup=keyboard)
    return CS.CREW_TITLE


async def receive_crew_title(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Display the crew title and request to enter a pickup location.
    """
    crew = context.user_data["crew"]
    answer = update.message.text
    if answer != '>>> Next >>>':
        crew.title = answer

    msg = f"Crew title: {crew.title}\n\n"\
          "Great! Now, please share the location of the crew"\
          " (e.g., address or coordinates)."
    if crew.pickup_location:
        msg += f'\n{crew.pickup_location.coords}'

    keyboard = await get_keyboard_crew(crew, 'pickup_location')
    await update.message.reply_text(msg, reply_markup=keyboard)
    return CS.CREW_LOCATION


async def receive_crew_location(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Display the location and request to enter a crew capacity.
    """
    crew = context.user_data["crew"]
    # TODO: Validation or error message
    # Try and return back step if not working
    answer = update.message.text
    if answer != '>>> Next >>>':
        crew.pickup_location = Point(
            *list(map(float, answer.split(',')))
        )

    msg = f"Location: {crew.pickup_location.coords}\n\n"\
          "Awesome! How many passengers could you take:"
    if crew.passengers_max:
        msg += '\n' + str(crew.passengers_max)

    keyboard = await get_keyboard_crew(crew, 'passengers_max')
    await update.message.reply_text(msg, reply_markup=keyboard)
    return CS.CREW_CAPACITY


async def receive_crew_capacity(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Display crew capacity and request to enter a crew departure datetime.
    """
    crew = context.user_data["crew"]
    answer = update.message.text
    if answer != '>>> Next >>>':
        crew.passengers_max = answer

    user = await get_user(update, context)
    msg = f"Max passengers: {crew.passengers_max}\n\n"\
        "Finally! Set up pickup date & time: `DD.MM.YYYY HH:MM"

    # TODO: Display available formats
    if crew.pickup_datetime:
        msg += f'\n{timezone.localtime(crew.pickup_datetime, user.tz)}'

    keyboard = await get_keyboard_crew(crew, 'pickup_datetime')
    await update.message.reply_text(msg, reply_markup=keyboard)
    return CS.CREW_DEPARTURE_TIME


async def get_crew_public_info(crew: Crew, tz: dt.timezone) -> str:
    """Return public crew info."""
    msg = f"""
Departure {crew.departure}

Crew title: '{crew.title}'
Max passengers: {crew.passengers_max}
Pickup location: {crew.pickup_location.coords}
Pickup datetime: {timezone.localtime(crew.pickup_datetime, tz)}
    """
    return msg


async def receive_crew_pickup_dt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Display entered summary and next action buttons."""
    crew = context.user_data["crew"]
    user = await get_user(update, context)
    answer = update.message.text
    if answer != '>>> Next >>>':
        crew.pickup_datetime = parse(answer).replace(tzinfo=user.tz)

    msg = await get_crew_public_info(crew, user.tz)\
        + '\n\nPlease select the next action.'

    buttons = [
        [
            InlineKeyboardButton("Save", callback_data=CS.SELECT),
            InlineKeyboardButton("Edit", callback_data=CS.BACK),
            InlineKeyboardButton("Cancel", callback_data=str(CS.END))
        ],
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(msg, reply_markup=keyboard)
    return CS.CREW_SELECT_ACTION


async def make_broadcast(
    context: ContextTypes,
    message: str,
    users: list[int] = allowed_users
) -> None:
    """Broadcast message to all allowed users."""
    for user_id in allowed_users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except error.Forbidden:
            logger.warning(f'User has blocked the bot. TG: {user_id}')
        except Exception as e:
            logger.warning(
                "Unexpected error. User doesn't receive broadcast msg. "
                f'TG: {user_id}, Error: {e}'
            )


async def crew_save_or_update(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Save or update crew instance."""
    query = update.callback_query
    await query.answer()

    user = await get_user(update, context)

    await query.delete_message()
    try:
        crew = context.user_data["crew"]
        crew.driver = user
        crew.status = Crew.StatusVerbose.AVAILABLE

        if getattr(crew, 'id') is None:
            msg = "Created"
        else:
            msg = "Updated"
        await crew.asave()

        broadcast_msg = f'Crew is available ({msg}).\n\n'\
            + await get_crew_public_info(crew, user.tz)
        await make_broadcast(context, broadcast_msg)

    except CustomUser.DoesNotExist:
        msg = "You are not found in database or don't have a car."\
              "Please update your profile or contact Operator."

        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=msg
        )
        logging.warning(f'TG_id: {user.telegram_id}, User is not found in DB.')
        return CS.END

    except Exception as e:
        msg = "Unexpected error. Crew is NOT created.\nTG: {user_id}, {e=}"
        logger.warning(e)
        return CS.END

    msg += '\nReturn back to /start_conversation.'
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=msg)
    context.user_data.clear()
    return CS.STOPPING


async def stop_nested(update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> int:
    """End nested conversation by command."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.delete_message()
    msg = "Canceled. Return back to /start_conversation."
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=msg,
                                   reply_markup=await get_keyboard_cancel())
    context.user_data.clear()
    return CS.STOPPING


# Crew update
async def list_crews(update: Update,
                     context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display a list of all available crews."""
    query = update.callback_query
    await query.answer()
    if context.user_data.get('crew'):
        del context.user_data['crew']

    crews = context.user_data['user_crews']

    if not await crews.aexists():
        await update.message.reply_text(
            "There are no available Crews to edit."
        )
        return CS.END

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
    return CS.DISPLAY_ITEM


async def get_crew_info(crew: CustomUser, tz: dt.timezone) -> str:
    """Display only the crew information."""

    passengers = '\n'.join([
        f"{ps.full_name} {ps.phone_number} @{ps.telegram_id}"
        async for ps in crew.passengers.all()
    ])

    info = f"""
__ Information __

**** Crew ****
Status: {crew.status}
ID: {crew.id}
Title: {crew.title}
Pickup time: {timezone.localtime(crew.pickup_datetime, tz)}
Pickup location: {crew.pickup_location.coords}

**** Passengers ({await crew.passengers.acount()}) ****
{passengers}
    """
    return info


async def display_crew(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display detailed information of the chosen crew with buttons."""
    query = update.callback_query
    await query.answer()
    user = await get_user(update, context)

    if context.user_data.get('crew'):
        crew = context.user_data['crew']

    else:
        pk = int(query.data)
        crew = await context.user_data['user_crews']\
            .select_related('departure', 'departure__search_request')\
            .aget(pk=pk)

        context.user_data['crew'] = crew

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
{await get_crew_info(crew, user.tz)}
**** Search Request ****
Missing person: {sreq.full_name}
Diasappearance date: {sreq.disappearance_date}
Location: {sreq.city}
PSN: {sreq.location.coords}

**** Departure ****
Number of crews: {await dep.crews.acount()}

**** Tasks ({await crew.departure.tasks.acount()}) ****
{tasks}
        """
        # raw json:\n{dep.__dict__}\n
        # raw search_request:\n{dep.search_request.__dict__}\n
        # raw tasks:\n{dep.tasks.__dict__}
        #         """
    )

    buttons = [
        [
            InlineKeyboardButton("Depart", callback_data=CS.DEPART),
        ],
        [
            InlineKeyboardButton("Delete", callback_data=CS.DELETE),
        ],
        [
            InlineKeyboardButton("Edit", callback_data=CS.SELECT),
            InlineKeyboardButton("Back", callback_data=CS.BACK),
            InlineKeyboardButton("Cancel", callback_data=CS.END),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)

    return CS.SELECT_ITEM_ACTION


async def crew_delete_confirmation(update: Update,
                                   context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display crew information and ask to confirm deletion."""
    query = update.callback_query
    await query.answer()

    user = get_user(update, context)
    crew = context.user_data['crew']

    msg = f'Do you want to delete crew: {crew.pk} {crew.title}\n'\
          + await get_crew_info(crew, user.tz)

    buttons = [
        [
            InlineKeyboardButton("Yes", callback_data=CS.DELETE),
            InlineKeyboardButton("No", callback_data=CS.BACK),
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)
    return CS.DELETE


async def crew_delete(update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> int:
    """Delete crew instance."""
    query = update.callback_query
    await query.answer()
    crew = context.user_data['crew']
    pk = crew.pk
    try:
        await crew.adelete()
        del context.user_data['crew']
    except Exception as e:  # TODO: specify deletion error
        logger.warning('Crew deletion error\n,'
                       f'TG: {query.from_user.id}, Crew: {pk},\n{e=}')

    msg = f"Deleted crew: {pk}"
    buttons = [
        [
            InlineKeyboardButton("Back", callback_data=CS.BACK),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)
    return CS.SELECT_ITEM_ACTION


async def crew_depart(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Switch crew instance status and make notification."""
    query = update.callback_query
    await query.answer()
    crew = context.user_data['crew']
    user = await get_user(update, context)
    try:
        crew.status = Crew.StatusVerbose.ON_MISSION
        crew.departure_datetime = dt.datetime.now(tz=user.tz)
        await crew.asave()
        # TODO: log event
    except Exception as e:  # TODO: specify deletion error
        logger.warning("Can't change crew status to ON_MISSION"
                       f'TG: {query.from_user.id}, Crew: {crew.pk}, {e=}')

    msg = f"Crew {crew.title}-{crew.pk} departured"
    buttons = [
       [
            InlineKeyboardButton("Back", callback_data=CS.BACK),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)
    return CS.SELECT_ITEM_ACTION


# User settings
async def change_tz(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Change user timezone."""
    query = update.callback_query
    await query.answer()
    # await query.delete_message()

    user = context.user_data['user']

    msg = 'You current TZ: '\
        f'{TZOffsetHandler.represent_tz_offset(user.timezone)}\n'\
        "Please enter your current Time Zone realtive to UTC\n"\
        "Format: ±HH:MM"

    buttons = [['Back'], ['/cancel']]
    keyboard = ReplyKeyboardMarkup(buttons, one_time_keyboard=True)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=msg,
                                   reply_markup=keyboard)
    return CS.CHANGE_TZ


async def receive_user_tz(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Receive timezone reply and save it."""
    user = context.user_data["user"]
    tz = update.message.text
    try:
        user.timezone = TZOffsetHandler.normalize_tz_offset(tz)
        await user.asave()
    except Exception as e:
        logger.warning(f'TG: {update.from_user.id}, {e}')
        msg = 'Please type correct Time Zone format.'

    msg = f"Timezone is updated: {tz}"
    buttons = [
        [
            InlineKeyboardButton("Back", callback_data=CS.SETTINGS),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(msg, reply_markup=keyboard)
    return CS.SELECT_ACTION


async def change_language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Change user language."""
    pass


async def change_car_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Change user car status."""
    query = update.callback_query
    await query.answer()

    user = context.user_data['user']
    try:
        user.has_car = not user.has_car
        await user.asave()
        msg = 'Car status is changed.'
    except Exception as e:
        logging.warning(f'Status is not changed. TG: {user.telegram_id}, {e}')
        msg = f'Status is not changed. {e}'

    buttons = [
        [
            InlineKeyboardButton("Back", callback_data=CS.SETTINGS),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)
    return CS.SELECT_ACTION


def main() -> None:
    """Run the bot."""
    application = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()

    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    start_handler = CommandHandler('start', start)
    restart_handler = CommandHandler('restart', restart)
    restrict_handler = MessageHandler(~ filter_users, restrict)

    info_handler = CommandHandler('info', info)
    help_handler = CommandHandler('help', help_command)

    crew_action_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            receive_departure, pattern=f"^{CS.SELECT}$"
        )],

        states={
            CS.SHOWING: [
                CallbackQueryHandler(receive_departure,
                                     pattern=f"^{CS.BACK}$")
            ],

            CS.CREW_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               receive_crew_title),
            ],
            CS.CREW_LOCATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               receive_crew_location),
            ],
            CS.CREW_CAPACITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               receive_crew_capacity),
            ],
            CS.CREW_DEPARTURE_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               receive_crew_pickup_dt),
            ],

            CS.CREW_SELECT_ACTION: [
                CallbackQueryHandler(crew_save_or_update,
                                     pattern=f'^{CS.SELECT}$'),
                CallbackQueryHandler(receive_departure,
                                     pattern=f'^{CS.BACK}$'),
                CallbackQueryHandler(stop_nested,
                                     pattern=f'^{CS.END}$'),
            ],
        },
        fallbacks=[CommandHandler("cancel", stop_nested)],
        map_to_parent={
            CS.STOPPING: CS.STOPPING,
            CS.SHOWING: CS.SHOWING
        },
    )

    crew_update_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            list_crews, pattern=f"^{CS.CREW_UPDATE}$"
        )],

        states={
            CS.DISPLAY_ITEM: [CallbackQueryHandler(display_crew)],
            CS.SELECT_ITEM_ACTION: [
                crew_action_handler,
                CallbackQueryHandler(crew_delete_confirmation,
                                     pattern=f"^{CS.DELETE}$"),

                CallbackQueryHandler(crew_depart,
                                     pattern=f"^{CS.DEPART}$"),
                CallbackQueryHandler(list_crews, pattern=f"^{CS.BACK}$"),
                CallbackQueryHandler(stop_nested, pattern=f"^{CS.END}$")
            ],
            CS.DELETE: [
                CallbackQueryHandler(crew_delete, pattern=f"^{CS.DELETE}$"),
                CallbackQueryHandler(display_crew, pattern=f"^{CS.BACK}$"),
            ]
        },

        fallbacks=[CommandHandler("cancel", stop_nested)],
        map_to_parent={
            CS.STOPPING: CS.END,
            CS.SHOWING: CS.SHOWING
        },
    )

    crew_create_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            list_departures, pattern=f"^{CS.CREW_CREATION}$")],

        states={
            CS.DISPLAY_ITEM: [CallbackQueryHandler(display_departure)],
            CS.SELECT_ITEM_ACTION: [
                crew_action_handler,
                CallbackQueryHandler(list_departures, pattern=f"^{CS.BACK}$"),
                CallbackQueryHandler(stop_nested, pattern=f"^{CS.END}$")
            ],
        },

        fallbacks=[CommandHandler("cancel", stop_nested)],
        map_to_parent={
            CS.STOPPING: CS.END,
            CS.SHOWING: CS.SHOWING
        },
    )

    action_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start_conversation", start_conversation)
        ],
        states={
            CS.SHOWING: [
                CallbackQueryHandler(start_conversation, pattern=f"^{CS.END}$")
            ],
            CS.SELECT_ACTION: [
                crew_create_handler,
                crew_update_handler,
                CallbackQueryHandler(info, pattern=f"^{CS.INFO}$"),
                CallbackQueryHandler(help_command, pattern=f"^{CS.HELP}$"),
                CallbackQueryHandler(
                    settings_command,
                    pattern=f"^{CS.SETTINGS}$"
                ),
            ],
            CS.SETTINGS: [
                CallbackQueryHandler(
                    change_car_status, pattern=f"^{CS.CHANGE_CAR_STATUS}"
                ),
                CallbackQueryHandler(
                    change_tz, pattern=f"^{CS.CHANGE_TZ}"
                ),
                CallbackQueryHandler(
                    change_language, pattern=f"^{CS.CHANGE_LANGUAGE}"
                ),
                CallbackQueryHandler(
                    start_conversation, pattern=f"^{CS.SHOWING}"
                ),
            ],
            CS.CHANGE_TZ: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_user_tz
                ),
            ],
            CS.STOPPING: [CommandHandler("stop", start_conversation)],
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

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
