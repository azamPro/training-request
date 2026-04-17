"""
User-initiated error reporting — lets users send a note to the admin after an error.

Entry point: callback_data="report_start"  (sent by _error_handler in main.py)
"""

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.config import ADMIN_TELEGRAM_ID
from bot.utils import main_menu_keyboard

REPORT_TEXT = 0


async def report_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "📝 اكتب ملاحظتك وسنوصلها للمطور مباشرة:\n"
        "(أو أرسل /cancel للإلغاء)"
    )
    return REPORT_TEXT


async def report_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    note = update.message.text.strip()
    user = update.effective_user

    if ADMIN_TELEGRAM_ID:
        msg = (
            f"🚨 *تقرير مشكلة من مستخدم*\n\n"
            f"المستخدم: @{user.username or 'بدون اسم'} (ID: `{user.id}`)\n"
            f"الاسم: {user.full_name or 'غير معروف'}\n\n"
            f"الملاحظة:\n{note}"
        )
        try:
            await context.bot.send_message(ADMIN_TELEGRAM_ID, msg, parse_mode="Markdown")
        except Exception:
            pass

    await update.message.reply_text(
        "✅ شكراً! وصل تقريرك للمطور.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def report_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("تم الإلغاء.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


async def skip_error_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer("تم التخطي")


error_report_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(report_start_cb, pattern="^report_start$")],
    states={
        REPORT_TEXT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, report_text_received),
        ]
    },
    fallbacks=[CommandHandler("cancel", report_cancel)],
    allow_reentry=True,
    per_message=False,
)
