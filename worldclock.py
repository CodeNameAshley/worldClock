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

# Channel ID for #world-clock
WORLD_CLOCK_CHANNEL_ID = 1323546512512520295  # Replace with your channel ID

# Message IDs for updates
RST_MESSAGE_ID = 1324168260412772453  # RuneScape Game Time
TIMEZONES_MESSAGE_ID = 1324168267434299464  # Timezones Display

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

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
    """Event triggered when the bot is ready."""
    print(f'Logged in as {bot.user.name}')
    await create_db()
    display_timezones.start()
    rsgametime_loop.start()

@bot.command()
async def addtimezone(ctx, label: str, timezone: str):
    """Adds a new timezone to the list of tracked timezones."""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("INSERT INTO timezones (label, timezone) VALUES (?, ?)", (label, timezone))
        await db.commit()
    await ctx.send(f"Timezone '{label}' ({timezone}) added.")

@bot.command()
async def listtimezones(ctx):
    """Lists all currently tracked timezones."""
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT label, timezone FROM timezones")
        timezones = await cursor.fetchall()

    if timezones:
        message = "```"
        for label, tz in timezones:
            message += f"{label} ({tz})\n"
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
    await ctx.send(f"Timezone '{label}' removed.")

def get_utc_offset(timezone_name):
    """Gets the UTC offset for a timezone."""
    tz_info = pytz.timezone(timezone_name)
    utc_time = datetime.now(pytz.utc)
    local_time = utc_time.astimezone(tz_info)
    offset = local_time.utcoffset().total_seconds() / 3600  # Convert to hours
    return offset

@tasks.loop(seconds=45)
async def display_timezones():
    """Periodically updates the Timezones Display message every 45 seconds."""
    channel = bot.get_channel(WORLD_CLOCK_CHANNEL_ID)
    if not channel:
        print("World Clock channel not found.")
        return

    try:
        message_to_edit = await channel.fetch_message(TIMEZONES_MESSAGE_ID)

        # Create the updated timezones message
        message = "```"
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT label, timezone FROM timezones")
            timezones = await cursor.fetchall()

        if timezones:
            timezones.sort(key=lambda x: get_utc_offset(x[1]))
            for label, tz in timezones:
                tz_info = pytz.timezone(tz)
                utc_time = datetime.now(pytz.utc)
                local_time = utc_time.astimezone(tz_info)
                region = label
                date = local_time.strftime('%m/%d')
                time = local_time.strftime('%I:%M %p')
                message += f"{region:<20} | {date:<7} | {time}\n"
            message += "```"

        # Edit the message with the new content
        await message_to_edit.edit(content=message)

    except discord.NotFound:
        print("Timezones Display message not found.")
    except discord.Forbidden:
        print("Bot lacks permission to edit the Timezones Display message.")
    except Exception as e:
        print(f"Error updating Timezones Display: {e}")

@tasks.loop(seconds=45)
async def rsgametime_loop():
    """Updates the RuneScape Game Time message every 45 seconds."""
    channel = bot.get_channel(WORLD_CLOCK_CHANNEL_ID)
    if not channel:
        print("World Clock channel not found.")
        return

    try:
        message_to_edit = await channel.fetch_message(RST_MESSAGE_ID)

        # Generate the updated RuneScape Game Time message
        tz_info = pytz.timezone('Europe/London')
        utc_time = datetime.now(pytz.utc)
        local_time = utc_time.astimezone(tz_info)
        game_time = local_time.strftime('%H:%M')
        message = f"```Runescape Game Time: {game_time}```"

        # Edit the message with the new content
        await message_to_edit.edit(content=message)

    except discord.NotFound:
        print("RuneScape Game Time message not found.")
    except discord.Forbidden:
        print("Bot lacks permission to edit the RuneScape Game Time message.")
    except Exception as e:
        print(f"Error updating RuneScape Game Time: {e}")

@bot.command()
async def currenttime(ctx):
    """Responds with the current times for all tracked timezones."""
    message = "```"
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT label, timezone FROM timezones")
        timezones = await cursor.fetchall()

    if timezones:
        timezones.sort(key=lambda x: get_utc_offset(x[1]))
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
    else:
        await ctx.send("No timezones are currently tracked.")

@bot.command()
async def worldclockhelp(ctx):
    """Displays a help message with available commands."""
    help_message = """
    **WorldClock Bot Commands:**

    `!addtimezone [label] [timezone]` - Adds a new timezone.
    `!listtimezones` - Lists all tracked timezones.
    `!removetimezone [label]` - Removes a timezone.
    `!displaytimezones` - Displays the current timezones and updates the #world-clock channel periodically.
    `!currenttime` - Responds with the current times of all tracked timezones.
    """
    await ctx.send(help_message)

# Run the bot
bot.run(TOKEN)
