import os
import sys
from dotenv import load_dotenv

# --- 1. Load Environment Variables (MANDATORY) ---
load_dotenv()

# --- 2. Core Dependencies ---
import discord
from discord.ext import commands
from sqlalchemy import text, create_engine # <-- ADDED FOR INIT
from app.models.message import Base # <-- ADDED FOR INIT

# Import your database connection logic (Needed for Base and other imports)
try:
    from app.core.database import get_db_session
except ImportError:
    print("CRITICAL: Cannot import database module. Check file structure.")
    sys.exit(1)

# Import the service function for ingestion (Needed for other imports)
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
# (These handlers are ignored in the temporary init mode, but kept for future use)

@bot.event
async def on_ready():
    print(f'✅ Bot Logged In: {bot.user} (ID: {bot.user.id})')
    # ... rest of on_ready logic


@bot.event
async def on_message(message):
    # This ingestion logic is also ignored in the temporary init mode
    await bot.process_commands(message)
    # ... rest of on_message logic


# --- 5. Basic Commands ---
@bot.command(name='ping')
async def ping(ctx):
    await ctx.send(f'🏓 Pong! Latency: {round(bot.latency * 1000)}ms')

@bot.command(name='status')
async def status(ctx):
    db = next(get_db_session())
    try:
        from sqlalchemy import text
        result = db.execute(text("SELECT COUNT(*) FROM discord_messages")).scalar()
        await ctx.send(f'✅ Bot Online | Messages stored: {result}')
    except Exception as e:
        await ctx.send(f'❌ Database error: {str(e)}')
    finally:
        db.close()


# --- 6. Execution (TEMPORARY DB INIT MODE) ---

if __name__ == '__main__':
    # This block is TEMPORARY to fix the database schema on Railway.
    # It MUST be reverted after a successful deployment!
    try:
        from sqlalchemy import create_engine, text
        
        DATABASE_URL = os.getenv("DATABASE_URL")
        engine = create_engine(DATABASE_URL)

        print("--- Attempting to fix pgvector extension and create tables ---")
        
        # 1. Create the extension (This MUST be done first)
        with engine.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;")) 
            connection.commit()
            print("✅ pgvector extension enabled.")

        # 2. Create the tables (DiscordMessage table with vector(1536))
        Base.metadata.create_all(engine)
        print("✅ Database schema (discord_messages) initialized successfully.")
        
        # CRITICAL: Exit the script after initialization.
        print("✅ Initialization complete. Exiting script. PLEASE REVERT bot.py CODE.")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Critical Error: Initialization failed: {e}")
        print(f"DEBUG URL used: {os.getenv('DATABASE_URL')}")
        sys.exit(1)