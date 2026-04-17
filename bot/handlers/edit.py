"""
Selective edit conversation — lets an existing user update one field at a time.

Entry points:
  /edit command
  cb_edit inline button
"""

import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
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
from bot.config import GENERATED_PDF_DIR, WEBAPP_URL
from bot.utils import arabic_to_western, main_menu_keyboard, NOT_REGISTERED, decode_webapp_image

EDIT_CHOOSE, EDIT_VALUE = range(2)

_FIELD_LABELS = {
    "full_name":       "الاسم الكامل",
    "university_id":   "الرقم الجامعي",
    "department":      "القسم",
    "remaining_hours": "الساعات المتبقية",
    "signature":       "التوقيع",
}

_CANCEL_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("❌ إلغاء", callback_data="edit_cancel")]
])


def _choose_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"edit_field:{key}")]
        for key, label in _FIELD_LABELS.items()
    ]
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="edit_cancel")])
    return InlineKeyboardMarkup(buttons)


async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        send = update.callback_query.message.reply_text
    else:
        send = update.message.reply_text

    tg_id = update.effective_user.id
    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()

    if not user:
        await send(NOT_REGISTERED)
        return ConversationHandler.END

    await send(
        "✏️ *تعديل البيانات*\n\nماذا تريد أن تعدّل؟",
        parse_mode="Markdown",
        reply_markup=_choose_keyboard(),
    )
    return EDIT_CHOOSE


async def edit_field_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    field = update.callback_query.data.split(":")[1]
    context.user_data["edit_field"] = field
    label = _FIELD_LABELS[field]

    if field == "signature":
        if WEBAPP_URL:
            kb = ReplyKeyboardMarkup(
                [
                    [KeyboardButton("✍️ افتح لوحة التوقيع", web_app=WebAppInfo(url=WEBAPP_URL))],
                    [KeyboardButton("⏭ تخطي (إبقاء الحالي)")],
                ],
                resize_keyboard=True,
                one_time_keyboard=True,
            )
            await update.callback_query.message.reply_text(
                "✍️ *تعديل التوقيع*\n\n"
                "اضغط *افتح لوحة التوقيع* لرسم توقيع جديد بإصبعك،\n"
                "أو *تخطي* للإبقاء على التوقيع الحالي.",
                parse_mode="Markdown",
                reply_markup=kb,
            )
        else:
            await update.callback_query.message.reply_text(
                "✍️ أرسل *صورة توقيعك* الجديد:",
                parse_mode="Markdown",
                reply_markup=_CANCEL_KB,
            )
    else:
        prompts = {
            "full_name":       "أدخل *اسمك الكامل* الجديد:",
            "university_id":   "أدخل *رقمك الجامعي* الجديد:",
            "department":      "أدخل *اسم قسمك* الجديد:",
            "remaining_hours": "أدخل عدد *الساعات المتبقية* الجديد (أرقام فقط):",
        }
        await update.callback_query.message.reply_text(
            prompts[field],
            parse_mode="Markdown",
            reply_markup=_CANCEL_KB,
        )

    return EDIT_VALUE


async def edit_value_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    field = context.user_data.get("edit_field")
    value = update.message.text.strip()

    if field == "remaining_hours":
        value = arabic_to_western(value)
        if not value.isdigit():
            await update.message.reply_text(
                "⚠️ الرجاء إدخال *رقم فقط* مثل: 42",
                parse_mode="Markdown",
                reply_markup=_CANCEL_KB,
            )
            return EDIT_VALUE
    elif field == "university_id":
        value = arabic_to_western(value)

    if value.startswith("⏭"):
        context.user_data.clear()
        await update.message.reply_text(
            "✅ تم الإبقاء على البيانات الحالية.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await update.message.reply_text("اختر ما تريد:", reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    return await _save_field(update, context, field, value)


async def edit_value_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    field = context.user_data.get("edit_field")
    if field != "signature":
        return EDIT_VALUE

    photo = update.message.photo[-1]
    sig_dir = os.path.join(GENERATED_PDF_DIR, "signatures")
    os.makedirs(sig_dir, exist_ok=True)

    tg_id = update.effective_user.id
    sig_path = os.path.join(sig_dir, f"{tg_id}_sig.jpg")
    file = await update.get_bot().get_file(photo.file_id)
    await file.download_to_drive(sig_path)

    return await _save_field(update, context, "signature_path", sig_path)


async def edit_value_webapp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    field = context.user_data.get("edit_field")
    if field != "signature":
        return EDIT_VALUE

    result = decode_webapp_image(update.message.web_app_data.data)
    if result is None:
        await update.message.reply_text("⚠️ بيانات التوقيع غير صالحة. حاول مرة أخرى.")
        return EDIT_VALUE

    img_bytes, ext = result
    sig_dir = os.path.join(GENERATED_PDF_DIR, "signatures")
    os.makedirs(sig_dir, exist_ok=True)

    tg_id = update.effective_user.id
    sig_path = os.path.join(sig_dir, f"{tg_id}_sig{ext}")
    with open(sig_path, "wb") as f:
        f.write(img_bytes)

    return await _save_field(update, context, "signature_path", sig_path)


async def _save_field(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    field: str,
    value: str,
) -> int:
    tg_id = update.effective_user.id
    label = _FIELD_LABELS.get(field, _FIELD_LABELS.get("signature"))

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()
        if not user:
            await update.message.reply_text(NOT_REGISTERED)
            context.user_data.clear()
            return ConversationHandler.END

        if field == "signature_path":
            user.signature_path = value
            display = "✅ تم تحديث *التوقيع* بنجاح!"
        else:
            setattr(user, field, value)
            display = f"✅ تم تحديث *{_FIELD_LABELS[field]}* إلى:\n`{value}`"

    context.user_data.clear()
    await update.message.reply_text(
        display,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    await update.message.reply_text("اختر ما تريد:", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


async def edit_cancel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    context.user_data.clear()
    await update.callback_query.edit_message_text("❌ تم إلغاء التعديل.")
    await update.callback_query.message.reply_text(
        "اختر ما تريد:", reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END


async def edit_cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "❌ تم إلغاء التعديل.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await update.message.reply_text("اختر ما تريد:", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


edit_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("edit", edit_start),
        CallbackQueryHandler(edit_start, pattern="^cb_edit$"),
    ],
    states={
        EDIT_CHOOSE: [
            CallbackQueryHandler(edit_field_chosen, pattern=r"^edit_field:"),
            CallbackQueryHandler(edit_cancel_cb, pattern="^edit_cancel$"),
        ],
        EDIT_VALUE: [
            MessageHandler(filters.StatusUpdate.WEB_APP_DATA, edit_value_webapp),
            MessageHandler(filters.PHOTO, edit_value_photo),
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value_text),
            CallbackQueryHandler(edit_cancel_cb, pattern="^edit_cancel$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", edit_cancel_cmd)],
    allow_reentry=True,
    per_message=False,
)
