import logging
import warnings

from telegram.warnings import PTBUserWarning

# suppress harmless warnings
warnings.filterwarnings("ignore", category=PTBUserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pypdf")
warnings.filterwarnings("ignore", message=".*ARC4.*")

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from bot.config import TELEGRAM_BOT_TOKEN
from bot.database.db import init_db
from bot.handlers.start import start_handler, profile_handler
from bot.handlers.register import register_conv_handler
from bot.handlers.request import (
    request_conv_handler,
    history_handler,
    handle_inline_request,
)
from bot.handlers.help import help_handler, handle_dotslash

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    init_db()
    logger.info("Database initialised")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Conversation handlers (must come before generic handlers)
    app.add_handler(register_conv_handler)
    app.add_handler(request_conv_handler)

    # Simple command handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("profile", profile_handler))
    app.add_handler(CommandHandler("history", history_handler))
    app.add_handler(CommandHandler("help", help_handler))

    # Inline keyboard callbacks
    app.add_handler(CallbackQueryHandler(handle_inline_request, pattern="^new_request$"))
    app.add_handler(
        CallbackQueryHandler(
            lambda u, c: profile_handler(u, c),
            pattern="^view_profile$",
        )
    )

    # ./ shortcut trigger
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^\./"),
            handle_dotslash,
        )
    )

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
