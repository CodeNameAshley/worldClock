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

# Prevent multiple instances
if os.path.exists("bot.lock"):
    print("Bot is already running!")
    exit()
open("bot.lock", "w").close()

# Clean up lock file on exit
import atexit
atexit.register(lambda: os.remove("bot.lock") if os.path.exists("bot.lock") else None)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True  # Ensure message content access
bot = commands.Bot(command_prefix="!", intents=intents)

# Store the message IDs and channel IDs for persistent updates
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
    """Event triggered when the bot is ready."""
    print(f'Logged in as {bot.user.name}')
    await create_db()  # Ensure the database and table are created
    display_timezones.start()
    rsgametime_loop.start()

@bot.event
async def on_disconnect():
    """Event triggered when the bot disconnects."""
    print("Bot disconnected.")

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

@tasks.loop(seconds=15)
async def display_timezones():
    """Updates the timezones message every 15 seconds."""
    global display_message_info

    if display_message_info.get('message_id') and display_message_info.get('channel_id'):
        try:
            channel = bot.get_channel(display_message_info['channel_id'])
            if not channel:
                return

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
                    date = local_time.strftime('%m/%d')
                    time = local_time.strftime('%I:%M %p')
                    message += f"{label:<20} | {date:<7} | {time}\n"
                message += "```"
                await message_to_edit.edit(content=message)

        except Exception as e:
            print(f"Error in display_timezones loop: {e}")

@tasks.loop(seconds=60)
async def rsgametime_loop():
    """Updates the Runescape Game Time message every 15 seconds."""
    global rsgame_message_info

    # If the message ID is stored, try to update the message
    if rsgame_message_info.get('message_id') and rsgame_message_info.get('channel_id'):
        try:
            channel = bot.get_channel(rsgame_message_info['channel_id'])
            if not channel:
                return

            message_to_edit = await channel.fetch_message(rsgame_message_info['message_id'])
            tz_info = pytz.timezone('Europe/London')
            utc_time = datetime.now(pytz.utc)
            local_time = utc_time.astimezone(tz_info)
            game_time = local_time.strftime('%H:%M')

            message = f"```Runescape Game Time: {game_time}```"
            await message_to_edit.edit(content=message)

        except Exception as e:
            print(f"Error in rsgametime_loop: {e}")

@bot.command()
async def worldclockhelp(ctx):
    """Displays a help message with a list of commands."""
    help_message = """
    **WorldClock Bot Commands:**

    `!addtimezone [label] [timezone]` - Adds a new timezone.
    `!listtimezones` - Lists all currently tracked timezones.
    `!removetimezone [label]` - Removes a tracked timezone.
    `!displaytimezones` - Displays and updates the current times of all timezones.
    """
    await ctx.send(help_message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found. Use `!worldclockhelp` to see the list of available commands.")

# Run the bot
try:
    bot.run(TOKEN)
except Exception as e:
    print(f"Failed to start bot: {e}")