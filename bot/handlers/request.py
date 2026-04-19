"""
Training request conversation — asks for company name + optional description,
generates and sends PDF with the user's saved signature embedded if available.

Entry points:
  /request command
  cb_request inline button
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from bot.database.db import get_db, log_event
from bot.database.models import User, TrainingRequest
from bot.pdf.filler import FormData, fill_form_to_bytes
from bot.storage import save_pdf
from bot.utils import NOT_REGISTERED, main_menu_keyboard

REQ_COMPANY, REQ_DESC = range(2)

_SKIP_DESC_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("⏭ تخطي", callback_data="skip_desc")]
])

_BUSY_MSG = "⚠️ أدخل اسم الشركة أولاً، أو أرسل /cancel للخروج."


def _stay(state: int) -> CallbackQueryHandler:
    async def _h(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.callback_query.answer(_BUSY_MSG)
        return state
    return CallbackQueryHandler(_h)


async def request_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
        "🏢 *طلب تدريب جديد*\n\nأدخل *اسم الشركة* التي تتقدم إليها:",
        parse_mode="Markdown",
    )
    return REQ_COMPANY


async def req_company(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["company_name"] = update.message.text.strip()
    await update.message.reply_text(
        "📝 *وصف الشركة* — اختياري\n\n"
        "أدخل وصفاً مختصراً للشركة أو مجال عملها،\n"
        "أو اضغط *تخطي* إذا لم ترد إضافة وصف.",
        parse_mode="Markdown",
        reply_markup=_SKIP_DESC_KB,
    )
    return REQ_DESC


async def req_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["company_description"] = update.message.text.strip()
    return await _generate_and_send(update, context)


async def req_desc_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    context.user_data["company_description"] = None
    return await _generate_and_send(update, context, via_callback=True)


async def _generate_and_send(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    via_callback: bool = False,
) -> int:
    msg = update.callback_query.message if via_callback else update.message
    company_name = context.user_data["company_name"]
    company_description = context.user_data.get("company_description")
    tg_id = update.effective_user.id

    processing_msg = await msg.reply_text("⏳ جاري إنشاء الطلب...")

    try:
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == tg_id).first()
            if not user:
                await processing_msg.edit_text(NOT_REGISTERED)
                return ConversationHandler.END

            form_data = FormData(
                full_name            = user.full_name,
                university_id        = user.university_id,
                department           = user.department,
                remaining_hours      = user.remaining_hours,
                company_name         = company_name,
                company_description  = company_description,
                signature_image_path = user.signature_path,
            )

            pdf_bytes = fill_form_to_bytes(form_data)

            req = TrainingRequest(
                user_id=user.id,
                company_name=company_name,
                company_description=company_description,
            )
            db.add(req)
            db.flush()

            req.pdf_path = save_pdf(pdf_bytes, tg_id, req.id)
            log_event(tg_id, "request", company_name)

        caption = f"✅ *تم إنشاء طلب التدريب*\n\nالشركة: {company_name}\n"
        if company_description:
            caption += f"الوصف: {company_description}\n"
        caption += "\nأرسل هذا النموذج لمنسق التدريب في قسمك."

        await processing_msg.delete()
        await msg.reply_document(
            document=pdf_bytes,
            filename=f"طلب_تدريب_{company_name}.pdf",
            caption=caption,
            parse_mode="Markdown",
        )
        await msg.reply_text(
            "اختر ما تريد القيام به:",
            reply_markup=main_menu_keyboard(),
        )

    except Exception as e:
        await processing_msg.edit_text(
            "⚠️ حدث خطأ أثناء إنشاء الطلب. حاول مرة أخرى أو تواصل مع المسؤول."
        )
        raise e

    context.user_data.clear()
    return ConversationHandler.END


async def req_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "❌ تم إلغاء الطلب.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


request_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("request", request_start),
        CallbackQueryHandler(request_start, pattern="^cb_request$"),
    ],
    states={
        REQ_COMPANY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE, req_company),
            _stay(REQ_COMPANY),
        ],
        REQ_DESC: [
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE, req_desc),
            CallbackQueryHandler(req_desc_skip, pattern="^skip_desc$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", req_cancel)],
    allow_reentry=True,
    per_message=False,
)
