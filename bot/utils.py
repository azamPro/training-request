from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def arabic_to_western(text: str) -> str:
    """Convert Arabic-Indic numerals ٠١٢٣٤٥٦٧٨٩ → 0-9."""
    return text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))


# ── Shared text ────────────────────────────────────────────────────────────

WELCOME_NEW = (
    "👋 *أهلاً بك في بوت طلب التدريب الصيفي!*\n\n"
    "هذا البوت يقوم بتعبئة نموذج طلب التدريب الصيفي تلقائياً.\n\n"
    "سجّل بياناتك *مرة واحدة* فقط، وبعدها كل طلب يحتاج اسم الشركة فقط.\n\n"
    "اضغط على الزر أدناه للبدء:"
)

MAIN_MENU = "اختر ما تريد القيام به:"

COMMANDS_LIST = (
    "📋 *الأوامر المتاحة:*\n\n"
    "/start — الصفحة الرئيسية\n"
    "/register — تسجيل أو تعديل بياناتك\n"
    "/profile — عرض بياناتك المحفوظة\n"
    "/request — إنشاء طلب تدريب جديد\n"
    "/history — سجل طلباتك السابقة\n"
    "/help — المساعدة\n"
    "`./ ` — عرض جميع الأوامر"
)

NOT_REGISTERED = "❌ لم يتم تسجيلك بعد. استخدم /register للتسجيل أولاً."


# ── Keyboards ───────────────────────────────────────────────────────────────

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📄 طلب جديد",       callback_data="cb_request"),
            InlineKeyboardButton("👤 ملفي الشخصي",    callback_data="cb_profile"),
        ],
        [
            InlineKeyboardButton("✏️ تعديل البيانات", callback_data="cb_edit"),
            InlineKeyboardButton("📋 سجل الطلبات",    callback_data="cb_history"),
        ],
        [InlineKeyboardButton("❓ المساعدة",           callback_data="cb_help")],
    ])


def welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تسجيل الآن", callback_data="cb_start_register")],
    ])


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 الرئيسية", callback_data="cb_main")],
    ])


def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ تعديل البيانات", callback_data="cb_edit")],
        [InlineKeyboardButton("🔙 الرئيسية",        callback_data="cb_main")],
    ])
