
import logging
import sys
import os

def setup_logging():
    """
    Configures the application's logging with structured output.
    MANDATE 2.3: Observability
    """
    # Create logger
    logger = logging.getLogger("discord_mind")
    logger.setLevel(logging.INFO)

    # Formatters
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler (Optional, good for production persistence)
    try:
        os.makedirs("logs", exist_ok=True)
        file_handler = logging.FileHandler("logs/bot.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not set up file logging: {e}")

    # Silence noisy libraries
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return logger

logger = setup_logging()
