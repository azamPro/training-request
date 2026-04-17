import logging
import warnings

from telegram.warnings import PTBUserWarning

warnings.filterwarnings("ignore", category=PTBUserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pypdf")
warnings.filterwarnings("ignore", message=".*ARC4.*")

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from bot.config import TELEGRAM_BOT_TOKEN
from bot.database.db import init_db
from bot.handlers.start import (
    start_handler,
    main_menu_callback,
    profile_callback,
    profile_command,
    history_callback,
    history_command,
    unknown_handler,
)
from bot.handlers.register import register_conv_handler
from bot.handlers.request import request_conv_handler
from bot.handlers.help import help_handler, help_callback, handle_dotslash

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception:", exc_info=context.error)
    if isinstance(update, Update):
        if update.callback_query:
            try:
                await update.callback_query.answer("⚠️ حدث خطأ. حاول مرة أخرى.")
            except Exception:
                pass
        elif update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⚠️ حدث خطأ غير متوقع. حاول مرة أخرى أو تواصل مع المسؤول."
                )
            except Exception:
                pass


async def _answer_unknown_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch any callback query not handled by any other handler."""
    await update.callback_query.answer()


def main() -> None:
    init_db()
    logger.info("Database initialised")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # ── Error handler (catches all unhandled exceptions) ────────────────────
    app.add_error_handler(_error_handler)

    # ── Conversation handlers (must be checked before generic handlers) ─────
    app.add_handler(register_conv_handler)
    app.add_handler(request_conv_handler)

    # ── Commands ─────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",   start_handler))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("help",    help_handler))

    # ── Inline button callbacks ───────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^cb_main$"))
    app.add_handler(CallbackQueryHandler(profile_callback,   pattern="^cb_profile$"))
    app.add_handler(CallbackQueryHandler(history_callback,   pattern="^cb_history$"))
    app.add_handler(CallbackQueryHandler(help_callback,      pattern="^cb_help$"))

    # ── ./ shortcut ──────────────────────────────────────────────────────────
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r"^\.\/"), handle_dotslash)
    )

    # ── Unknown text messages → show main menu ────────────────────────────────
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_handler)
    )

    # ── Catch-all for any unhandled callback query (prevents hanging buttons) ─
    app.add_handler(CallbackQueryHandler(_answer_unknown_cb))

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
