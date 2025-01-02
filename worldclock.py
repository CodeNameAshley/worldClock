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

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Store the message ID for the display message
display_message_id = None

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
    """Periodically updates the #world-clock channel every 45 seconds."""
    global display_message_id

    channel = bot.get_channel(WORLD_CLOCK_CHANNEL_ID)
    if not channel:
        print("World Clock channel not found.")
        return

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

    if display_message_id:
        try:
            msg = await channel.fetch_message(display_message_id)
            await msg.edit(content=message)
        except discord.NotFound:
            display_message_id = None
    else:
        sent_message = await channel.send(message)
        display_message_id = sent_message.id

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

@tasks.loop(seconds=45)
async def rsgametime_loop():
    """Updates the Runescape Game Time message every 45 seconds."""
    tz_info = pytz.timezone('Europe/London')
    utc_time = datetime.now(pytz.utc)
    local_time = utc_time.astimezone(tz_info)
    game_time = local_time.strftime('%H:%M')

    message = f"```Runescape Game Time: {game_time}```"
    print(message)  # Debugging purposes, replace this with sending a message if needed

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
