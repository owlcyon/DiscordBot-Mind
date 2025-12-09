import os
import sys
from dotenv import load_dotenv

# --- 1. Load Environment Variables (MANDATORY) ---
load_dotenv()

# --- 2. Core Dependencies ---
import discord
from discord.ext import commands
from sqlalchemy import text 

# Import database and service functions
try:
    from app.core.database import get_db_session
    from app.services.embedding_service import process_and_store_message
    from app.services.retrieval_service import retrieve_and_answer 
except ImportError:
    print("CRITICAL: Cannot import necessary module. Check file structure and __init__.py files.")
    sys.exit(1)


# --- 3. Configuration ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    print("CRITICAL: DISCORD_TOKEN not found in .env. Cannot proceed.")
    sys.exit(1)

# Initialize Discord Client with required intents
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
    # 1. Skip bot's own messages
    if message.author == bot.user:
        return
    
    # 2. Check if the message is a command. 
    # This prevents ingestion for commands, but allows commands to run later.
    is_command = message.content and message.content.startswith(bot.command_prefix)

    # --- 3. INGESTION LOGIC (Runs ONLY if it's NOT a command) ---
    if not is_command and message.guild is not None and message.content and message.content.strip():
        try:
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

    # --- 4. Handle Commands (This should always be the last step) ---
    await bot.process_commands(message)


# --- 5. Basic Commands & RAG ---

@bot.command(name='ping')
async def ping(ctx):
    """Test if bot is responsive"""
    await ctx.send(f'🏓 Pong! Latency: {round(bot.latency * 1000)}ms')

@bot.command(name='status')
async def status(ctx):
    """Check bot status and message count"""
    db = None
    try:
        # ✅ FIX: Get the session from the generator
        db = next(get_db_session()) 
        result = db.execute(text("SELECT COUNT(*) FROM discord_messages")).scalar()
        await ctx.send(f'✅ Bot Online | Messages stored: {result}')
    except Exception as e:
        await ctx.send(f'❌ Database error: {str(e)}')
    finally:
        # ✅ CRITICAL: Ensure the session is closed
        if db:
            db.close() 


@bot.command(name='ask')
async def ask_command(ctx, *, question):
    """Searches the knowledge base and generates an answer using RAG."""
    await ctx.send(f"🔍 Searching knowledge base for: `{question}`...")
    
    db = None
    try:
        # ✅ FIX: Get the session from the generator
        db = next(get_db_session())
        answer = retrieve_and_answer(question, db)
        await ctx.send(f"🧠 **Answer:**\n{answer}")
            
    except Exception as e:
        print(f"Bot Command Error: {e}")
        await ctx.send("Sorry, I ran into an error while trying to answer that question.")
    finally:
        # ✅ CRITICAL: Ensure the session is closed
        if db:
            db.close()

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