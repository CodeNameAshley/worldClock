import discord
from discord.ext import commands, tasks
from datetime import datetime
import pytz
import aiosqlite
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE = 'timezones.db'

# Bot setup
intents = discord.Intents.default()
intents.message_content = True  # Make sure this is enabled for message content access
bot = commands.Bot(command_prefix="!", intents=intents)

# Store the message ID and channel ID for the display message
display_message_info = {}
rsgame_message_info = {}

async def create_db():
    """Creates the database and the table if it doesn't exist."""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS timezones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                timezone TEXT NOT NULL
            )
        ''')
        await db.commit()

@bot.event
async def on_ready():
    """Event that runs when the bot is ready."""
    print(f'Logged in as {bot.user.name}')
    await create_db()  # Ensure the database and table are created
    display_timezones.start()
    rsgametime_loop.start()

@bot.command()
async def addtimezone(ctx, label: str):
    """Adds a new timezone to the list of tracked timezones."""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("INSERT INTO timezones (label, timezone) VALUES (?, ?)", (label, label))
        await db.commit()
    await ctx.send(f"Timezone {label} added.")

@bot.command()
async def listtimezones(ctx):
    """Lists all currently tracked timezones."""
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT label FROM timezones")
        timezones = await cursor.fetchall()

    if timezones:
        message = "```"
        for tz in timezones:
            message += f"{tz[0]}\n"
        message += "```"
        await ctx.send(message)
    else:
        await ctx.send("No timezones are currently tracked.")

@bot.command()
async def removetimezone(ctx, label: str):
    """Removes a timezone from the list of tracked timezones."""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("DELETE FROM timezones WHERE label = ?", (label,))
        await db.commit()
    await ctx.send(f"Timezone {label} removed.")

# Function to get the UTC offset for a timezone
def get_utc_offset(timezone_name):
    tz_info = pytz.timezone(timezone_name)
    utc_time = datetime.now(pytz.utc)
    local_time = utc_time.astimezone(tz_info)
    offset = local_time.utcoffset().total_seconds() / 3600  # Convert to hours
    return offset

@bot.command()
async def displaytimezones(ctx):
    """Displays the current timezones in the channel and stores the message ID for future updates."""
    global display_message_info
    channel = ctx.channel

    # Create the message content
    message = "```"
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT label, timezone FROM timezones")
        timezones = await cursor.fetchall()

    if timezones:
        # Sort timezones based on UTC offset
        timezones.sort(key=lambda x: get_utc_offset(x[1]))

        # Add sorted timezones to the message
        for label, tz in timezones:
            tz_info = pytz.timezone(tz)
            utc_time = datetime.now(pytz.utc)
            local_time = utc_time.astimezone(tz_info)

            region = label
            date = local_time.strftime('%m/%d')
            time = local_time.strftime('%I:%M %p')

            message += f"{region:<20} | {date:<7} | {time}\n"
        message += "```"

    # Send the message and store the message_id and channel_id for future updates
    sent_message = await channel.send(message)
    display_message_info = {'message_id': sent_message.id, 'channel_id': channel.id}

@tasks.loop(seconds=45)
async def display_timezones():
    """Updates the timezones message every 45 seconds"""
    global display_message_info

    # If the message ID is stored, try to update the message
    if display_message_info.get('message_id') and display_message_info.get('channel_id'):
        channel = bot.get_channel(display_message_info['channel_id'])
        if channel:
            try:
                message_to_edit = await channel.fetch_message(display_message_info['message_id'])
                message = "```"
                async with aiosqlite.connect(DATABASE) as db:
                    cursor = await db.execute("SELECT label, timezone FROM timezones")
                    timezones = await cursor.fetchall()

                if timezones:
                    # Sort timezones based on UTC offset
                    timezones.sort(key=lambda x: get_utc_offset(x[1]))

                    # Add sorted timezones to the message
                    for label, tz in timezones:
                        tz_info = pytz.timezone(tz)
                        utc_time = datetime.now(pytz.utc)
                        local_time = utc_time.astimezone(tz_info)

                        region = label
                        date = local_time.strftime('%m/%d')
                        time = local_time.strftime('%I:%M %p')

                        message += f"{region:<20} | {date:<7} | {time}\n"
                    message += "```"

                # Update the message with the new timezone data
                await message_to_edit.edit(content=message)

            except discord.NotFound:
                print("Message not found, skipping update.")
            except discord.Forbidden:
                print("Bot does not have permission to edit the message.")

@bot.command()
async def currenttime(ctx):
    """Displays the current timezones in a static message."""
    message = "```"
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT label, timezone FROM timezones")
        timezones = await cursor.fetchall()

    if timezones:
        # Sort timezones based on UTC offset
        timezones.sort(key=lambda x: get_utc_offset(x[1]))

        # Add sorted timezones to the message
        for label, tz in timezones:
            tz_info = pytz.timezone(tz)
            utc_time = datetime.now(pytz.utc)
            local_time = utc_time.astimezone(tz_info)

            region = label
            date = local_time.strftime('%m/%d')
            time = local_time.strftime('%I:%M %p')

            message += f"{region:<20} | {date:<7} | {time}\n"
        message += "```"
        await ctx.send(message)

@bot.command()
async def rsgametime(ctx):
    """Displays the current Runescape Game Time (RST)."""
    global rsgame_message_info
    channel = ctx.channel

    # Create the message content
    message = "```"
    tz_info = pytz.timezone('Europe/London')
    utc_time = datetime.now(pytz.utc)
    local_time = utc_time.astimezone(tz_info)

    # Runescape Game Time is based on London time
    game_time = local_time.strftime('%H:%M')

    message += f"Runescape Game Time is {game_time}\n"
    message += "```"

    # Send the message and store the message_id and channel_id for future updates
    sent_message = await channel.send(message)
    rsgame_message_info = {'message_id': sent_message.id, 'channel_id': channel.id}

@tasks.loop(seconds=15)
async def rsgametime_loop():
    """Updates the Runescape Game Time message every 15 seconds."""
    global rsgame_message_info

    # If the message ID is stored, try to update the message
    if rsgame_message_info.get('message_id') and rsgame_message_info.get('channel_id'):
        channel = bot.get_channel(rsgame_message_info['channel_id'])
        if channel:
            try:
                message_to_edit = await channel.fetch_message(rsgame_message_info['message_id'])
                message = "```"
                tz_info = pytz.timezone('Europe/London')
                utc_time = datetime.now(pytz.utc)
                local_time = utc_time.astimezone(tz_info)

                # Runescape Game Time is based on London time
                game_time = local_time.strftime('%H:%M')

                message += f"Runescape Game Time is {game_time}\n"
                message += "```"

                # Update the message with the new game time
                await message_to_edit.edit(content=message)

            except discord.NotFound:
                print("Message not found, skipping update.")
            except discord.Forbidden:
                print("Bot does not have permission to edit the message.")

@bot.command()
async def worldclockhelp(ctx):
    """Displays the help message with a list of available commands."""
    help_message = """
    **WorldClock Bot Commands:**

    `!addtimezone [label]` - Adds a new timezone to the list of tracked timezones.
    `!listtimezones` - Lists all currently tracked timezones.
    `!removetimezone [label]` - Removes a timezone from the list of tracked timezones.
    `!displaytimezones` - Displays the current times of all tracked timezones and updates every 15 seconds.
    `!currenttime` - Displays the current times of all tracked timezones in a static message.
    `!rsgametime` - Displays the current Runescape Game Time (RST) and updates every 15 seconds.
    """
    await ctx.send(help_message)

# Run the bot
bot.run(TOKEN)
