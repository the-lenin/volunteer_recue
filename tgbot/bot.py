import os
import logging
import django
import asyncio

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from telegram.ext import (
    filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes,
    ConversationHandler,  # RegexHandler,
)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_dashboard.settings')
django.setup()

from django.conf import settings  # noqa: E402
from django.core.paginator import Paginator  # noqa: E402
from web_dashboard.logistics.models import Departure  # noqa: E402
from web_dashboard.logistics.serializers import DepartureSerializer  # noqa: E402 
from web_dashboard.search_requests.models import SearchRequest   # noqa: E402
from asgiref.sync import sync_to_async

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# reply_keyboard = [
#     ['Info', 'Help'],
#     ['Create crew'],
#     ['Update crew'],
# ]
# markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

# Basic features:
# start, info, unknown


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcoming a user at the joining."""
    welcome_msg = "I'm a Volunteer Rescue Bot, please talk to me!"
    # await update.message.reply_text(welcome_msg, reply_markup=markup)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=welcome_msg)


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display present number of the open SearchRequest and Departures."""
    search_requests = await SearchRequest.objects.filter(
        status=SearchRequest.StatusVerbose.OPEN
    ).acount()

    departures = await Departure.objects.filter(
            status=Departure.StatusVerbose.OPEN
    ).acount()

    information = (
        f'{SearchRequest._meta.verbose_name_plural}: {search_requests}\n'
        f'{Departure._meta.verbose_name_plural}: {departures}'
    )

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=information)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return unknown command message if a command is not found."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I didn't understand that command."
    )

# CREW CREATION
(
    LIST_DEPARTURES,
    DISPLAY_DEPARTURE,
    HANDLE_DEPARTURE_ACTION,
    CREW_NAME,
    CREW_LOCATION,
    CREW_CAPACITY,
    CHOOSE_ACTION
) = range(6)


async def start_crew_creation(update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start crew creation conversation."""
    return LIST_DEPARTURES


async def list_departures(update: Update,
                          context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display a list of all departures with open status."""
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
             f"{ind}. {dep.search_request.full_name} - "
             f"{dep.search_request.city} (Crews: {await dep.crews.acount()})"
        ])

    context.user_data['departures'] = list(zip(departures, keyboard))

    await update.message.reply_text(
        f"Total number of departures: {len(departures)}\n"
        "Let's create a crew! Please choose Departure.",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
    )

    return DISPLAY_DEPARTURE


async def display_departure(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display detailed information of the chosen departure with buttons."""
    index = int(update.message.text.split('.')[0])
    departure = context.user_data['departures'][index]

    # Display detailed information about the selected departure with buttons
    dep = departure[0]
    tasks = '\n'.join([
        f'* {task.title} - {task.coordinates.coords}:\n{task.description}'
        async for task in dep.tasks.all()
    ])

    detailed_info_message = (
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

    keyboard = [
        ["Select", "Back", "Cancel"]
    ]

    await update.message.reply_text(
        detailed_info_message,
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
    )

    # Store the selected departure information in the context
    context.user_data['selected_departure'] = departure

    return HANDLE_DEPARTURE_ACTION


async def handle_departure_action(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE) -> int:
    action = update.message.text

    match action:
        case "Select":
            await update.message.reply_text(
                "Selecting Departure",
                reply_markup=ReplyKeyboardRemove()
            )
            # context.user_data['selected_departure'] =
            context.user_data['departures'].clear()
            return CREW_NAME

        case "Back":
            return CREW_NAME

        case "Cancel":
            return await cancel_crew_creation(update, context)

        case _:
            await update.message.reply_text(
                "Invalid action. Please choose from the options."
            )
            return CHOOSE_ACTION

async def receive_departure(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["departure"] = update.message.text
    await update.message.reply_text(
        "Please send the name of the crew."
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
    departure = context.user_data["departure"]
    crew_name = context.user_data["crew_name"]
    crew_location = context.user_data["crew_location"]
    crew_capacity = update.message.text

    # Perform crew creation logic here, e.g., save to database
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
    application = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()

    start_handler = CommandHandler('start', start)
    # test_handler = CommandHandler('test', test)
    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    info_handler = CommandHandler('info', info)

    crew_creation_handler = ConversationHandler(
        entry_points=[CommandHandler("createcrew", start_crew_creation)],
        states={
            CHOOSE_DEPARTURE: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, choose_departure
            )],
            DEPARTURE_ACTION: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, receive_departure
            )],
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
    # application.add_handler(test_handler)
    application.add_handler(crew_creation_handler)
    application.add_handler(unknown_handler)  # last one

    application.run_polling()


if __name__ == '__main__':
    main()
