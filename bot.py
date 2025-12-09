import os
import sys
from dotenv import load_dotenv

# --- 1. Load Environment Variables (MANDATORY) ---
load_dotenv()

# --- 2. Core Dependencies ---
import discord
from discord.ext import commands
# Import your database connection logic
try:
    from app.core.database import get_db_session
except ImportError:
    print("CRITICAL: Cannot import database module. Check file structure.")
    sys.exit(1)


# --- 3. Configuration ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    print("CRITICAL: DISCORD_TOKEN not found in .env. Cannot proceed.")
    sys.exit(1)

# Initialize Discord Client (using intents required for message content and guilds)
intents = discord.Intents.default()
intents.message_content = True # MANDATORY for accessing message content
bot = commands.Bot(command_prefix='!', intents=intents)


# --- 4. Bot Event Handlers (Your Logic) ---

@bot.event
async def on_ready():
    # MANDATE 2.3: Observability - Structured Logging
    print(f'✅ Bot Logged In: {bot.user} (ID: {bot.user.id})')
    # Optional: Test database connection here if needed
    
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # This is where your Stage 2 (Embedding & Persistence) logic will go.
    if "hello bot" in message.content.lower():
        await message.channel.send(f"Hello, {message.author.display_name}! I am ready to ingest your consciousness data.")
    
    # Process other commands/events
    await bot.process_commands(message)


# --- 5. Execution ---

if __name__ == '__main__':
    try:
        # Check if the database connection can be established before running the bot
        # This is a good sanity check
        with next(get_db_session()):
            print("✅ Database session successfully initiated.")
        
        bot.run(DISCORD_TOKEN)
        
    except Exception as e:
        print(f"❌ Critical Error: Bot failed to run: {e}")
