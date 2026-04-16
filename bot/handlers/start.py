from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.database.db import get_db
from bot.database.models import User


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()

    if user:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 New Request", callback_data="new_request")],
            [InlineKeyboardButton("👤 My Profile", callback_data="view_profile")],
        ])
        await update.message.reply_text(
            f"Welcome back, *{user.full_name}*! 👋\n\n"
            "What would you like to do?",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Register Now", callback_data="start_register")],
        ])
        await update.message.reply_text(
            "👋 Welcome to the *Summer Training Request Bot*!\n\n"
            "This bot fills your university training request form automatically.\n\n"
            "You only need to register *once*, then every request just needs the company name.\n\n"
            "Use /register to get started, or tap below.",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )


async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()

    if not user:
        await update.message.reply_text(
            "You don't have a profile yet. Use /register to create one."
        )
        return

    sig = "✅ Saved" if user.signature_path else "❌ Not set"
    await update.message.reply_text(
        f"👤 *Your Profile*\n\n"
        f"Name: {user.full_name}\n"
        f"University ID: {user.university_id}\n"
        f"Department: {user.department}\n"
        f"Remaining Hours: {user.remaining_hours}\n"
        f"Signature: {sig}\n\n"
        "Use /register to update your profile.",
        parse_mode="Markdown",
    )
