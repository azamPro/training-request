"""
Training request conversation — asks for company name, generates and sends PDF.

Entry points:
  /request command
  cb_request inline button
"""

import os
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from bot.database.db import get_db
from bot.database.models import User, TrainingRequest
from bot.pdf.filler import FormData, fill_form_to_bytes
from bot.config import GENERATED_PDF_DIR
from bot.utils import NOT_REGISTERED, main_menu_keyboard

REQ_COMPANY = 0

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
    company_name = update.message.text.strip()
    tg_id = update.effective_user.id

    processing_msg = await update.message.reply_text("⏳ جاري إنشاء الطلب...")

    try:
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == tg_id).first()
            if not user:
                await processing_msg.edit_text(NOT_REGISTERED)
                return ConversationHandler.END

            form_data = FormData(
                full_name      = user.full_name,
                university_id  = user.university_id,
                department     = user.department,
                remaining_hours= user.remaining_hours,
                company_name   = company_name,
                signature      = "",   # leave blank — student signs by hand
            )

            pdf_bytes = fill_form_to_bytes(form_data)

            req = TrainingRequest(user_id=user.id, company_name=company_name)
            db.add(req)
            db.flush()

            filename = f"{tg_id}_{req.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            pdf_path = os.path.join(GENERATED_PDF_DIR, filename)
            os.makedirs(GENERATED_PDF_DIR, exist_ok=True)
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
            req.pdf_path = pdf_path

        await processing_msg.delete()
        await update.message.reply_document(
            document=pdf_bytes,
            filename=f"طلب_تدريب_{company_name}.pdf",
            caption=(
                f"✅ *تم إنشاء طلب التدريب*\n\n"
                f"الشركة: {company_name}\n\n"
                "أرسل هذا النموذج لمنسق التدريب في قسمك."
            ),
            parse_mode="Markdown",
        )
        await update.message.reply_text(
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
            MessageHandler(filters.TEXT & ~filters.COMMAND, req_company),
            _stay(REQ_COMPANY),
        ],
    },
    fallbacks=[CommandHandler("cancel", req_cancel)],
    allow_reentry=True,
    per_message=False,
)
