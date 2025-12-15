
import os
import sys
import asyncio
import discord
from discord.ext import commands
from sqlalchemy import text
from dotenv import load_dotenv

# --- 1. Load Config (Must be before app imports) ---
load_dotenv()

# --- Production Imports ---
from app.core.logger import logger
from app.core.database import get_db_session
from app.services.embedding_service import process_and_store_message
from app.services.retrieval_service import retrieve_and_answer
from app.services.clustering_service import get_clustering_service

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    # Logger might not be initialized if we needed env for it, but here it's fine
    print("CRITICAL: DISCORD_TOKEN not found in .env. Exiting.")
    sys.exit(1)

# --- 2. Bot Class definition (MANDATE 4.2) ---
class DiscordMindBot(commands.Bot):
    def __init__(self):
        # Intents
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=commands.DefaultHelpCommand()
        )
    
    async def setup_hook(self):
        """
        Perform async initialization tasks here.
        """
        logger.info("🚀 Performing setup hooks...")
        # Verify DB connection on startup
        try:
            db = next(get_db_session())
            db.execute(text("SELECT 1"))
            db.close()
            logger.info("✅ Database connection healthy.")
        except Exception as e:
            logger.critical(f"❌ Database connection failed: {e}")
            await self.close()
            sys.exit(1)

    async def on_ready(self):
        logger.info(f'✅ Logged in as: {self.user} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guild(s)')
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.listening, 
            name="the substrate"
        ))

    async def on_message(self, message: discord.Message):
        # 1. Self-protection
        if message.author.bot:
            return

        # 2. Command Handling
        # If it's a command, process it and STOP (don't ingest commands)
        if message.content.startswith(self.command_prefix):
            await self.process_commands(message)
            return

        # 3. Direct Conversation (Mentions)
        # If the bot is mentioned, we treat it as a conversation turn
        if self.user in message.mentions:
            # Strip the mention to get the clean query
            clean_content = message.content.replace(f'<@{self.user.id}>', '').replace(f'<@!{self.user.id}>', '').strip()
            
            if clean_content:
                async with message.channel.typing():
                    db = None
                    try:
                        db = next(get_db_session())
                        # Re-use retrieve_and_answer to leverage RAG + Persona prompt
                        answer = retrieve_and_answer(clean_content, db)
                        await message.reply(answer)
                    except Exception as e:
                        logger.error(f"Reply error: {e}")
                        await message.reply("The gravitational field is failing. (Error occurred)")
                    finally:
                        if db: db.close()

            # We DO continue to ingest this message so the conversation is remembered!
            
        # 4. Ingestion Logic
        if message.guild and message.content.strip():
            await self._ingest_message(message)

    async def _ingest_message(self, message: discord.Message):
        """Private helper to handle ingestion safely."""
        db = None
        try:
            db = next(get_db_session())
            await process_and_store_message(
                db=db,
                discord_message_id=str(message.id),
                author_id=str(message.author.id),
                channel_id=str(message.channel.id),
                content=message.content
            )
            # logger.info(f"Ingested: {message.author.name} ({len(message.content)} chars)")
        except Exception as e:
            logger.error(f"Ingestion failed for msg {message.id}: {e}")
        finally:
            if db:
                db.close()


# --- 3. Instantiation ---
bot = DiscordMindBot()

# --- 4. Command Registrations ---
# We register commands here to keep the class clean, or simpler: use decorators.

@bot.command(name='ping')
async def ping(ctx):
    """Latency check."""
    await ctx.send(f'🏓 Pong! Latency: {round(bot.latency * 1000)}ms')

@bot.command(name='status')
async def status(ctx):
    """Health check."""
    db = None
    try:
        db = next(get_db_session())
        result = db.execute(text("SELECT COUNT(*) FROM discord_messages")).scalar()
        await ctx.send(f'✅ **Substrate Status**\nMessages Observed: `{result}`')
    except Exception as e:
        logger.error(f"Status command error: {e}")
        await ctx.send(f'❌ Database error.')
    finally:
        if db: db.close()

@bot.command(name='ask')
async def ask(ctx, *, question):
    """RAG Retrieval."""
    async with ctx.typing(): # Show typing indicator while thinking
        db = None
        try:
            db = next(get_db_session())
            answer = retrieve_and_answer(question, db)
            await ctx.send(f"🧠 **Substrate Oracle:**\n{answer}")
        except Exception as e:
            logger.error(f"Ask command error: {e}")
            await ctx.send("The substrate is silent. (Error occurred)")
        finally:
            if db: db.close()

# --- Clustering Commands ---
@bot.command(name='topics')
async def topics(ctx, num: int = 5):
    """Semantic clustering."""
    async with ctx.typing():
        db = None
        try:
            db = next(get_db_session())
            clustering = get_clustering_service(db)
            
            summary = clustering.get_cluster_summary()
            if summary["total_messages"] < 5:
                # Lowered threshold for testing easier
                await ctx.send("⚠️ Not enough mass for clustering yet.")
                return

            clusters = clustering.discover_topics(n_clusters=min(num, summary["total_messages"] // 2))
            
            if not clusters:
                await ctx.send("No patterns found.")
                return

            response = f"**🌌 Topic Clusters ({len(clusters)})**\n\n"
            for i, c in enumerate(clusters, 1):
                try:
                    top_author_id = c.top_authors[0][0]
                    # Try fetch user
                    user = ctx.guild.get_member(int(top_author_id))
                    name = user.display_name if user else f"User {top_author_id[:4]}"
                except:
                    name = "Unknown"
                    
                response += f"**{i}.** ({c.message_count} msgs) Voice: {name}\n"
                response += f"   *\"{c.representative_messages[0][:80]}...\"*\n"
            
            await ctx.send(response)
        except Exception as e:
            logger.error(f"Topics error: {e}")
            await ctx.send("Error analyzing patterns.")
        finally:
            if db: db.close()

@bot.command(name='mindmap')
async def mindmap(ctx, member: discord.Member = None):
    member = member or ctx.author
    db = None
    try:
        db = next(get_db_session())
        clustering = get_clustering_service(db)
        profile = clustering.get_author_profile(str(member.id))
        
        if not profile:
            await ctx.send(f"No data for {member.display_name}.")
            return
            
        await ctx.send(f"**🌀 Mindmap: {member.display_name}**\nMass: {profile.message_count} messages")
    except Exception as e:
        logger.error(f"Mindmap error: {e}")
    finally:
        if db: db.close()

@bot.command(name='whosaid')
async def whosaid(ctx, *, idea: str):
    db = None
    try:
        db = next(get_db_session())
        clustering = get_clustering_service(db)
        attributions = clustering.attribute_idea(idea)
        
        if not attributions:
            await ctx.send("Trace failed.")
            return
            
        resp = f"**🎯 Origin Trace:** *\"{idea}\"*\n"
        for i, (uid, score, _) in enumerate(attributions, 1):
            user = ctx.guild.get_member(int(uid))
            name = user.display_name if user else uid
            resp += f"{i}. **{name}** ({score*100:.1f}%)\n"
            
        await ctx.send(resp)
    except Exception as e:
        logger.error(f"Whosaid error: {e}")
    finally:
        if db: db.close()

# --- 5. Main Execution ---
if __name__ == '__main__':
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.critical(f"Bot execution failed: {e}")
        sys.exit(1)
