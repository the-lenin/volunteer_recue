import os
import logging
import django
import re
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

from warnings import filterwarnings
from telegram.warnings import PTBUserWarning

from tgbot.logging_config import setup_logging_config

filterwarnings(
    action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning
)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_dashboard.settings')
django.setup()

from django.conf import settings  # noqa: E402
from django.db.models import F, Q  # noqa: E402
from django.contrib.gis.geos import Point  # noqa: E402
from django.contrib.gis.db.models.functions import Distance  # noqa: E402
from django.utils import timezone  # noqa: E402
from django.db.models.query import QuerySet  # noqa: E402
from django.db.models import Count  # noqa: E402

from web_dashboard.logistics.models import (  # noqa: E402
    Departure,
    Crew,
    JoinRequest
)
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
        CREW_JOINING,
        CREW_MANAGE_JOINED,
        CREW_ARCHIVE,

        LIST_ITEM,
        DISPLAY_ITEM,
        SELECT_ITEM_ACTION,
        RECEIVE_FILE,

        CREW_TITLE,
        CREW_LOCATION,
        CREW_CAPACITY,
        CREW_DEPARTURE_TIME,
        CREW_SELECT_ACTION,
        CREW_MANAGE_PASSENGERS,

        SELECT,
        BACK,

        ACCEPT,
        REJECT,

        DELETE,
        STATUS,
    ) = map(chr, range(30))

    END = ConversationHandler.END


CS = ConversationStates


def get_coordinates(psn: str) -> tuple[float]:
    """Parse coordinates string, validate it and return tuple (lat, long)."""
    pattern = r'([-+]?\d*\.?\d+)[,\s]*([-+]?\d*\.?\d+)'
    matches = re.findall(pattern, psn)

    if matches:
        lat, long = list(map(float, matches[0]))

        if all((bool(-90 <= lat <= 90), bool(-180 <= long <= 180))):
            return lat, long

        raise ValueError(
            "Exceed limit. -180 <= Latitude <= 180. -90 <= Longitude <= 90."
        )

    else:
        raise ValueError("Invalid coordinates format. `Latitude, Longitude`.")


def get_allowed_users() -> set:
    """Return a set of allowed_users."""
    return set(CustomUser.objects.values_list('telegram_id', flat=True))


def get_formated_dtime(dtime: dt.datetime, tz=False) -> str:
    if tz:
        timestr = dtime.strftime('%d.%m.%Y - %H:%M (UTC %z)')
        return timestr[:-3] + ':' + timestr[-3:]
    return dtime.strftime('%d.%m.%Y - %H:%M ')


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
    fields = {
        'id',
        'telegram_id',
        'timezone',
        'has_car',

        'first_name',
        'last_name',
        'patronymic_name',
        'nickname',
    }.union(extra_fields)

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

    await TelegramUser.objects.aupdate_or_create(
        user_id=user_id,
        defaults={'last_action': dt.datetime.now(dt.UTC)}
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
    """Start top level conversation handler."""

    query = update.callback_query

    user = await get_user(update, context)
    crews = Crew.objects.exclude(status=Crew.StatusVerbose.COMPLETED)
    user_crews = crews.filter(driver=user).prefetch_related('driver')
    context.user_data['user_crews'] = user_crews

    time = get_formated_dtime(dt.datetime.now(tz=user.tz), tz=True)
    msg = f"🕰️ Now: {time} 🕰️\nTotal number of crews: {await crews.acount()}"

    if await user_crews.aexists():
        lines = [
            f"{get_formated_dtime(timezone.localtime(crew.pickup_datetime, user.tz))}: "  # noqa: E501
            f"{crew.__str__()}: {crew.passengers_count} p."

            async for crew in crews.only(
                'title', 'pickup_datetime', 'status',
            ).annotate(passengers_count=Count('passengers'))
        ]

        msg += f"\n\nYour crews: {await user_crews.acount()}\n\t"
        msg += ('\n\t').join(lines)

    msg += "\n\nI'm a Volunteer Rescue Bot!\nWhat do you want to do?"

    buttons = [
        [
            InlineKeyboardButton('🆕 Reload', callback_data=CS.SHOWING)
        ],
        [
            InlineKeyboardButton('ℹ️ Info', callback_data=CS.INFO),
            InlineKeyboardButton('🆘 Help', callback_data=CS.HELP),
        ],
        [
            InlineKeyboardButton('⚙ Settings', callback_data=CS.SETTINGS),
        ],
    ]

    if user.has_car:
        buttons.append([
            InlineKeyboardButton('🏗️ Create crew',
                                 callback_data=CS.CREW_CREATION),
            InlineKeyboardButton('🔄 Update crew',
                                 callback_data=CS.CREW_UPDATE),
        ])
    buttons.append([
        InlineKeyboardButton('➕ Join crew',
                             callback_data=CS.CREW_MANAGE_PASSENGERS),
    ])

    if await user.join_requests.aexists():
        buttons[-1].append(InlineKeyboardButton(
            '📝 Manage joined crews', callback_data=CS.CREW_MANAGE_JOINED
        ))

    buttons.append([
        InlineKeyboardButton('📜 Archive',
                             callback_data=CS.CREW_ARCHIVE),
    ])

    keyboard = InlineKeyboardMarkup(buttons)

    if query:
        await query.answer()
        await query.delete_message()

    await update.effective_chat.send_message(msg, reply_markup=keyboard)

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
        [InlineKeyboardButton("🔙 Back", callback_data=str(CS.END))],
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
        [InlineKeyboardButton("🔙 Back", callback_data=str(CS.END))],
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
    if query:
        await query.answer()
        await query.delete_message()

    user = await get_user(
        update,
        context,
        {
            'first_name',
            'last_name',
            'patronymic_name',
        }
    )

    # TODO: Feature to display language
    # TZ for a user
    msg = f"""
Full name: {user.full_name}
Car: {'🚙 Yes' if user.has_car else '🚶 No'}
Language:
Time zone: {user.tz}

Please select what you want to change:
    """

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🚙 Car status", callback_data=CS.CHANGE_CAR_STATUS
        )],
        [InlineKeyboardButton(
            "🌐 Language", callback_data=CS.CHANGE_LANGUAGE

        )],
        [InlineKeyboardButton(
            "🕰 Time zone", callback_data=CS.CHANGE_TZ
        )],
        [InlineKeyboardButton(
            "🔙 Back", callback_data=CS.SHOWING
        )],
    ])

    await update.effective_chat.send_message(msg, reply_markup=keyboard)
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
            InlineKeyboardButton("☑️ Select", callback_data=CS.SELECT),
            InlineKeyboardButton("🔙 Back", callback_data=CS.BACK),
            InlineKeyboardButton("❌ Cancel", callback_data=str(CS.END)),
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
    """ Display the location and request to enter a crew capacity."""
    crew = context.user_data["crew"]
    # TODO: Validation or error message
    # Try and return back step if not working
    answer = update.message.text
    if answer != '>>> Next >>>':
        crew.pickup_location = Point(get_coordinates(answer))

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
            InlineKeyboardButton("✅ Save", callback_data=CS.SELECT),
            InlineKeyboardButton("🔧 Edit", callback_data=CS.BACK),
            InlineKeyboardButton("❌ Cancel", callback_data=str(CS.END))
        ],
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(msg, reply_markup=keyboard)
    return CS.CREW_SELECT_ACTION


async def make_broadcast(
    context: ContextTypes,
    message: str,
    users: list[int] | int = allowed_users
) -> None:
    """Broadcast message to all allowed users."""
    if isinstance(users, int):
        users = [users]

    for user_id in users:
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

        broadcast_msg = f'📢 Crew is available ({msg}). 📢\n\n'\
            + await get_crew_public_info(crew, user.tz)
        await make_broadcast(context, broadcast_msg)

    except CustomUser.DoesNotExist:
        msg = "You are not found in database or don't have a car."\
              "Please update your profile or contact Operator."

        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=msg
        )
        logging.warning(f'TG_id: {user.telegram_id}, User is not found in DB.')
        return CS.SHOWING

    except Exception as e:
        msg = "Unexpected error. Crew is NOT created.\nTG: {user_id}, {e=}"
        logger.warning(e)
        return CS.SHOWING

    msg += '\nReturn back to Main menu.'

    buttons = [[InlineKeyboardButton("🔙 Back", callback_data=CS.BACK)]]
    keyboard = InlineKeyboardMarkup(buttons)
    await update.effective_chat.send_message(msg, reply_markup=keyboard)

    context.user_data.clear()
    return CS.SHOWING


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
async def get_keyboard_crew_list(
    crews: QuerySet[list[Crew]],
    distance: bool = False
) -> InlineKeyboardMarkup:
    """Return a list of crew as Keyboard with buttons and callback."""
    if not distance:
        buttons = [
            [InlineKeyboardButton(
                f"{get_formated_dtime(crew.pickup_datetime)}: "
                f"{crew.__str__()}: {crew.passengers_count} p.",
                callback_data=str(crew.id)
            )]

            async for crew in crews.only(
                'title', 'pickup_datetime', 'status',
            ).annotate(passengers_count=Count('passengers'))
        ]
    else:
        buttons = [
            [InlineKeyboardButton(
                f"{get_formated_dtime(crew.pickup_datetime)}: "
                f"{crew.__str__()}: {crew.passengers_count} p. "
                f"({crew.distance.km:.2f} km)",
                callback_data=str(crew.id)
            )]

            async for crew in crews.only(
                'title', 'pickup_datetime', 'status',
            ).annotate(passengers_count=Count('passengers'))
        ]
    # buttons.append([
    #     InlineKeyboardButton("🔙 Back", callback_data=CS.BACK),
    #     InlineKeyboardButton("❌ Cancel", callback_data=str(CS.END))
    # ])

    keyboard = InlineKeyboardMarkup(buttons)
    return keyboard


async def list_crews(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Display a list of all available crews."""
    query = update.callback_query
    await query.answer()
    if context.user_data.get('crew'):
        del context.user_data['crew']

    crews = context.user_data['user_crews']

    btn_bottom_row = [[
        InlineKeyboardButton("🔙 Back", callback_data=CS.BACK),
        # InlineKeyboardButton("❌ Cancel", callback_data=CS.END)
    ]]

    if not await crews.aexists():
        msg = "There are no available Crews to edit."
        keyboard = InlineKeyboardMarkup(btn_bottom_row)
        await query.edit_message_text(msg, reply_markup=keyboard)
        return CS.SHOWING

    keyboard = await get_keyboard_crew_list(crews)
    msg = f"Total number of existing crews: {await crews.acount()}\n\n"\
          "Please choose Crew to update:"

    await query.edit_message_text(msg, reply_markup=keyboard)
    return CS.DISPLAY_ITEM


async def get_crew_info(crew: Crew, tz: dt.timezone) -> str:
    """Display only the crew information."""

    passengers = '\n'.join([
        f"{ps.nickname if ps.nickname else ps.full_name} "
        f"{ps.phone_number} @{ps.telegram_id}"
        async for ps in crew.passengers.all()
    ])

    d = crew.driver

    info = f"""
__ Information __

**** Crew ****
Status: {crew.get_status_display()}
ID: {crew.id}
Title: {crew.title}
Pickup time: {timezone.localtime(crew.pickup_datetime, tz)}
Pickup location: {crew.pickup_location.coords}

    Driver
Nickname: {d.nickname if d.nickname else d.full_name}
Phone: {d.phone_number}
Telegram: # TODO: add @Username

**** Passengers ({await crew.passengers.acount()}) ****
{passengers}
    """
    return info


async def get_crew_detailed_info(crew: Crew, tz: dt.timezone) -> str:
    """Display the crew and related information."""
    dep = crew.departure
    tasks = '\n'.join([
        f'* {task.title} - {task.coordinates.coords}:\n{task.description}'
        async for task in dep.tasks.all()
    ])

    sreq = dep.search_request

    msg = (
        f"""
{await get_crew_info(crew, tz)}
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
    return msg


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
        context.user_data['departure'] = crew.departure

    join_requests = JoinRequest.objects.filter(crew=crew)\
        .exclude(status=JoinRequest.StatusVerbose.ACCEPTED)

    if await join_requests.aexists():
        pending = await join_requests.filter(
            status=JoinRequest.StatusVerbose.PENDING
        ).acount()

        rejected = await join_requests.filter(
            status=JoinRequest.StatusVerbose.REJECTED
        ).acount()
        msg = f'📥 Join requests: ({pending}) 📥\n'\
            f'Pending: {pending}\nRejected: {rejected}\n'\
            f'Accepted: {await crew.passengers.acount()}/{crew.passengers_max}'

    else:
        msg = ''

    msg += await get_crew_detailed_info(crew, user.tz)

    match crew.status:
        case crew.StatusVerbose.AVAILABLE:
            label = "Depart"
        case crew.StatusVerbose.ON_MISSION:
            label = "Return"
        case crew.StatusVerbose.RETURNING:
            label = "Complete"
        case _:
            label = None

    buttons = []

    if label:
        buttons.append(
            [InlineKeyboardButton('🏷️ ' + label, callback_data=CS.STATUS)]
        )

    buttons.extend([
        [
            InlineKeyboardButton('🛂 Manage passengers',
                                 callback_data=CS.CREW_MANAGE_PASSENGERS)
        ],
        [
            InlineKeyboardButton("⚠ Delete", callback_data=CS.DELETE)
        ],
        [
            InlineKeyboardButton("🔧 Edit", callback_data=CS.SELECT),
            InlineKeyboardButton("🔙 Back", callback_data=CS.BACK),
            InlineKeyboardButton("❌ Cancel", callback_data=CS.END),
        ]
    ])

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)

    return CS.SELECT_ITEM_ACTION


async def crew_delete_confirmation(update: Update,
                                   context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display crew information and ask to confirm deletion."""
    query = update.callback_query
    await query.answer()

    user = await get_user(update, context)
    crew = context.user_data['crew']

    msg = f'Do you want to delete crew: {crew.title}-{crew.pk}?\n'\
          + await get_crew_info(crew, user.tz)

    buttons = [
        [
            InlineKeyboardButton("🗑️ Yes", callback_data=CS.DELETE),
            InlineKeyboardButton("🔙 No", callback_data=CS.BACK),
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
    title = f'{crew.title}-{crew.pk}'

    try:
        msg = f"Deleted crew: {title}"
        await crew.adelete()
        del context.user_data['crew']
    except Exception as e:  # TODO: specify deletion error
        logger.warning('Crew deletion error\n,'
                       f'TG: {query.from_user.id}, Crew: {title},\n{e=}')
        msg = f'Crew deletion error.\n{e}'

    buttons = [
        [
            InlineKeyboardButton("🔙 Back", callback_data=CS.BACK),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)
    return CS.SELECT_ITEM_ACTION


async def crew_change_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Switch crew instance status and make notification."""
    query = update.callback_query
    await query.answer()

    crew = context.user_data['crew']
    user = await get_user(update, context)

    try:
        match crew.status:
            case crew.StatusVerbose.AVAILABLE:
                crew.status = Crew.StatusVerbose.ON_MISSION
                crew.departure_datetime = dt.datetime.now(tz=user.tz)
                msg = f"Crew {crew.title}-{crew.pk} departured."

            case crew.StatusVerbose.ON_MISSION:
                crew.status = Crew.StatusVerbose.RETURNING
                msg = f"Crew {crew.title}-{crew.pk} returning."

            case crew.StatusVerbose.RETURNING:
                crew.status = Crew.StatusVerbose.COMPLETED
                crew.return_datetime = dt.datetime.now(tz=user.tz)
                msg = f"Crew {crew.title}-{crew.pk} completed.\n"\
                    "Please add your tracks to the crew History."

                passengers = await sync_to_async(list)(
                    crew.passengers.values_list('telegram_id', flat=True)
                )

                logger.info(f"Broacast crew status completed to: {passengers}")
                await make_broadcast(context, msg, passengers)

        await crew.asave()
        # TODO: log event

    except Exception as e:
        logger.warning("Can't change crew status."
                       f'TG: {user.telegram_id}, Crew: {crew.pk}, {e=}')
        # raise e
    buttons = [[InlineKeyboardButton("🔙 Back", callback_data=CS.BACK)]]
    keyboard = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(msg, reply_markup=keyboard)
    return CS.SELECT_ITEM_ACTION


# Passengers managemnt
async def list_passengers(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Display a list of passager requests as buttons."""
    query = update.callback_query
    await query.answer()

    user = await get_user(update, context)
    crew = context.user_data['crew']

    joinrequests = crew.join_requests.prefetch_related('passenger')
    context.user_data['joinrequests'] = joinrequests

    msg = await get_crew_info(crew, user.tz) + '\nPlease select the action:'

    buttons = [
        [
            InlineKeyboardButton(f"{jreq.passenger.full_name} {jreq.emoji}",
                                 callback_data=f'{jreq.pk}'),
        ]
        async for jreq in joinrequests.all()
    ]

    buttons.append(
        [
            InlineKeyboardButton("🔙 Back", callback_data=CS.BACK),
            InlineKeyboardButton("❌ Cancel", callback_data=CS.END),
        ]
    )

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)

    return CS.CREW_MANAGE_PASSENGERS


async def display_passenger(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Display passenger instance with buttons."""
    query = update.callback_query
    await query.answer()
    pk = int(query.data)

    joinrequests = context.user_data['joinrequests']
    jreq = await joinrequests.aget(pk=pk)
    context.user_data['joinrequest'] = jreq

    p = jreq.passenger

    msg = f"""{jreq.emoji} ({jreq.get_status_display()})
Full name: {p.full_name}
Nickname: {p.nickname}
DOB: {p.dateofbirth}
Address: {p.address}
Phone: {p.phone_number}
Telegram: # TODO: @Username
    """

    btn_accept = InlineKeyboardButton("🟢 Accept", callback_data=CS.ACCEPT)
    btn_reject = InlineKeyboardButton("🔴 Reject", callback_data=CS.REJECT)

    match jreq.status:
        case JoinRequest.StatusVerbose.PENDING:
            btn_row = [btn_accept, btn_reject]
        case JoinRequest.StatusVerbose.ACCEPTED:
            btn_row = [btn_reject]
        case JoinRequest.StatusVerbose.REJECTED:
            btn_row = [btn_accept]

    buttons = [
        btn_row,
        [
            InlineKeyboardButton("🔙 Back",
                                 callback_data=CS.CREW_MANAGE_PASSENGERS),
            InlineKeyboardButton("❌ Cancel", callback_data=CS.END),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)

    return CS.CREW_MANAGE_PASSENGERS


async def accept_join_request(update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> int:
    """Accept passenger join request to the crew."""
    query = update.callback_query
    await query.answer()

    crew = context.user_data['crew']
    jreq = context.user_data['joinrequest']
    title = f'{crew.title}-{crew.pk}'

    try:
        msg = f"Passenger '{jreq.passenger.full_name}' joined crew: {title}"
        await crew.aaccept_join_request(jreq)

        broadcast_msg = f"You are accepted to crew '{title}'"
        await make_broadcast(context,
                             broadcast_msg,
                             jreq.passenger.telegram_id)

    except Exception as e:
        logger.warning('Passenger joining error\n TG: {query.from_user.id},'
                       f'Crew: {title}, JoinRequest: {jreq} \n{e=}')
        msg = f'Error. Passenger is not added to the crew.\n{e}'
        raise e
    buttons = [
        [
            InlineKeyboardButton("🔙 Back",
                                 callback_data=CS.CREW_MANAGE_PASSENGERS),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)
    return CS.CREW_MANAGE_PASSENGERS


async def reject_join_request(update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> int:
    """Accept passenger join request to the crew."""
    query = update.callback_query
    await query.answer()

    crew = context.user_data['crew']
    jreq = context.user_data['joinrequest']
    title = f'{crew.title}-{crew.pk}'

    try:
        msg = f"Passenger {jreq.passenger.full_name} rejected from crew: {title}"  # noqa: E501
        await crew.areject_join_request(jreq)

        broadcast_msg = f"You are rejected to crew '{title}'"
        await make_broadcast(context,
                             broadcast_msg,
                             jreq.passenger.telegram_id)

    except Exception as e:
        logger.warning('Passenger rejection error\n TG: {query.from_user.id},'
                       f'Crew: {title}, JoinRequest: {jreq} \n{e=}')
        msg = f'Error. Passenger rejection is unsuccessfull.\n{e}'

    buttons = [
        [
            InlineKeyboardButton("🔙 Back",
                                 callback_data=CS.CREW_MANAGE_PASSENGERS),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)
    return CS.CREW_MANAGE_PASSENGERS


# User settings
async def change_tz(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Change user timezone."""
    query = update.callback_query
    await query.answer()
    await query.delete_message()
    # await query.delete_message()

    user = context.user_data['user']

    msg = 'Go /back to settings\n\nYou current TZ: '\
        f'{TZOffsetHandler.represent_tz_offset(user.timezone)}\n'\
        "Please enter your current Time Zone realtive to UTC\n"\
        "Format: ±HH:MM"

    buttons = [
        ['/cancel']
    ]
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
        msg = f"Timezone is updated: {tz}"
    except Exception as e:
        logger.warning(f'TG: {user.telegram_id}, {e}')
        msg = f'Please type correct Time Zone format.\nError: {e}'

    buttons = [
        [
            InlineKeyboardButton("🔙 Back", callback_data=CS.SETTINGS),
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
            InlineKeyboardButton("🔙 Back", callback_data=CS.SETTINGS),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)
    return CS.SELECT_ACTION


# Crew Joining
async def request_passenger_psn(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Request passenger postition."""
    query = update.callback_query
    await query.answer()
    await query.delete_message()

    msg = '/back\n\nPlease send your current coordinates: X, Y'
    keyboard = await get_keyboard_cancel()

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=msg,
                                   reply_markup=keyboard)
    return CS.CREW_MANAGE_PASSENGERS


async def confirm_passenger_psn(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Request passenger postition."""
    psn = update.message.text
    try:
        psn = get_coordinates(psn)
        context.user_data['passenger_psn'] = psn

    except Exception as e:
        error_msg = f"Unexpected error: {e}\n"\
            "Please send your current coordinates: X, Y"

        logger.warning(
            "Passanger psn validation error."
            f"TG: '{update.effective_user.id}'. Error: {e}"
        )

        keyboard = await get_keyboard_cancel()
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=error_msg,
                                       reply_markup=keyboard)

        return CS.CREW_MANAGE_PASSENGERS

    msg = f'Your position is: {psn}\n\nPlease confirm.'
    buttons = [
        [
            InlineKeyboardButton('Confirm',
                                 callback_data=CS.CREW_JOINING)
        ],
        [
            InlineKeyboardButton("🔙 Back",
                                 callback_data=CS.CREW_MANAGE_PASSENGERS),
            InlineKeyboardButton("❌ Cancel", callback_data=CS.SHOWING),
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.effective_chat.send_message(msg, reply_markup=keyboard)
    return CS.SELECT_ACTION


async def list_public_crews(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Display a list of all available crews or a passeger specific crews."""
    query = update.callback_query
    await query.answer()

    user = await get_user(update, context)

    status = context.user_data.get('status')
    if status is None:
        status = query.data
        context.user_data['status'] = status

    match status:
        case CS.CREW_JOINING:
            # TODO: enter filter validation
            lat, long = context.user_data['passenger_psn']
            passenger_location = Point(lat, long, srid=4326)

            crews = Crew.objects.filter(
                status=Crew.StatusVerbose.AVAILABLE
            ).annotate(
                distance=Distance('pickup_location', passenger_location)
            ).order_by('distance')

            error_msg = "There are no available Crews to join."
            msg = "The total number of existing crews: "\
                f"{await crews.acount()}\n\nPlease choose a Crew to join:"

        case CS.CREW_MANAGE_JOINED:
            crews = Crew.objects.filter(join_requests__passenger=user)
            error_msg = "There are no Crews you took part in."
            msg = "The total number of Crews you took part in: "\
                f"{await crews.acount()}\n\nPlease choose a Crew to edit:"

    if not await crews.aexists():
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=error_msg
        )
        return CS.END

    keyboard = await get_keyboard_crew_list(crews, distance=True)

    await update.effective_chat.send_message(msg, reply_markup=keyboard)
    return CS.DISPLAY_ITEM


async def display_crew_for_passenger(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Display detailed crew information for passenger."""
    query = update.callback_query
    await query.answer()

    pk = int(query.data)
    crew = await context.user_data['user_crews']\
        .select_related('departure', 'departure__search_request')\
        .annotate(driver_tg_id=F('driver__telegram_id'))\
        .prefetch_related('driver', 'passengers')\
        .aget(pk=pk)

    context.user_data['crew'] = crew

    user = await get_user(update, context)
    msg = await get_crew_detailed_info(crew, user.tz)

    is_passenger = await JoinRequest.objects.filter(crew=crew, passenger=user)\
        .aexists()

    if is_passenger:
        button = [InlineKeyboardButton(
           "❗ Cancel joining request (& leave crew)", callback_data=CS.DELETE
        )]

    else:
        button = [InlineKeyboardButton(
           "☑️ Send joining request", callback_data=CS.SELECT
        )]

    buttons = [
        button,
        [
            # InlineKeyboardButton("🔧 Edit", callback_data=CS.SELECT),
            InlineKeyboardButton("🔙 Back", callback_data=CS.BACK),
            InlineKeyboardButton("❌ Cancel", callback_data=CS.END),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)

    return CS.SELECT_ITEM_ACTION


async def apply_to_crew(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Create a JoinRequest for the crew and inform driver about it."""
    query = update.callback_query
    await query.answer()

    user = await get_user(update, context)
    crew = context.user_data['crew']

    try:
        await JoinRequest.objects.acreate(
            status=JoinRequest.StatusVerbose.PENDING,
            crew=crew,
            passenger=user,
            request_time=dt.datetime.now(tz=user.tz)
        )

        num_joinrequests = await JoinRequest.objects.filter(crew=crew)\
            .exclude(status=JoinRequest.StatusVerbose.REJECTED).acount()

        broadcast_msg = f"🟢 Crew '{crew}': +1 join request! "\
            f"({num_joinrequests}/{crew.passengers_max})"

        await make_broadcast(context, broadcast_msg, crew.driver_tg_id)
        msg = "Join request is sent"

    except Exception as e:
        msg = 'Join request is failed. '\
            f'TG: {user.telegram_id} Unexpected error: {e}'
        logger.warning(msg)

    buttons = [[InlineKeyboardButton("🔙 Back", callback_data=CS.BACK)]]
    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)
    del context.user_data['status']

    return CS.STOPPING


async def exempt_from_crew(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Delete the JoinRequest instance and exclude the passenger from the crew.
    """
    query = update.callback_query
    await query.answer()

    user = await get_user(update, context)
    crew = context.user_data['crew']

    try:
        joinrequest = await JoinRequest.objects.aget(
            crew=crew,
            passenger=user,
        )

        await joinrequest.adelete()

        num_joinrequests = await JoinRequest.objects.filter(crew=crew)\
            .exclude(status=JoinRequest.StatusVerbose.REJECTED).acount()

        broadcast_msg = f"🔴 Crew '{crew}': –1 join request! "\
            f"({num_joinrequests}/{crew.passengers_max})"

        msg = "Join request is canceled"

        if await crew.passengers.filter(pk=user.pk).aexists():
            await crew.passengers.aremove(user)
            broadcast_msg += f'\n⚠ {user.full_name} left the crew.'
            msg = f'You left crew {crew}'
            logger.info(
                    f"User '{user.pk}: {user.full_name}' left crew '{crew}'"
            )

        await make_broadcast(context, broadcast_msg, crew.driver_tg_id)

    except Exception as e:
        msg = 'Join request is failed. '\
            f'TG: {user.telegram_id} Unexpected error: {e}'
        logger.warning(msg)

    buttons = [[InlineKeyboardButton("🔙 Back", callback_data=CS.BACK)]]
    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)
    del context.user_data['status']

    return CS.STOPPING


# Crew Archive
async def list_user_archived_crews(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Display a list of all available crews or a passeger specific crews."""
    query = update.callback_query
    await query.answer()

    user = await get_user(update, context)
    crews = Crew.objects.filter(status=Crew.StatusVerbose.COMPLETED).filter(
        Q(driver=user) | Q(join_requests__passenger=user)
    )
    context.user_data['user_archived_crews'] = crews
    msg = "The total number of Crews (Completed) you took part in: "\
        f"{await crews.acount()}\n\nPlease choose a Crew to upload track:"

    error_msg = "There are no Crews (Completed) you took part in."

    if not await crews.aexists():
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=error_msg
        )
        return CS.END

    keyboard = await get_keyboard_crew_list(crews)

    await query.edit_message_text(msg, reply_markup=keyboard)
    return CS.DISPLAY_ITEM


async def display_user_archived_crew(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Display detailed archived crew information."""
    query = update.callback_query
    await query.answer()

    pk = int(query.data)
    crew = await context.user_data['user_archived_crews']\
        .select_related('departure', 'departure__search_request')\
        .annotate(driver_tg_id=F('driver__telegram_id'))\
        .prefetch_related('driver', 'passengers')\
        .aget(pk=pk)

    context.user_data['crew'] = crew

    user = await get_user(update, context)
    msg = await get_crew_detailed_info(crew, user.tz)

    buttons = [
        [
            InlineKeyboardButton("☑️ Send track", callback_data=CS.SELECT)
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data=CS.BACK),
            InlineKeyboardButton("❌ Cancel", callback_data=CS.STOPPING),
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(msg, reply_markup=keyboard)

    return CS.SELECT_ITEM_ACTION


async def request_track(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Request user to send track."""
    query = update.callback_query
    await query.answer()
    await query.delete_message()

    crew = context.user_data['crew']

    msg = "Please share the track file (.gpx) related to the crew"\
        f"'{crew.title}-{crew.id}' departure:"

    keyboard = await get_keyboard_cancel()
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=msg,
                                   reply_markup=keyboard)
    return CS.RECEIVE_FILE


async def receive_track(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Recieve track."""
    user = await get_user(update, context)
    crew = context.user_data['crew']

    upload_dir = f"share/dep_{crew.departure.id}/{crew.title}_{crew.id}/"
    os.makedirs(upload_dir, exist_ok=True)

    new_file = await update.effective_message.effective_attachment.get_file()

    title = (
        user.nickname if user.nickname else user.full_name.replace(' ', '_')
    ) + dt.datetime.now(dt.UTC).strftime('%Y.%m.%d_%H%m')\
        + '.' + new_file.file_path.split('.')[-1]

    await new_file.download_to_drive(
        f'{upload_dir}/{title}'
    )

    buttons = [[
        InlineKeyboardButton("🔙 Back", callback_data=CS.BACK),
    ]]

    msg = f'Received track file: {new_file.file_size / 1024: .1f} Kb'
    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(msg, reply_markup=keyboard)

    return CS.SHOWING


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
            CS.STOPPING: CS.END,
            CS.SHOWING: CS.SHOWING
        },
    )

    crew_archive_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            list_user_archived_crews,
            pattern=f"^{CS.CREW_ARCHIVE}$"
        )],

        states={
            CS.DISPLAY_ITEM: [
                CallbackQueryHandler(display_user_archived_crew)
            ],
            CS.SELECT_ITEM_ACTION: [
                CallbackQueryHandler(request_track, pattern=f"^{CS.SELECT}$"),
                CallbackQueryHandler(list_user_archived_crews,
                                     pattern=f'^{CS.BACK}$'),
                CallbackQueryHandler(stop_nested, pattern=f"^{CS.STOPPING}$")
            ],
            CS.RECEIVE_FILE: [
                MessageHandler(
                    filters.Document.FileExtension('gpx') & ~filters.COMMAND,
                    receive_track
                )
            ],

        },
        fallbacks=[CommandHandler("cancel", stop_nested)],
        map_to_parent={
            CS.STOPPING: CS.STOPPING,
            CS.SHOWING: CS.SHOWING,
            CS.END: CS.END,
        },
    )

    crew_joining_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            list_public_crews,
            pattern=f"^({CS.CREW_JOINING}|{CS.CREW_MANAGE_JOINED})$"
        )],

        states={
            CS.DISPLAY_ITEM: [
                CallbackQueryHandler(display_crew_for_passenger)
            ],
            CS.SELECT_ITEM_ACTION: [
                CallbackQueryHandler(apply_to_crew, pattern=f"^{CS.SELECT}$"),
                CallbackQueryHandler(exempt_from_crew,
                                     pattern=f"^{CS.DELETE}$"),
                CallbackQueryHandler(list_public_crews,
                                     pattern=f'^{CS.BACK}$'),
                CallbackQueryHandler(stop_nested, pattern=f"^{CS.END}$")
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
            CS.DISPLAY_ITEM: [
                # CallbackQueryHandler(start_conversation,
                #                      pattern=f"^{CS.BACK}$"),
                # CallbackQueryHandler(stop_nested, pattern=f"^{CS.END}$"),
                CallbackQueryHandler(display_crew),
            ],
            CS.SELECT_ITEM_ACTION: [
                crew_action_handler,
                CallbackQueryHandler(crew_delete_confirmation,
                                     pattern=f"^{CS.DELETE}$"),
                CallbackQueryHandler(crew_change_status,
                                     pattern=f"^{CS.STATUS}$"),
                CallbackQueryHandler(list_passengers,
                                     pattern=f"^{CS.CREW_MANAGE_PASSENGERS}$"),
                CallbackQueryHandler(list_crews, pattern=f"^{CS.BACK}$"),
                CallbackQueryHandler(stop_nested, pattern=f"^{CS.END}$")
            ],
            CS.CREW_MANAGE_PASSENGERS: [
                CallbackQueryHandler(list_passengers,
                                     pattern=f"^{CS.CREW_MANAGE_PASSENGERS}$"),
                CallbackQueryHandler(accept_join_request,
                                     pattern=f"^{CS.ACCEPT}$"),
                CallbackQueryHandler(reject_join_request,
                                     pattern=f"^{CS.REJECT}$"),
                CallbackQueryHandler(display_crew, pattern=f"^{CS.BACK}$"),
                CallbackQueryHandler(stop_nested, pattern=f"^{CS.END}$"),
                CallbackQueryHandler(display_passenger),
            ],

            CS.DELETE: [
                CallbackQueryHandler(crew_delete, pattern=f"^{CS.DELETE}$"),
                CallbackQueryHandler(display_crew, pattern=f"^{CS.BACK}$"),
            ],
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
                CallbackQueryHandler(start_conversation)
            ],
            CS.SELECT_ACTION: [
                CommandHandler("back", start_conversation),
                crew_create_handler,
                crew_update_handler,
                crew_joining_handler,
                crew_archive_handler,
                CallbackQueryHandler(info, pattern=f"^{CS.INFO}$"),
                CallbackQueryHandler(help_command, pattern=f"^{CS.HELP}$"),
                CallbackQueryHandler(start_conversation,
                                     pattern=f"^{CS.SHOWING}$"),
                CallbackQueryHandler(
                    settings_command,
                    pattern=f"^{CS.SETTINGS}$"
                ),
                CallbackQueryHandler(request_passenger_psn,
                                     pattern=f"^{CS.CREW_MANAGE_PASSENGERS}$"),
            ],
            CS.CREW_MANAGE_PASSENGERS: [
                CommandHandler("back", start_conversation),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    confirm_passenger_psn
                )
            ],
            CS.SETTINGS: [
                CallbackQueryHandler(
                    change_car_status, pattern=f"^{CS.CHANGE_CAR_STATUS}$"
                ),
                CallbackQueryHandler(
                    change_tz, pattern=f"^{CS.CHANGE_TZ}$"
                ),
                CallbackQueryHandler(
                    change_language, pattern=f"^{CS.CHANGE_LANGUAGE}$"
                ),
                CallbackQueryHandler(
                    start_conversation, pattern=f"^{CS.SHOWING}$"
                ),
            ],
            CS.CHANGE_TZ: [
                CommandHandler("back", settings_command),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_user_tz
                ),
            ],
            CS.STOPPING: [CallbackQueryHandler(start_conversation)],
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
