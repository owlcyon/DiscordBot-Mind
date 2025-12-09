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

# NEW: Import the service function for ingestion
try:
    from app.services.embedding_service import process_and_store_message
except ImportError:
    print("CRITICAL: Cannot import embedding service. Check app/services/embedding_service.py.")
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


# --- 4. Bot Event Handlers ---

@bot.event
async def on_ready():
    # MANDATE 2.3: Observability - Structured Logging
    print(f'✅ Bot Logged In: {bot.user} (ID: {bot.user.id})')
    # Optional: Test database connection here if needed
    
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # --- 1. Handle Commands ---
    # Process commands first (e.g., !ask, !remember)
    await bot.process_commands(message)

    # --- 2. Ingestion Logic (Embedding and Storage) ---
    # We skip DMs and ensure the message has content before processing
    if message.guild is None or not message.content:
        return

    # Use the database session manager to ensure the session is opened and closed correctly
    # The 'for' loop is necessary because get_db_session is a generator/context manager
    for db in get_db_session():
        # This calls the service which contacts OpenAI and saves to PostgreSQL
        await process_and_store_message(
            db, 
            message.content, 
            message.author.id, 
            message.guild.id
        )
        print(f"-> Ingested message from {message.author.name} (Length: {len(message.content)})")
        # We don't send a public confirmation to avoid spam

    
    


# --- 5. Execution ---

if __name__ == '__main__':
    try:
        # Check if the database connection can be established before running the bot
        with next(get_db_session()):
            print("✅ Database session successfully initiated.")
        
        bot.run(DISCORD_TOKEN)
        
    except Exception as e:
        print(f"❌ Critical Error: Bot failed to run: {e}")
 

