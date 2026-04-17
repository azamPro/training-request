"""
Registration conversation — creates or updates user profile.

Entry points:
  /register, /edit commands
  cb_start_register, cb_edit inline buttons

Steps: الاسم → الرقم الجامعي → القسم → الساعات → التوقيع (اختياري)
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
from bot.utils import arabic_to_western, main_menu_keyboard

REG_NAME, REG_UNI_ID, REG_DEPT, REG_HOURS, REG_SIG = range(5)

_SKIP_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("⏭ تخطي", callback_data="skip_sig")]
])

_BUSY_MSG = "⚠️ أتمم هذه الخطوة أولاً، أو أرسل /cancel للخروج."


def _stay(state: int) -> CallbackQueryHandler:
    """Return a handler that answers any stray button click and stays in current state."""
    async def _h(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.callback_query.answer(_BUSY_MSG)
        return state
    return CallbackQueryHandler(_h)


async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()

    if update.callback_query:
        await update.callback_query.answer()
        send = update.callback_query.message.reply_text
    else:
        send = update.message.reply_text

    await send(
        "📝 *التسجيل — الخطوة 1 من 5*\n\n"
        "أدخل *اسمك الكامل* كما يظهر في السجلات الجامعية:",
        parse_mode="Markdown",
    )
    return REG_NAME


async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["full_name"] = update.message.text.strip()
    await update.message.reply_text(
        "📝 *الخطوة 2 من 5*\n\nأدخل *رقمك الجامعي:*",
        parse_mode="Markdown",
    )
    return REG_UNI_ID


async def reg_uni_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["university_id"] = arabic_to_western(update.message.text.strip())
    await update.message.reply_text(
        "📝 *الخطوة 3 من 5*\n\nأدخل *اسم قسمك:*\n_مثال: علوم الحاسب، تقنية المعلومات_",
        parse_mode="Markdown",
    )
    return REG_DEPT


async def reg_dept(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["department"] = update.message.text.strip()
    await update.message.reply_text(
        "📝 *الخطوة 4 من 5*\n\nكم *ساعة دراسية* متبقية لتخرجك بافتراض النجاح؟",
        parse_mode="Markdown",
    )
    return REG_HOURS


async def reg_hours(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = arabic_to_western(update.message.text.strip())
    if not raw.isdigit():
        await update.message.reply_text(
            "⚠️ الرجاء إدخال *رقم فقط* مثل: 42",
            parse_mode="Markdown",
        )
        return REG_HOURS

    context.user_data["remaining_hours"] = raw
    await update.message.reply_text(
        "📝 *الخطوة 5 من 5 — اختياري*\n\n"
        "أرسل *صورة توقيعك* لإدراجها في النموذج،\n"
        "أو اضغط *تخطي* لترك خانة التوقيع فارغة.",
        parse_mode="Markdown",
        reply_markup=_SKIP_KB,
    )
    return REG_SIG


async def reg_sig_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo = update.message.photo[-1]
    sig_dir = os.path.join(GENERATED_PDF_DIR, "signatures")
    os.makedirs(sig_dir, exist_ok=True)

    tg_id = update.effective_user.id
    sig_path = os.path.join(sig_dir, f"{tg_id}_sig.jpg")
    file = await context.bot.get_file(photo.file_id)
    await file.download_to_drive(sig_path)
    context.user_data["signature_path"] = sig_path

    return await _save_user(update, context)


async def reg_sig_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    context.user_data["signature_path"] = None
    return await _save_user(update, context, via_callback=True)


async def _save_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    via_callback: bool = False,
) -> int:
    tg_id = update.effective_user.id
    d = context.user_data

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()
        if user:
            user.telegram_username = update.effective_user.username
            user.full_name         = d["full_name"]
            user.university_id     = d["university_id"]
            user.department        = d["department"]
            user.remaining_hours   = d["remaining_hours"]
            if d.get("signature_path") is not None:
                user.signature_path = d["signature_path"]
            verb = "تحديث"
        else:
            user = User(
                telegram_id       = tg_id,
                telegram_username = update.effective_user.username,
                full_name         = d["full_name"],
                university_id     = d["university_id"],
                department        = d["department"],
                remaining_hours   = d["remaining_hours"],
                signature_path    = d.get("signature_path"),
            )
            db.add(user)
            verb = "حفظ"

    success_msg = (
        f"✅ *تم {verb} بياناتك بنجاح!*\n\n"
        f"الاسم: {d['full_name']}\n"
        f"الرقم الجامعي: `{d['university_id']}`\n"
        f"القسم: {d['department']}\n"
        f"الساعات المتبقية: {d['remaining_hours']}\n\n"
        "يمكنك الآن إنشاء طلب تدريب من القائمة 👇"
    )

    if via_callback:
        await update.callback_query.edit_message_text(success_msg, parse_mode="Markdown")
        await update.callback_query.message.reply_text(
            "اختر ما تريد:", reply_markup=main_menu_keyboard(),
        )
    else:
        await update.message.reply_text(
            success_msg, parse_mode="Markdown", reply_markup=main_menu_keyboard(),
        )

    context.user_data.clear()
    return ConversationHandler.END


async def reg_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "❌ تم إلغاء التسجيل.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


register_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("register", register_start),
        CommandHandler("edit",     register_start),
        CallbackQueryHandler(register_start, pattern="^(cb_start_register|cb_edit)$"),
    ],
    states={
        REG_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name),
            _stay(REG_NAME),
        ],
        REG_UNI_ID: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, reg_uni_id),
            _stay(REG_UNI_ID),
        ],
        REG_DEPT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, reg_dept),
            _stay(REG_DEPT),
        ],
        REG_HOURS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, reg_hours),
            _stay(REG_HOURS),
        ],
        REG_SIG: [
            MessageHandler(filters.PHOTO, reg_sig_photo),
            CallbackQueryHandler(reg_sig_skip, pattern="^skip_sig$"),
            _stay(REG_SIG),
        ],
    },
    fallbacks=[CommandHandler("cancel", reg_cancel)],
    allow_reentry=True,
    per_message=False,
)
