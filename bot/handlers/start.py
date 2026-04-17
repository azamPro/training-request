from telegram import Update
from telegram.ext import ContextTypes

from bot.database.db import get_db
from bot.database.models import User, TrainingRequest
from bot.utils import (
    WELCOME_NEW, MAIN_MENU, NOT_REGISTERED,
    main_menu_keyboard, welcome_keyboard, profile_keyboard, back_keyboard,
)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()

    if user:
        await update.effective_message.reply_text(
            f"👋 أهلاً *{user.full_name}*!\n\n{MAIN_MENU}",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await update.effective_message.reply_text(
            WELCOME_NEW,
            parse_mode="Markdown",
            reply_markup=welcome_keyboard(),
        )


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()

    if user:
        await update.callback_query.message.reply_text(
            f"👋 أهلاً *{user.full_name}*!\n\n{MAIN_MENU}",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await update.callback_query.message.reply_text(
            WELCOME_NEW,
            parse_mode="Markdown",
            reply_markup=welcome_keyboard(),
        )


async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()
        if not user:
            await update.callback_query.message.reply_text(NOT_REGISTERED)
            return
        sig = "✅ محفوظ" if user.signature_path else "—"
        reg_date = user.created_at.strftime("%Y-%m-%d") if user.created_at else "—"
        full_name = user.full_name
        university_id = user.university_id
        department = user.department
        remaining_hours = user.remaining_hours

    await update.callback_query.message.reply_text(
        f"👤 *ملفك الشخصي*\n\n"
        f"الاسم: {full_name}\n"
        f"الرقم الجامعي: `{university_id}`\n"
        f"القسم: {department}\n"
        f"الساعات المتبقية: {remaining_hours}\n"
        f"التوقيع: {sig}\n"
        f"تاريخ التسجيل: {reg_date}",
        parse_mode="Markdown",
        reply_markup=profile_keyboard(),
    )


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()
        if not user:
            await update.message.reply_text(NOT_REGISTERED)
            return
        sig = "✅ محفوظ" if user.signature_path else "—"
        reg_date = user.created_at.strftime("%Y-%m-%d") if user.created_at else "—"
        full_name = user.full_name
        university_id = user.university_id
        department = user.department
        remaining_hours = user.remaining_hours

    await update.message.reply_text(
        f"👤 *ملفك الشخصي*\n\n"
        f"الاسم: {full_name}\n"
        f"الرقم الجامعي: `{university_id}`\n"
        f"القسم: {department}\n"
        f"الساعات المتبقية: {remaining_hours}\n"
        f"التوقيع: {sig}\n"
        f"تاريخ التسجيل: {reg_date}",
        parse_mode="Markdown",
        reply_markup=profile_keyboard(),
    )


async def history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()
        if not user:
            await update.callback_query.message.reply_text(NOT_REGISTERED)
            return

        requests = (
            db.query(TrainingRequest)
            .filter(TrainingRequest.user_id == user.id)
            .order_by(TrainingRequest.created_at.desc())
            .limit(5)
            .all()
        )

    if not requests:
        await update.callback_query.message.reply_text(
            "📋 لا توجد طلبات سابقة.\n\nاستخدم *📄 طلب جديد* لإنشاء أول طلب.",
            parse_mode="Markdown",
            reply_markup=back_keyboard(),
        )
        return

    lines = ["📋 *آخر 5 طلبات:*\n"]
    for i, r in enumerate(requests, 1):
        dt = r.created_at.strftime("%Y-%m-%d") if r.created_at else "—"
        lines.append(f"{i}. {r.company_name} — _{dt}_")

    await update.callback_query.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=back_keyboard(),
    )


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()
        if not user:
            await update.message.reply_text(NOT_REGISTERED)
            return

        requests = (
            db.query(TrainingRequest)
            .filter(TrainingRequest.user_id == user.id)
            .order_by(TrainingRequest.created_at.desc())
            .limit(5)
            .all()
        )

    if not requests:
        await update.message.reply_text(
            "📋 لا توجد طلبات سابقة.\n\nاستخدم /request لإنشاء أول طلب.",
        )
        return

    lines = ["📋 *آخر 5 طلبات:*\n"]
    for i, r in enumerate(requests, 1):
        dt = r.created_at.strftime("%Y-%m-%d") if r.created_at else "—"
        lines.append(f"{i}. {r.company_name} — _{dt}_")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def unknown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch all unrecognised messages and show the main menu."""
    tg_id = update.effective_user.id

    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == tg_id).first()

    if user:
        await update.message.reply_text(
            f"لم أفهم رسالتك. 😅\n\n{MAIN_MENU}",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await update.message.reply_text(
            WELCOME_NEW,
            parse_mode="Markdown",
            reply_markup=welcome_keyboard(),
        )
