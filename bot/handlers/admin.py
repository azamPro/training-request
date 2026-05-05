"""
Admin-only commands: /admin (analytics) and /admin_errors (error log with delete).
"""

from datetime import datetime, timedelta

from sqlalchemy import func
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from telegram.helpers import escape_markdown

from bot.config import ADMIN_TELEGRAM_ID, USE_S3, AWS_S3_BUCKET, AWS_REGION
from bot.database.db import get_db
from bot.database.models import BotEvent, TrainingRequest, User


def _esc(text: str) -> str:
    return escape_markdown(str(text), version=1)


def _is_admin(tg_id: int) -> bool:
    return bool(ADMIN_TELEGRAM_ID and tg_id == ADMIN_TELEGRAM_ID)


async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر للمسؤول فقط.")
        return

    now = datetime.utcnow()
    today = now.date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    with get_db() as db:
        total_users = db.query(func.count(User.id)).scalar() or 0
        total_requests = db.query(func.count(TrainingRequest.id)).scalar() or 0

        users_today = db.query(func.count(User.id)).filter(func.date(User.created_at) == today).scalar() or 0
        users_week = db.query(func.count(User.id)).filter(func.date(User.created_at) >= week_ago).scalar() or 0
        users_month = db.query(func.count(User.id)).filter(func.date(User.created_at) >= month_ago).scalar() or 0

        req_today = db.query(func.count(TrainingRequest.id)).filter(func.date(TrainingRequest.created_at) == today).scalar() or 0
        req_week = db.query(func.count(TrainingRequest.id)).filter(func.date(TrainingRequest.created_at) >= week_ago).scalar() or 0
        req_month = db.query(func.count(TrainingRequest.id)).filter(func.date(TrainingRequest.created_at) >= month_ago).scalar() or 0

        with_sig = db.query(func.count(User.id)).filter(User.signature_path.isnot(None)).scalar() or 0

        top_companies = (
            db.query(TrainingRequest.company_name, func.count(TrainingRequest.id).label("cnt"))
            .group_by(TrainingRequest.company_name)
            .order_by(func.count(TrainingRequest.id).desc())
            .limit(5)
            .all()
        )

        top_users = (
            db.query(User.full_name, func.count(TrainingRequest.id).label("cnt"))
            .join(TrainingRequest, TrainingRequest.user_id == User.id)
            .group_by(User.id, User.full_name)
            .order_by(func.count(TrainingRequest.id).desc())
            .limit(3)
            .all()
        )

        latest_users = (
            db.query(User.full_name, User.telegram_username, User.created_at)
            .order_by(User.created_at.desc())
            .limit(5)
            .all()
        )

        active_today = (
            db.query(func.count(func.distinct(BotEvent.telegram_id)))
            .filter(func.date(BotEvent.created_at) == today)
            .scalar() or 0
        )

        recent_errors = (
            db.query(BotEvent.telegram_id, BotEvent.payload, BotEvent.created_at)
            .filter(BotEvent.event_type == "error")
            .order_by(BotEvent.created_at.desc())
            .limit(3)
            .all()
        )

        pdfs_on_s3 = (
            db.query(func.count(TrainingRequest.id))
            .filter(TrainingRequest.pdf_path.like("s3://%"))
            .scalar() or 0
        )
        pdfs_on_local = (
            db.query(func.count(TrainingRequest.id))
            .filter(TrainingRequest.pdf_path.notlike("s3://%"), TrainingRequest.pdf_path.isnot(None))
            .scalar() or 0
        )
        pdfs_no_path = (
            db.query(func.count(TrainingRequest.id))
            .filter(TrainingRequest.pdf_path.is_(None))
            .scalar() or 0
        )

    avg_req = round(total_requests / total_users, 1) if total_users else 0

    companies_text = "\n".join(
        f"  {i + 1}. {_esc(name)} ({cnt})" for i, (name, cnt) in enumerate(top_companies)
    ) or "  —"

    top_users_text = "\n".join(
        f"  {i + 1}. {_esc(name)} ({cnt} طلب)" for i, (name, cnt) in enumerate(top_users)
    ) or "  —"

    latest_text = "\n".join(
        f"  • {_esc(name)}{' (@' + _esc(uname) + ')' if uname else ''} — {dt.strftime('%Y-%m-%d') if dt else '—'}"
        for name, uname, dt in latest_users
    ) or "  —"

    errors_text = "\n".join(
        f"  • `{tid}` — {_esc((payload or '')[:60])} ({dt.strftime('%m-%d %H:%M') if dt else '—'})"
        for tid, payload, dt in recent_errors
    ) or "  لا توجد أخطاء"

    storage_mode = f"S3 (`{AWS_S3_BUCKET}` / `{AWS_REGION}`)" if USE_S3 else "Local disk"
    storage_text = (
        f"  الوضع: {storage_mode}\n"
        f"  في S3: {pdfs_on_s3} | محلي: {pdfs_on_local} | بدون مسار: {pdfs_no_path}"
    )

    msg = (
        f"📊 *لوحة تحكم المسؤول*\n"
        f"🕐 {now.strftime('%Y-%m-%d %H:%M')} UTC\n\n"
        f"👥 *المستخدمون*\n"
        f"  الإجمالي: *{total_users}* | نشطون اليوم: {active_today}\n"
        f"  جدد — اليوم: {users_today} | الأسبوع: {users_week} | الشهر: {users_month}\n"
        f"  بتوقيع محفوظ: {with_sig}/{total_users}\n\n"
        f"📄 *الطلبات*\n"
        f"  الإجمالي: *{total_requests}*\n"
        f"  اليوم: {req_today} | الأسبوع: {req_week} | الشهر: {req_month}\n"
        f"  متوسط لكل مستخدم: {avg_req}\n\n"
        f"🏢 *أكثر الشركات طلباً*\n{companies_text}\n\n"
        f"🏆 *أكثر المستخدمين نشاطاً*\n{top_users_text}\n\n"
        f"🆕 *آخر التسجيلات*\n{latest_text}\n\n"
        f"🗄 *التخزين*\n{storage_text}\n\n"
        f"🚨 *آخر الأخطاء*\n{errors_text}"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


# ── Error log (/admin_errors) ─────────────────────────────────────────────────

def _fetch_errors() -> list:
    with get_db() as db:
        return (
            db.query(BotEvent.id, BotEvent.telegram_id, BotEvent.payload, BotEvent.created_at)
            .filter(BotEvent.event_type == "error")
            .order_by(BotEvent.created_at.desc())
            .limit(5)
            .all()
        )


def _build_errors_message(errors: list) -> tuple:
    if not errors:
        return "✅ لا توجد أخطاء مسجلة.", InlineKeyboardMarkup([])

    lines = ["🚨 *سجل الأخطاء* — آخر 5 أخطاء\n"]
    btn_rows = []

    for i, (err_id, tid, payload, created_at) in enumerate(errors, 1):
        dt_str = created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else "—"
        payload_text = _esc((payload or "—")[:300])
        lines.append(
            f"*{i}.* 🕐 `{dt_str}`\n"
            f"   👤 `{tid}`\n"
            f"   ❌ {payload_text}\n"
        )
        btn_rows.append([InlineKeyboardButton(f"🗑 حذف #{i}", callback_data=f"del_error_{err_id}")])

    return "\n".join(lines), InlineKeyboardMarkup(btn_rows)


async def admin_errors_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر للمسؤول فقط.")
        return

    errors = _fetch_errors()
    msg, kb = _build_errors_message(errors)
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)


async def delete_error_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    if not _is_admin(update.effective_user.id):
        await query.answer("❌ غير مصرح", show_alert=True)
        return

    await query.answer()

    error_id = int(query.data[len("del_error_"):])
    with get_db() as db:
        err = db.query(BotEvent).filter(BotEvent.id == error_id).first()
        if err:
            db.delete(err)

    errors = _fetch_errors()
    msg, kb = _build_errors_message(errors)
    try:
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb)
    except Exception:
        pass
