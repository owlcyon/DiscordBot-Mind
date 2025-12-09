import os
import sys
from dotenv import load_dotenv

# --- 1. Load Environment Variables (MANDATORY) ---
load_dotenv()

# --- 2. Core Dependencies ---
import discord
from discord.ext import commands
from sqlalchemy import text # Required for status command

# Import your database connection logic
try:
    from app.core.database import get_db_session
except ImportError:
    print("CRITICAL: Cannot import database module. Check file structure.")
    sys.exit(1)

# Import the service functions
try:
    from app.services.embedding_service import process_and_store_message
    from app.services.retrieval_service import retrieve_and_answer # <-- NEW RAG IMPORT
except ImportError:
    print("CRITICAL: Cannot import necessary service. Check app/services/ directory.")
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
    print(f'✅ Bot Logged In: {bot.user} (ID: {bot.user.id})')
    print(f'Connected to {len(bot.guilds)} guild(s)')
    
@bot.event
async def on_message(message):
    # Skip bot's own messages
    if message.author == bot.user:
        return
    
    # --- 1. Handle Commands ---
    await bot.process_commands(message)

    # --- 2. Ingestion Logic (Embedding and Storage) ---
    # Skip DMs, empty messages, or messages that are commands
    if message.guild is None or not message.content or not message.content.strip() or message.content.startswith(bot.command_prefix):
        return

    # Use context manager properly for database session
    try:
        # Note: Using get_db_session() as a context manager is cleaner but requires adaptation.
        # Sticking to next(get_db_session()) for consistency with your existing code structure.
        db = next(get_db_session())
        try:
            await process_and_store_message(
                db=db,
                discord_message_id=str(message.id),
                author_id=str(message.author.id),
                channel_id=str(message.channel.id),
                content=message.content
            )
            print(f"✅ Ingested: {message.author.name} | Ch: {message.channel.name} | Len: {len(message.content)}")
        except Exception as e:
            print(f"❌ Ingestion failed for message {message.id}: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Database session error: {e}")


# --- 5. Basic Commands & RAG ---

@bot.command(name='ping')
async def ping(ctx):
    """Test if bot is responsive"""
    await ctx.send(f'🏓 Pong! Latency: {round(bot.latency * 1000)}ms')

@bot.command(name='status')
async def status(ctx):
    """Check bot status and message count"""
    # Using the database session as a context manager for safety and cleanliness
    try:
        with get_db_session() as db:
            result = db.execute(text("SELECT COUNT(*) FROM discord_messages")).scalar()
            await ctx.send(f'✅ Bot Online | Messages stored: {result}')
    except Exception as e:
        await ctx.send(f'❌ Database error: {str(e)}')

@bot.command(name='ask') # <-- NEW RAG COMMAND
async def ask_command(ctx, *, question):
    """
    Searches the knowledge base and generates an answer using RAG.
    Usage: !ask What was the decision on deployment?
    """
    await ctx.send(f"🔍 Searching knowledge base for: `{question}`...")
    
    try:
        # Use the database session as a context manager
        with get_db_session() as session:
            # Call the new RAG service
            answer = retrieve_and_answer(question, session)
            
            # Send the final response
            await ctx.send(f"🧠 **Answer:**\n{answer}")
            
    except Exception as e:
        print(f"Bot Command Error: {e}")
        await ctx.send("Sorry, I ran into an error while trying to answer that question.")


# --- 6. Execution ---

if __name__ == '__main__':
    try:
        # Check if the database connection can be established before running the bot
        db = next(get_db_session())
        print("✅ Database session successfully initiated.")
        db.close()
        
        print("🚀 Starting bot...")
        bot.run(DISCORD_TOKEN)
        
    except Exception as e:
        print(f"❌ Critical Error: Bot failed to run: {e}")
        sys.exit(1)