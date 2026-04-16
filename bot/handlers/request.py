"""
Training request conversation handler.

Flow:
  /request
    → check user is registered
    → ask for company name
    → generate PDF
    → send PDF + save to DB
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

REQ_COMPANY = 0

_CANCEL_TEXT = "❌ Request cancelled. Use /request to start a new one."


async def request_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()

    if not user:
        await update.message.reply_text(
            "You don't have a profile yet. Use /register first."
        )
        return ConversationHandler.END

    context.user_data["user_db_id"] = user.id
    await update.message.reply_text(
        "🏢 Enter the *company name* you're applying to:",
        parse_mode="Markdown",
    )
    return REQ_COMPANY


async def req_company(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    company_name = update.message.text.strip()
    tg_id = update.effective_user.id

    await update.message.reply_text("⏳ Generating your PDF...")

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()
        if not user:
            await update.message.reply_text("Profile not found. Use /register.")
            return ConversationHandler.END

        form_data = FormData(
            full_name=user.full_name,
            university_id=user.university_id,
            department=user.department,
            remaining_hours=user.remaining_hours,
            company_name=company_name,
            signature=user.full_name,  # text signature fallback
        )

        pdf_bytes = fill_form_to_bytes(form_data)

        # Save record to DB
        req = TrainingRequest(
            user_id=user.id,
            company_name=company_name,
        )
        db.add(req)
        db.flush()  # get req.id before commit

        # Optionally save PDF file to disk
        filename = f"{tg_id}_{req.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        pdf_path = os.path.join(GENERATED_PDF_DIR, filename)
        os.makedirs(GENERATED_PDF_DIR, exist_ok=True)
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        req.pdf_path = pdf_path

    await update.message.reply_document(
        document=pdf_bytes,
        filename=f"training_request_{company_name}.pdf",
        caption=(
            f"✅ *Training Request — {company_name}*\n\n"
            "Submit this PDF to your department coordinator."
        ),
        parse_mode="Markdown",
    )

    context.user_data.clear()
    return ConversationHandler.END


async def req_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(_CANCEL_TEXT)
    return ConversationHandler.END


async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()
        if not user:
            await update.message.reply_text("No profile found. Use /register first.")
            return

        requests = (
            db.query(TrainingRequest)
            .filter(TrainingRequest.user_id == user.id)
            .order_by(TrainingRequest.created_at.desc())
            .limit(5)
            .all()
        )

    if not requests:
        await update.message.reply_text("You have no requests yet. Use /request to create one.")
        return

    lines = ["📋 *Your Last 5 Requests:*\n"]
    for i, r in enumerate(requests, 1):
        dt = r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "—"
        lines.append(f"{i}. {r.company_name} — _{dt}_")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def handle_inline_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'New Request' button from /start."""
    await update.callback_query.answer()
    tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()

    if not user:
        await update.callback_query.edit_message_text(
            "You don't have a profile yet. Use /register first."
        )
        return

    await update.callback_query.edit_message_text(
        "🏢 Enter the *company name* you're applying to:",
        parse_mode="Markdown",
    )
    context.user_data["awaiting_company"] = True


request_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("request", request_start),
    ],
    states={
        REQ_COMPANY: [MessageHandler(filters.TEXT & ~filters.COMMAND, req_company)],
    },
    fallbacks=[CommandHandler("cancel", req_cancel)],
    allow_reentry=True,
)
