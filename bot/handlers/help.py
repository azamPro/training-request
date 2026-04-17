from telegram import Update
from telegram.ext import ContextTypes

from bot.config import ADMIN_TELEGRAM_USERNAME
from bot.utils import COMMANDS_LIST, main_menu_keyboard
from bot.handlers.start import profile_command, history_command

_HELP_FULL = (
    "ℹ️ *بوت طلب التدريب الصيفي*\n\n"
    "يقوم البوت بتعبئة نموذج طلب التدريب الصيفي تلقائياً بناءً على بياناتك المحفوظة.\n\n"
    "*طريقة الاستخدام:*\n"
    "1️⃣ سجّل بياناتك مرة واحدة عبر /register\n"
    "2️⃣ عند الحاجة لطلب، اضغط *📄 طلب جديد* وأدخل اسم الشركة فقط\n"
    "3️⃣ يصلك الـ PDF جاهزاً فوراً\n\n"
    "{commands}\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "للتواصل مع المسؤول: @{admin}"
)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        COMMANDS_LIST + f"\n\n━━━━━━━━━━━━━━━━\nللتواصل: @{ADMIN_TELEGRAM_USERNAME}",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        _HELP_FULL.format(commands=COMMANDS_LIST, admin=ADMIN_TELEGRAM_USERNAME),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def handle_dotslash(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip().lower()
    sub = text[2:].strip()

    if sub in ("help", "h"):
        await update.message.reply_text(
            _HELP_FULL.format(commands=COMMANDS_LIST, admin=ADMIN_TELEGRAM_USERNAME),
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
    elif sub in ("profile", "p"):
        await profile_command(update, context)
    elif sub in ("history", "hist"):
        await history_command(update, context)
    else:
        # ./ alone or unrecognised sub-command → show commands list
        await update.message.reply_text(
            COMMANDS_LIST,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
