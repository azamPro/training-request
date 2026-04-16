from telegram import Update
from telegram.ext import ContextTypes

from bot.config import ADMIN_TELEGRAM_USERNAME

COMMANDS_TEXT = """
📋 *Available Commands*

*Registration & Profile*
/start — Welcome message
/register — Register your profile (first time) or update it
/profile — View your saved profile

*Requests*
/request — Generate a new training letter for a company
/history — View your last 5 requests

*Help*
/help — Show this help message
./  — Show all commands (shortcut)
./help — Show detailed help

━━━━━━━━━━━━━━━━━━━━
For support, contact: @{admin}
""".strip()

HELP_DETAIL_TEXT = """
ℹ️ *Summer Training Request Bot*

This bot auto-fills the university summer training request form (PDF) with your saved profile.

*How it works:*
1. Register once with `/register` — enter your name, university ID, department, and remaining credit hours.
2. Every time you want a letter, use `/request` — just type the company name.
3. The bot sends you a filled PDF in seconds.

*Your data is stored securely* in a private database and never shared.

*Commands:*
{commands}

━━━━━━━━━━━━━━━━━━━━
Contact admin: @{admin}
""".strip()


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        COMMANDS_TEXT.format(admin=ADMIN_TELEGRAM_USERNAME),
        parse_mode="Markdown",
    )


async def handle_dotslash(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ./  and ./help shortcut commands."""
    text = (update.message.text or "").strip().lower()
    sub = text[2:].strip()  # everything after ./

    if sub in ("", "help"):
        if sub == "help":
            await update.message.reply_text(
                HELP_DETAIL_TEXT.format(
                    commands=COMMANDS_TEXT.format(admin=ADMIN_TELEGRAM_USERNAME),
                    admin=ADMIN_TELEGRAM_USERNAME,
                ),
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                COMMANDS_TEXT.format(admin=ADMIN_TELEGRAM_USERNAME),
                parse_mode="Markdown",
            )
    else:
        await update.message.reply_text(
            f"Unknown shortcut: `{text}`\nType `./` to see all commands.",
            parse_mode="Markdown",
        )
