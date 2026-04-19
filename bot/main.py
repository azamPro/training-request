import logging
import os
import warnings
from logging.handlers import RotatingFileHandler

from telegram.warnings import PTBUserWarning

warnings.filterwarnings("ignore", category=PTBUserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pypdf")
warnings.filterwarnings("ignore", message=".*ARC4.*")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from bot.config import TELEGRAM_BOT_TOKEN, ADMIN_TELEGRAM_ID
from bot.database.db import init_db, log_event
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
from bot.handlers.edit import edit_conv_handler
from bot.handlers.request import request_conv_handler
from bot.handlers.help import help_handler, help_callback, handle_dotslash
from bot.handlers.error_report import error_report_conv_handler, skip_error_cb
from bot.handlers.admin import admin_handler

_LOG_DIR = os.getenv("LOG_DIR", "/app/logs")
os.makedirs(_LOG_DIR, exist_ok=True)

_fmt = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")
_file_handler = RotatingFileHandler(
    os.path.join(_LOG_DIR, "bot.log"),
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
_file_handler.setFormatter(_fmt)

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(), _file_handler],
)
logger = logging.getLogger(__name__)


_REPORT_KB = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📝 إبلاغ عن المشكلة", callback_data="report_start"),
        InlineKeyboardButton("❌ تخطي",              callback_data="skip_error"),
    ]
])


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception:", exc_info=context.error)

    if isinstance(update, Update) and update.effective_user:
        log_event(update.effective_user.id, "error", str(context.error)[:500])

    if ADMIN_TELEGRAM_ID:
        admin_msg = (
            f"🚨 *خطأ غير متوقع في البوت*\n\n"
            f"`{str(context.error)[:600]}`"
        )
        try:
            await context.bot.send_message(ADMIN_TELEGRAM_ID, admin_msg, parse_mode="Markdown")
        except Exception:
            pass

    if not isinstance(update, Update):
        return

    error_text = "⚠️ حدث خطأ غير متوقع.\nهل تريد إبلاغ المطور عن المشكلة؟"
    if update.callback_query:
        try:
            await update.callback_query.answer("⚠️ حدث خطأ.")
            await update.callback_query.message.reply_text(error_text, reply_markup=_REPORT_KB)
        except Exception:
            pass
    elif update.effective_message:
        try:
            await update.effective_message.reply_text(error_text, reply_markup=_REPORT_KB)
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
    app.add_handler(error_report_conv_handler)
    app.add_handler(register_conv_handler)
    app.add_handler(edit_conv_handler)
    app.add_handler(request_conv_handler)

    # ── Commands ─────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",   start_handler))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("help",    help_handler))
    app.add_handler(CommandHandler("admin",   admin_handler))

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
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE, unknown_handler)
    )

    # ── Error report skip button ─────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(skip_error_cb, pattern="^skip_error$"))

    # ── Catch-all for any unhandled callback query (prevents hanging buttons) ─
    app.add_handler(CallbackQueryHandler(_answer_unknown_cb))

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
