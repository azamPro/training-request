"""
Registration conversation handler.

Flow:
  /register
    → ask full name
    → ask university ID
    → ask department
    → ask remaining credit hours
    → ask for signature image (skippable)
    → confirm & save
"""

import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from bot.database.db import get_db
from bot.database.models import User
from bot.config import GENERATED_PDF_DIR

# Conversation states
REG_NAME, REG_UNI_ID, REG_DEPT, REG_HOURS, REG_SIG = range(5)

_CANCEL_TEXT = "❌ Registration cancelled. Use /register to start again."
_SKIP_KB = InlineKeyboardMarkup([[InlineKeyboardButton("⏭ Skip", callback_data="skip_sig")]])


async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "📝 *Registration*\n\n"
        "Step 1/5 — Enter your *full name* as it appears on university records:",
        parse_mode="Markdown",
    )
    return REG_NAME


async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["full_name"] = update.message.text.strip()
    await update.message.reply_text(
        "Step 2/5 — Enter your *university ID number*:",
        parse_mode="Markdown",
    )
    return REG_UNI_ID


async def reg_uni_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["university_id"] = update.message.text.strip()
    await update.message.reply_text(
        "Step 3/5 — Enter your *department name*:\n"
        "_e.g. Computer Science, Information Technology_",
        parse_mode="Markdown",
    )
    return REG_DEPT


async def reg_dept(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["department"] = update.message.text.strip()
    await update.message.reply_text(
        "Step 4/5 — How many *credit hours* remain until graduation (assuming you pass all current courses)?",
        parse_mode="Markdown",
    )
    return REG_HOURS


async def reg_hours(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    hours = update.message.text.strip()
    if not hours.isdigit():
        await update.message.reply_text("Please enter a *number* only (e.g. 45):", parse_mode="Markdown")
        return REG_HOURS

    context.user_data["remaining_hours"] = hours
    await update.message.reply_text(
        "Step 5/5 — *Optional:* Send a photo of your signature to embed in the form.\n\n"
        "Or tap *Skip* to use your name as signature text.",
        parse_mode="Markdown",
        reply_markup=_SKIP_KB,
    )
    return REG_SIG


async def reg_sig_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo = update.message.photo[-1]  # highest resolution
    sig_dir = os.path.join(GENERATED_PDF_DIR, "signatures")
    os.makedirs(sig_dir, exist_ok=True)

    tg_id = update.effective_user.id
    sig_path = os.path.join(sig_dir, f"{tg_id}_sig.jpg")
    file = await context.bot.get_file(photo.file_id)
    await file.download_to_drive(sig_path)

    context.user_data["signature_path"] = sig_path
    return await _save_user(update, context)


async def reg_sig_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["signature_path"] = None
    await update.callback_query.answer()
    return await _save_user(update, context, via_callback=True)


async def _save_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    via_callback: bool = False,
) -> int:
    tg_id = update.effective_user.id
    tg_username = update.effective_user.username
    d = context.user_data

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()
        if user:
            user.telegram_username = tg_username
            user.full_name = d["full_name"]
            user.university_id = d["university_id"]
            user.department = d["department"]
            user.remaining_hours = d["remaining_hours"]
            user.signature_path = d.get("signature_path")
            action = "updated"
        else:
            user = User(
                telegram_id=tg_id,
                telegram_username=tg_username,
                full_name=d["full_name"],
                university_id=d["university_id"],
                department=d["department"],
                remaining_hours=d["remaining_hours"],
                signature_path=d.get("signature_path"),
            )
            db.add(user)
            action = "saved"

    msg = (
        f"✅ *Profile {action} successfully!*\n\n"
        f"Name: {d['full_name']}\n"
        f"University ID: {d['university_id']}\n"
        f"Department: {d['department']}\n"
        f"Remaining Hours: {d['remaining_hours']}\n\n"
        "Use /request whenever you need a training letter."
    )

    if via_callback:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, parse_mode="Markdown")

    context.user_data.clear()
    return ConversationHandler.END


async def reg_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(_CANCEL_TEXT)
    return ConversationHandler.END


register_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("register", register_start),
        CallbackQueryHandler(register_start, pattern="^start_register$"),
    ],
    states={
        REG_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
        REG_UNI_ID:[MessageHandler(filters.TEXT & ~filters.COMMAND, reg_uni_id)],
        REG_DEPT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_dept)],
        REG_HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_hours)],
        REG_SIG: [
            MessageHandler(filters.PHOTO, reg_sig_photo),
            CallbackQueryHandler(reg_sig_skip, pattern="^skip_sig$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", reg_cancel)],
    allow_reentry=True,
    per_message=False,
)
