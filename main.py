import os
import logging
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "7764329763"))
except Exception:
    ADMIN_ID = 7764329763

REFERRAL_PERCENT = 0.20

try:
    PORT = int(os.getenv("PORT", "10000"))
except Exception:
    PORT = 10000


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# =========================================================
# LANGUAGE / TRANSLATION
# =========================================================

TEXTS = {

    "bn": {

        # Main menu
        "balance": "💸 ব্যালেন্স",
        "tasks": "💰 কাজ",
        "withdraw": "📤 টাকা উত্তোলন",
        "profile": "👤 প্রোফাইল",
        "top": "🏆 সেরা ব্যবহারকারী",
        "referrals": "🫂 আমার রেফারেল",
        "language": "🌏 ভাষা",
        "admin_panel": "👨‍💻 অ্যাডমিন প্যানেল",

        # General
        "welcome": (
            "👋 Success Income Zone-এ স্বাগতম!\n\n"
            "💰 কাজ সম্পন্ন করে BDT আয় করুন।\n"
            "👥 বন্ধু রেফার করে ২০% কমিশন আয় করুন।\n\n"
            "👇 একটি অপশন নির্বাচন করুন:"
        ),

        "select_option": "👇 একটি অপশন নির্বাচন করুন:",
        "main_menu": "🏠 প্রধান মেনু",
        "cancel": "❌ বাতিল",
        "back": "🔙 ফিরে যান",

        # Balance
        "balance_title": "💸 ব্যালেন্স",
        "balance_amount": "💰 ব্যালেন্স",
        "referral_earnings": "🎁 রেফারেল আয়",

        # Profile
        "profile_title": "👤 প্রোফাইল",
        "no_username": "কোনো ইউজারনেম নেই",
        "user_id": "🆔 আইডি",
        "username": "👤 ইউজারনেম",
        "referrals_count": "👥 রেফারেল",
        "joined": "📅 যোগদানের সময়",

        # Referral
        "referral_title": "🫂 আমার রেফারেল",
        "referral_link": "🔗 আপনার রেফারেল লিংক",
        "referral_commission": "🎁 কমিশন",

        # Tasks
        "tasks_title": "📋 কাজসমূহ",
        "no_tasks": "❌ বর্তমানে কোনো কাজ নেই।",
        "select_task": "👇 একটি কাজ নির্বাচন করুন:",
        "task": "📋 কাজ",
        "reward": "💰 পুরস্কার",
        "review_time": "⏳ রিভিউ সময়",
        "description": "📄 বিবরণ",
        "uid": "🆔 UID",
        "report_instruction": "✍️ রিপোর্টের নির্দেশনা",
        "required": "প্রয়োজন",
        "not_required": "প্রয়োজন নেই",
        "start": "🚀 শুরু করুন",
        "task_started": "🚀 কাজ শুরু হয়েছে!",
        "send_uid": "🆔 আপনার প্রয়োজনীয় UID পাঠান:",
        "uid_received": "🆔 UID গ্রহণ করা হয়েছে।",
        "send_report": "📋 প্রয়োজনীয় রিপোর্ট পাঠান:",
        "valid_uid": "❌ একটি সঠিক UID পাঠান।",
        "report_empty": "❌ রিপোর্ট খালি রাখা যাবে না।",
        "report_received": "📋 রিপোর্ট গ্রহণ করা হয়েছে।",
        "confirm_submission": "আপনার সাবমিশন নিশ্চিত করুন:",
        "submit": "✅ জমা দিন",
        "submission_incomplete": "❌ সাবমিশন অসম্পূর্ণ।",
        "task_not_found": "❌ কাজটি পাওয়া যায়নি।",
        "uid_required": "❌ UID প্রয়োজন।",
        "submit_failed": (
            "❌ কাজ জমা দেওয়া যায়নি।\n\n"
            "অনুগ্রহ করে পরে আবার চেষ্টা করুন।"
        ),
        "report_received_success": (
            "✅ আপনার রিপোর্ট গ্রহণ করা হয়েছে!\n\n"
            "⏳ কাজটি অ্যাডমিন রিভিউয়ের অপেক্ষায় আছে।"
        ),
        "submission_cancelled": (
            "❌ সাবমিশন বাতিল করা হয়েছে।"
        ),

        # Withdraw
        "withdraw_title": "📤 টাকা উত্তোলন",
        "zero_balance": (
            "❌ আপনার ব্যালেন্স ০.০০ BDT।"
        ),
        "available_balance": "💰 বর্তমান ব্যালেন্স",
        "send_amount": "টাকা উত্তোলনের পরিমাণ পাঠান:",
        "invalid_amount": "❌ সঠিক পরিমাণ পাঠান।",
        "insufficient": "❌ পর্যাপ্ত ব্যালেন্স নেই।",
        "send_method": (
            "💳 টাকা উত্তোলনের মাধ্যম পাঠান:\n\n"
            "উদাহরণ:\n"
            "bKash\n"
            "Nagad\n"
            "Rocket"
        ),
        "send_account": "🏦 আপনার অ্যাকাউন্ট নম্বর পাঠান:",
        "withdraw_created": (
            "❌ টাকা উত্তোলনের অনুরোধ তৈরি করা যায়নি।"
        ),
        "withdraw_success": (
            "✅ টাকা উত্তোলনের অনুরোধ জমা হয়েছে!\n\n"
            "⏳ অ্যাডমিন রিভিউয়ের জন্য অপেক্ষা করুন।"
        ),
        "balance_update_failed": (
            "❌ ব্যালেন্স আপডেট করা যায়নি।"
        ),

        # Language
        "language_title": "🌏 ভাষা",
        "select_language": "ভাষা নির্বাচন করুন:",
        "bangla_selected": "🇧🇩 বাংলা ভাষা নির্বাচন করা হয়েছে।",
        "english_selected": "🇬🇧 English language selected.",

        # Top
        "top_title": "🏆 সেরা ব্যবহারকারী",
        "no_users": "❌ এখনো কোনো ব্যবহারকারী নেই।",

        # Admin
        "admin_not_allowed": "❌ আপনি অ্যাডমিন নন।",
        "access_denied": "❌ Access denied.",
        "admin_title": "👨‍💻 অ্যাডমিন প্যানেল",
        "admin_select": "👇 একটি অপশন নির্বাচন করুন:",
        "add_task": "➕ কাজ যোগ করুন",
        "all_tasks": "📋 সব কাজ",
        "delete_task": "🗑 কাজ মুছুন",
        "users": "👥 ব্যবহারকারী",
        "pending_tasks": "📥 Pending কাজ",
        "add_balance": "💰 ব্যালেন্স যোগ",
        "remove_balance": "➖ ব্যালেন্স কমান",
        "withdrawals": "📤 উত্তোলনসমূহ",

        "send_task_title": "📌 কাজের Title পাঠান:",
        "send_reward": (
            "💵 Reward BDT-তে পাঠান:\n\n"
            "উদাহরণ:\n"
            "10\n"
            "25.50"
        ),
        "invalid_reward": (
            "❌ Reward সঠিক নয়।\n\n"
            "উদাহরণ: 5.80"
        ),
        "send_review": (
            "⏳ Review Time ঘণ্টায় পাঠান:\n\n"
            "উদাহরণ:\n"
            "12"
        ),
        "invalid_review": (
            "❌ Review Hours সঠিক নয়।\n\n"
            "শুধু পূর্ণ সংখ্যা দিন।\n\n"
            "উদাহরণ: 12"
        ),
        "send_description": "📄 কাজের Description পাঠান:",
        "uid_requirement": (
            "🆔 UID Requirement:\n\n"
            "UID প্রয়োজন হলে YES পাঠান।\n"
            "UID প্রয়োজন না হলে NO পাঠান।"
        ),
        "yes_no": "❌ শুধু YES অথবা NO পাঠান।",
        "send_report_instruction": (
            "✍️ Report Instruction পাঠান:"
        ),
        "task_save_failed": (
            "❌ কাজ Save হয়নি।\n\n"
            "Supabase database error হয়েছে।\n"
            "Render Logs দেখুন।"
        ),
        "task_added": "✅ কাজ সফলভাবে যোগ হয়েছে!",
        "invalid_task_id": "❌ Task ID সঠিক নয়।",
        "task_deleted": "✅ কাজ মুছে ফেলা হয়েছে।",
        "task_id_not_found": "❌ Task ID পাওয়া যায়নি।",
        "no_tasks_admin": "❌ কোনো কাজ নেই।",
        "no_users_admin": "❌ কোনো ব্যবহারকারী নেই।",
        "no_pending": "📥 কোনো Pending submission নেই।",
        "no_withdrawals": "📤 কোনো Pending withdrawal নেই।",

        # Admin balance
        "add_balance_format": (
            "💰 ব্যালেন্স যোগ\n\n"
            "Format:\n"
            "USER_ID | AMOUNT\n\n"
            "উদাহরণ:\n"
            "7764329763 | 100"
        ),
        "remove_balance_format": (
            "➖ ব্যালেন্স কমান\n\n"
            "Format:\n"
            "USER_ID | AMOUNT"
        ),
        "wrong_format": (
            "❌ Format সঠিক নয়।\n\n"
            "USER_ID | AMOUNT"
        ),
        "balance_added": "✅ ব্যালেন্স যোগ করা হয়েছে।",
        "balance_removed": "✅ ব্যালেন্স কমানো হয়েছে।",

        # Review
        "task_approved": (
            "🎉 কাজ Approved!\n\n"
            "💰 Reward"
        ),
        "task_rejected": (
            "❌ কাজ Rejected হয়েছে।\n\n"
            "💰 কোনো Reward যোগ করা হয়নি।"
        ),
        "already_reviewed": "⚠️ এই submission ইতিমধ্যে review করা হয়েছে।",
        "submission_not_found": "❌ Submission পাওয়া যায়নি।",
        "withdraw_approved": "✅ টাকা উত্তোলন Approved হয়েছে!",
        "withdraw_rejected": "❌ টাকা উত্তোলন Rejected হয়েছে।",
        "money_returned": "আপনার ব্যালেন্সে টাকা ফেরত দেওয়া হয়েছে।",

        # Unknown
        "unknown": (
            "❓ অনুগ্রহ করে একটি অপশন নির্বাচন করুন।"
        ),
    },

    "en": {

        # Main menu
        "balance": "💸 Balance",
        "tasks": "💰 Tasks",
        "withdraw": "📤 Withdraw",
        "profile": "👤 Profile",
        "top": "🏆 Top",
        "referrals": "🫂 My Referrals",
        "language": "🌏 Language",
        "admin_panel": "👨‍💻 Admin Panel",

        # General
        "welcome": (
            "👋 Welcome to Success Income Zone!\n\n"
            "💰 Complete tasks and earn BDT.\n"
            "👥 Refer friends and earn 20% commission.\n\n"
            "👇 Select an option:"
        ),

        "select_option": "👇 Select an option:",
        "main_menu": "🏠 Main Menu",
        "cancel": "❌ Cancel",
        "back": "🔙 Back",

        # Balance
        "balance_title": "💸 BALANCE",
        "balance_amount": "💰 Balance",
        "referral_earnings": "🎁 Referral Earnings",

        # Profile
        "profile_title": "👤 PROFILE",
        "no_username": "No username",
        "user_id": "🆔 ID",
        "username": "👤 Username",
        "referrals_count": "👥 Referrals",
        "joined": "📅 Joined",

        # Referral
        "referral_title": "🫂 MY REFERRALS",
        "referral_link": "🔗 Your Referral Link",
        "referral_commission": "🎁 Earnings",

        # Tasks
        "tasks_title": "📋 Tasks",
        "no_tasks": "❌ Currently there are no tasks.",
        "select_task": "👇 Please select a task:",
        "task": "📋 Task",
        "reward": "💰 Reward",
        "review_time": "⏳ Review time",
        "description": "📄 Description",
        "uid": "🆔 UID",
        "report_instruction": "✍️ Report instruction",
        "required": "Required",
        "not_required": "Not Required",
        "start": "🚀 Start",
        "task_started": "🚀 Task Started!",
        "send_uid": "🆔 Send your required UID:",
        "uid_received": "🆔 UID received.",
        "send_report": "📋 Please send the required report:",
        "valid_uid": "❌ Please send a valid UID.",
        "report_empty": "❌ Report cannot be empty.",
        "report_received": "📋 Report received.",
        "confirm_submission": "Please confirm your submission:",
        "submit": "✅ Submit",
        "submission_incomplete": "❌ Submission incomplete.",
        "task_not_found": "❌ Task not found.",
        "uid_required": "❌ UID is required.",
        "submit_failed": (
            "❌ Could not submit task.\n\n"
            "Please try again later."
        ),
        "report_received_success": (
            "✅ Your report has been received!\n\n"
            "⏳ Task Pending Review"
        ),
        "submission_cancelled": (
            "❌ Submission cancelled."
        ),

        # Withdraw
        "withdraw_title": "📤 WITHDRAW",
        "zero_balance": (
            "❌ Your balance is 0.00 BDT."
        ),
        "available_balance": "💰 Available Balance",
        "send_amount": "Send withdrawal amount:",
        "invalid_amount": "❌ Invalid amount.",
        "insufficient": "❌ Insufficient balance.",
        "send_method": (
            "💳 Send withdrawal method:\n\n"
            "Example:\n"
            "bKash\n"
            "Nagad\n"
            "Rocket"
        ),
        "send_account": "🏦 Send your account number:",
        "withdraw_created": (
            "❌ Withdrawal request could not be created."
        ),
        "withdraw_success": (
            "✅ Withdrawal Request Submitted!\n\n"
            "⏳ Please wait for Admin review."
        ),
        "balance_update_failed": (
            "❌ Balance update failed."
        ),

        # Language
        "language_title": "🌏 LANGUAGE",
        "select_language": "Select language:",
        "bangla_selected": "🇧🇩 বাংলা ভাষা নির্বাচন করা হয়েছে।",
        "english_selected": "🇬🇧 English language selected.",

        # Top
        "top_title": "🏆 TOP USERS",
        "no_users": "❌ No users yet.",

        # Admin
        "admin_not_allowed": "❌ You are not an Admin.",
        "access_denied": "❌ Access denied.",
        "admin_title": "👨‍💻 ADMIN PANEL",
        "admin_select": "👇 Select an option:",
        "add_task": "➕ Add Task",
        "all_tasks": "📋 All Tasks",
        "delete_task": "🗑 Delete Task",
        "users": "👥 Users",
        "pending_tasks": "📥 Pending Tasks",
        "add_balance": "💰 Add Balance",
        "remove_balance": "➖ Remove Balance",
        "withdrawals": "📤 Withdrawals",

        "send_task_title": "📌 Send Task Title:",
        "send_reward": (
            "💵 Send Reward in BDT:\n\n"
            "Example:\n"
            "10\n"
            "25.50"
        ),
        "invalid_reward": (
            "❌ Invalid Reward.\n\n"
            "Example: 5.80"
        ),
        "send_review": (
            "⏳ Send Review Time in hours:\n\n"
            "Example:\n"
            "12"
        ),
        "invalid_review": (
            "❌ Invalid Review Hours.\n\n"
            "Please send whole number.\n\n"
            "Example: 12"
        ),
        "send_description": "📄 Send Task Description:",
        "uid_requirement": (
            "🆔 UID Requirement:\n\n"
            "Send YES if UID is required.\n"
            "Send NO if UID is not required."
        ),
        "yes_no": "❌ Please send YES or NO.",
        "send_report_instruction": (
            "✍️ Send Report Instruction:"
        ),
        "task_save_failed": (
            "❌ Task save failed.\n\n"
            "Supabase database error occurred.\n"
            "Please check Render Logs."
        ),
        "task_added": "✅ TASK ADDED SUCCESSFULLY!",
        "invalid_task_id": "❌ Invalid Task ID.",
        "task_deleted": "✅ Task Deleted.",
        "task_id_not_found": "❌ Task ID not found.",
        "no_tasks_admin": "❌ No tasks.",
        "no_users_admin": "❌ No users.",
        "no_pending": "📥 No pending submissions.",
        "no_withdrawals": "📤 No pending withdrawals.",

        # Admin balance
        "add_balance_format": (
            "💰 ADD BALANCE\n\n"
            "Format:\n"
            "USER_ID | AMOUNT\n\n"
            "Example:\n"
            "7764329763 | 100"
        ),
        "remove_balance_format": (
            "➖ REMOVE BALANCE\n\n"
            "Format:\n"
            "USER_ID | AMOUNT"
        ),
        "wrong_format": (
            "❌ Wrong Format.\n\n"
            "USER_ID | AMOUNT"
        ),
        "balance_added": "✅ Balance Added.",
        "balance_removed": "✅ Balance Removed.",

        # Review
        "task_approved": (
            "🎉 Task Approved!\n\n"
            "💰 Reward"
        ),
        "task_rejected": (
            "❌ Task Rejected\n\n"
            "💰 No reward was added."
        ),
        "already_reviewed": "⚠️ Already reviewed.",
        "submission_not_found": "❌ Submission not found.",
        "withdraw_approved": "✅ Withdrawal Approved!",
        "withdraw_rejected": "❌ Withdrawal Rejected.",
        "money_returned": "has been returned to your balance.",

        # Unknown
        "unknown": (
            "❓ Please select an option."
        ),
    },
}


def get_language(user_id):
    """
    User-এর database language বের করবে।
    Default বাংলা।
    """

    try:
        user = get_user_by_id(user_id)

        if user:
            language = user.get("language", "bn")

            if language in ("bn", "en"):
                return language

    except Exception:
        logger.exception("Language fetch error")

    return "bn"


def t(user_id, key):
    """
    Translation helper.
    """

    language = get_language(user_id)

    return TEXTS.get(
        language,
        TEXTS["bn"],
    ).get(
        key,
        key,
    )


def t_user(tg_user, key):
    return t(tg_user.id, key)


# =========================================================
# SUPABASE
# =========================================================

def supabase_headers():

    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def sb_get(table, params=None):

    try:

        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=supabase_headers(),
            params=params or {},
            timeout=20,
        )

        if not response.ok:

            logger.error(
                "Supabase GET %s %s: %s",
                table,
                response.status_code,
                response.text,
            )

            return []

        return response.json()

    except Exception:

        logger.exception(
            "Supabase GET exception"
        )

        return []


def sb_post(table, data):

    try:

        headers = supabase_headers()

        headers["Prefer"] = (
            "return=representation"
        )

        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=headers,
            json=data,
            timeout=20,
        )

        if not response.ok:

            logger.error(
                "Supabase POST %s %s: %s",
                table,
                response.status_code,
                response.text,
            )

            return None

        if not response.text:
            return []

        return response.json()

    except Exception:

        logger.exception(
            "Supabase POST exception"
        )

        return None


def sb_patch(table, params, data):

    try:

        headers = supabase_headers()

        headers["Prefer"] = (
            "return=representation"
        )

        response = requests.patch(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=headers,
            params=params,
            json=data,
            timeout=20,
        )

        if not response.ok:

            logger.error(
                "Supabase PATCH %s %s: %s",
                table,
                response.status_code,
                response.text,
            )

            return None

        if not response.text:
            return []

        return response.json()

    except Exception:

        logger.exception(
            "Supabase PATCH exception"
        )

        return None


def sb_delete(table, params):

    try:

        response = requests.delete(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=supabase_headers(),
            params=params,
            timeout=20,
        )

        if not response.ok:

            logger.error(
                "Supabase DELETE %s %s: %s",
                table,
                response.status_code,
                response.text,
            )

            return False

        return True

    except Exception:

        logger.exception(
            "Supabase DELETE exception"
        )

        return False


# =========================================================
# HEALTH SERVER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8",
        )

        self.end_headers()

        self.wfile.write(
            b"Success Income Zone Bot is running!"
        )

    def do_HEAD(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8",
        )

        self.end_headers()

    def log_message(self, format, *args):
        return


def run_health_server():

    try:

        server = HTTPServer(
            ("0.0.0.0", PORT),
            HealthHandler,
        )

        logger.info(
            "Health server started on port %s",
            PORT,
        )

        server.serve_forever()

    except Exception:

        logger.exception(
            "Health server crashed"
        )


# =========================================================
# USER
# =========================================================

def get_user(tg_user):

    user_id = tg_user.id

    rows = sb_get(
        "bot_users",
        {
            "id": f"eq.{user_id}",
            "limit": "1",
        },
    )

    if rows:

        user = rows[0]

        updated = sb_patch(
            "bot_users",
            {
                "id": f"eq.{user_id}",
            },
            {
                "first_name":
                    tg_user.first_name or "",

                "last_name":
                    tg_user.last_name or "",

                "username":
                    tg_user.username or "",
            },
        )

        if updated:
            return updated[0]

        return user

    data = {
        "id": user_id,
        "first_name":
            tg_user.first_name or "",
        "last_name":
            tg_user.last_name or "",
        "username":
            tg_user.username or "",
        "language": "bn",
        "balance": 0,
        "referral_earnings": 0,
        "referred_by": None,
        "joined_at":
            datetime.now().isoformat(),
    }

    result = sb_post(
        "bot_users",
        data,
    )

    if result:
        return result[0]

    return data


def get_user_by_id(user_id):

    rows = sb_get(
        "bot_users",
        {
            "id": f"eq.{user_id}",
            "limit": "1",
        },
    )

    return rows[0] if rows else None


def update_user(user_id, data):

    return sb_patch(
        "bot_users",
        {
            "id": f"eq.{user_id}",
        },
        data,
    )


# =========================================================
# TASKS
# =========================================================

def get_tasks():

    return sb_get(
        "tasks",
        {
            "is_active": "eq.true",
            "order": "id.asc",
        },
    )


def get_all_tasks():

    return sb_get(
        "tasks",
        {
            "order": "id.asc",
        },
    )


def get_task(task_id):

    rows = sb_get(
        "tasks",
        {
            "id": f"eq.{task_id}",
            "limit": "1",
        },
    )

    return rows[0] if rows else None


def get_submission(submission_id):

    rows = sb_get(
        "submissions",
        {
            "id": f"eq.{submission_id}",
            "limit": "1",
        },
    )

    return rows[0] if rows else None


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard(user_id=None):

    language = get_language(
        user_id
    ) if user_id else "bn"

    if language == "bn":

        keyboard = [
            [
                "💸 ব্যালেন্স",
                "💰 কাজ",
            ],
            [
                "📤 টাকা উত্তোলন",
                "👤 প্রোফাইল",
            ],
            [
                "🏆 সেরা ব্যবহারকারী",
                "🫂 আমার রেফারেল",
            ],
            [
                "🌏 ভাষা",
            ],
        ]

    else:

        keyboard = [
            [
                "💸 Balance",
                "💰 Tasks",
            ],
            [
                "📤 Withdraw",
                "👤 Profile",
            ],
            [
                "🏆 Top",
                "🫂 My Referrals",
            ],
            [
                "🌏 Language",
            ],
        ]

    if user_id == ADMIN_ID:

        keyboard.append(
            [
                (
                    "👨‍💻 অ্যাডমিন প্যানেল"
                    if language == "bn"
                    else "👨‍💻 Admin Panel"
                )
            ]
        )

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )


def cancel_keyboard(user_id):

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                t(user_id, "cancel"),
                callback_data="global_cancel",
            )
        ]
    ])


def admin_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "➕ Add Task",
                callback_data="admin_add_task",
            ),
            InlineKeyboardButton(
                "📋 All Tasks",
                callback_data="admin_all_tasks",
            ),
        ],

        [
            InlineKeyboardButton(
                "🗑 Delete Task",
                callback_data="admin_delete_task",
            ),
            InlineKeyboardButton(
                "👥 Users",
                callback_data="admin_users",
            ),
        ],

        [
            InlineKeyboardButton(
                "📥 Pending Tasks",
                callback_data="admin_pending",
            ),
            InlineKeyboardButton(
                "💰 Add Balance",
                callback_data="admin_add_balance",
            ),
        ],

        [
            InlineKeyboardButton(
                "➖ Remove Balance",
                callback_data="admin_remove_balance",
            ),
            InlineKeyboardButton(
                "📤 Withdrawals",
                callback_data="admin_withdrawals",
            ),
        ],

        [
            InlineKeyboardButton(
                "🔙 Main Menu",
                callback_data="admin_main_menu",
            ),
    ])


def admin_cancel_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "❌ Cancel",
                callback_data="admin_cancel",
            )
        ]
    ])


# =========================================================
# START
# =========================================================

async def start(update, context):

    if not update.effective_user:
        return

    tg_user = update.effective_user

    user = get_user(tg_user)

    # Referral
    if context.args:

        referral_id = context.args[0]

        if referral_id.isdigit():

            referral_id = int(
                referral_id
            )

            if referral_id != tg_user.id:

                if user.get(
                    "referred_by"
                ) is None:

                    referrer = (
                        get_user_by_id(
                            referral_id
                        )
                    )

                    if referrer:

                        update_user(
                            tg_user.id,
                            {
                                "referred_by":
                                    referral_id
                            },
                        )

    context.user_data.clear()

    await update.message.reply_text(
        t_user(
            tg_user,
            "welcome",
        ),
        reply_markup=main_keyboard(
            tg_user.id
        ),
    )


# =========================================================
# BALANCE
# =========================================================

async def balance(update, context):

    user = get_user(
        update.effective_user
    )

    user_id = update.effective_user.id

    language = get_language(
        user_id
    )

    await update.message.reply_text(

        f"{t(user_id, 'balance_title')}\n\n"

        f"{t(user_id, 'balance_amount')}: "
        f"{float(user.get('balance', 0)):.2f} BDT\n\n"

        f"{t(user_id, 'referral_earnings')}: "
        f"{float(user.get('referral_earnings', 0)):.2f} BDT",

        reply_markup=main_keyboard(
            user_id
        ),
    )


# =========================================================
# PROFILE
# =========================================================

async def profile(update, context):

    user = get_user(
        update.effective_user
    )

    user_id = update.effective_user.id

    username = (
        "@" + user.get("username", "")
        if user.get("username")
        else t(
            user_id,
            "no_username",
        )
    )

    referrals = sb_get(
        "bot_users",
        {
            "referred_by":
                f"eq.{user['id']",
            "select": "id",
        },
    )

    await update.message.reply_text(

        f"{t(user_id, 'profile_title')}\n\n"

        f"{t(user_id, 'user_id')}: "
        f"{user['id']}\n"

        f"{t(user_id, 'username')}: "
        f"{username}\n"

        f"{t(user_id, 'balance_amount')}: "
        f"{float(user.get('balance', 0)):.2f} BDT\n"

        f"{t(user_id, 'referrals_count')}: "
        f"{len(referrals)}\n"

        f"{t(user_id, 'referral_earnings')}: "
        f"{float(user.get('referral_earnings', 0)):.2f} BDT\n"

        f"{t(user_id, 'joined')}: "
        f"{user.get('joined_at', 'N/A')}",

        reply_markup=main_keyboard(
            user_id
        ),
    )


# =========================================================
# REFERRALS
# =========================================================

async def referrals(update, context):

    user = get_user(
        update.effective_user
    )

    user_id = update.effective_user.id

    bot = await context.bot.get_me()

    rows = sb_get(
        "bot_users",
        {
            "referred_by":
                f"eq.{user['id']}",
            "select": "id",
        },
    )

    link = (
        f"https://t.me/{bot.username}"
        f"?start={user['id']}"
    )

    await update.message.reply_text(

        f"{t(user_id, 'referral_title')}\n\n"

        f"{t(user_id, 'referrals_count')}: "
        f"{len(rows)}\n"

        f"{t(user_id, 'referral_commission')}: "
        f"{float(user.get('referral_earnings', 0)):.2f} BDT\n\n"

        f"{t(user_id, 'referral_link')}:\n"
        f"{link}",

        reply_markup=main_keyboard(
            user_id
        ),
    )


# =========================================================
# SHOW TASKS
# =========================================================

async def show_tasks(update, context):

    user_id = update.effective_user.id

    tasks = get_tasks()

    if not tasks:

        await update.message.reply_text(
            t(user_id, "no_tasks"),
            reply_markup=main_keyboard(
                user_id
            ),
        )

        return

    keyboard = []

    for task in tasks:

        reward = float(
            task.get("reward", 0)
        )

        keyboard.append([
            InlineKeyboardButton(
                f"{task.get('title', 'Task')} "
                f"({reward:.2f} BDT)",

                callback_data=
                f"select_task_{task['id']}",
            )
        ])

    await update.message.reply_text(

        f"{t(user_id, 'tasks_title')}\n\n"
        f"{t(user_id, 'select_task')}",

        reply_markup=
        InlineKeyboardMarkup(
            keyboard
        ),
    )


# =========================================================
# SELECT TASK
# =========================================================

async def select_task(update, context):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    task_id = query.data.replace(
        "select_task_",
        "",
    )

    task = get_task(task_id)

    if not task:

        await query.message.reply_text(
            t(user_id, "task_not_found")
        )

        return

    reward = float(
        task.get("reward", 0)
    )

    review_hours = int(
        task.get("review_hours", 0)
    )

    description = task.get(
        "description",
        "",
    )

    uid_required = str(
        task.get("uid", "")
    ).lower()

    report_instruction = task.get(
        "report_instruction",
        "",
    )

    uid_text = (
        t(user_id, "required")
        if uid_required in (
            "yes",
            "true",
            "required",
            "হ্যাঁ",
        )
        else
        t(user_id, "not_required")
    )

    text = (

        f"{t(user_id, 'task')}: "
        f"{task.get('title', '')}\n\n"

        f"{t(user_id, 'reward')}: "
        f"{reward:.2f} BDT\n\n"

        f"{t(user_id, 'review_time')}: "
        f"{review_hours} hours\n\n"

        f"{t(user_id, 'description')}:\n"
        f"{description}\n\n"

        f"{t(user_id, 'uid')}: "
        f"{uid_text}\n\n"

        f"{t(user_id, 'report_instruction')}:\n"
        f"{report_instruction}"
    )

    keyboard = [[
        InlineKeyboardButton(
            t(user_id, "start"),
            callback_data=
            f"start_task_{task['id']}",
        )
    ], [
        InlineKeyboardButton(
            t(user_id, "cancel"),
            callback_data="global_cancel",
        )
    ]]

    await query.message.reply_text(
        text,
        reply_markup=
        InlineKeyboardMarkup(
            keyboard
        ),
    )


# =========================================================
# START TASK
# =========================================================

async def start_task(update, context):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    task_id = query.data.replace(
        "start_task_",
        "",
    )

    task = get_task(task_id)

    if not task:

        await query.message.reply_text(
            t(user_id, "task_not_found")
        )

        return

    context.user_data.clear()

    context.user_data[
        "task_id"
    ] = int(task_id)

    uid_required = str(
        task.get("uid", "")
    ).lower()

    if uid_required in (
        "yes",
        "true",
        "required",
        "হ্যাঁ",
    ):

        context.user_data[
            "task_step"
        ] = "uid"

        await query.message.reply_text(
            f"{t(user_id, 'task_started')}\n\n"
            f"{t(user_id, 'send_uid')}",
            reply_markup=cancel_keyboard(
                user_id
            ),
        )

    else:

        context.user_data[
            "task_step"
        ] = "report"

        await query.message.reply_text(
            f"{t(user_id, 'task_started')}\n\n"
            f"{t(user_id, 'send_report')}",
            reply_markup=cancel_keyboard(
                user_id
            ),
        )


# =========================================================
# TASK TEXT FLOW
# =========================================================

async def process_task_text(update, context):

    step = context.user_data.get(
        "task_step"
    )

    if not step:
        return False

    if not update.message:
        return False

    user_id = update.effective_user.id

    text = update.message.text.strip()

    if step == "uid":

        if len(text) < 3:

            await update.message.reply_text(
                t(user_id, "valid_uid"),
                reply_markup=cancel_keyboard(
                    user_id
                ),
            )

            return True

        context.user_data[
            "task_uid"
        ] = text

        context.user_data[
            "task_step"
        ] = "report"

        task_id = context.user_data.get(
            "task_id"
        )

        task = get_task(task_id)

        report_instruction = ""

        if task:

            report_instruction = task.get(
                "report_instruction",
                "",
            )

        message = (
            f"{t(user_id, 'uid_received')}\n\n"
            f"{t(user_id, 'send_report')}"
        )

        if report_instruction:

            message += (
                "\n\n"
                f"{t(user_id, 'report_instruction')}:\n"
                f"{report_instruction}"
            )

        await update.message.reply_text(
            message,
            reply_markup=cancel_keyboard(
                user_id
            ),
        )

        return True

    if step == "report":

        if len(text) < 1:

            await update.message.reply_text(
                t(user_id, "report_empty"),
                reply_markup=cancel_keyboard(
                    user_id
                ),
            )

            return True

        context.user_data[
            "task_report"
        ] = text

        context.user_data[
            "task_step"
        ] = "confirm"

        await update.message.reply_text(

            f"{t(user_id, 'report_received')}\n\n"
            f"{t(user_id, 'confirm_submission')}",

            reply_markup=
            InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        t(user_id, "submit"),
                        callback_data=
                        "confirm_submission",
                    )
                ],

                [
                    InlineKeyboardButton(
                        t(user_id, "cancel"),
                        callback_data=
                        "global_cancel",
                    )
                ],

            ]),
        )

        return True

    return False


# =========================================================
# GLOBAL CANCEL
# =========================================================

async def global_cancel(update, context):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    context.user_data.clear()

    await query.message.reply_text(
        t(user_id, "submission_cancelled"),
        reply_markup=main_keyboard(
            user_id
        ),
    )


# =========================================================
# CONFIRM SUBMISSION
# =========================================================

async def confirm_submission(update, context):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    task_id = context.user_data.get(
        "task_id"
    )

    uid_value = context.user_data.get(
        "task_uid"
    )

    report = context.user_data.get(
        "task_report"
    )

    if not task_id or not report:

        await query.message.reply_text(
            t(
                user_id,
                "submission_incomplete",
            )
        )

        return

    task = get_task(task_id)

    if not task:

        await query.message.reply_text(
            t(
                user_id,
                "task_not_found",
            )
        )

        return

    uid_required = str(
        task.get("uid", "")
    ).lower()

    uid_is_required = uid_required in (
        "yes",
        "true",
        "required",
        "হ্যাঁ",
    )

    if uid_is_required and not uid_value:

        await query.message.reply_text(
            t(
                user_id,
                "uid_required",
            )
        )

        return

    user = get_user(
        query.from_user
    )

    reward = float(
        task.get("reward", 0)
    )

    data = {
        "user_id":
            user["id"],

        "task_id":
            int(task["id"]),

        "facebook_uid":
            uid_value or "",

        "written_report":
            report,

        "reward":
            reward,

        "status":
            "pending",

        "created_at":
            datetime.now().isoformat(),
    }

    result = sb_post(
        "submissions",
        data,
    )

    if not result:

        await query.message.reply_text(
            t(
                user_id,
                "submit_failed",
            ),
            reply_markup=main_keyboard(
                user_id
            ),
        )

        return

    submission = result[0]

    context.user_data.clear()

    await query.message.reply_text(
        t(
            user_id,
            "report_received_success",
        ),
        reply_markup=main_keyboard(
            user_id
        ),
    )

    # Admin notification
    try:

        uid_display = (
            uid_value
            if uid_value
            else "Not required"
        )

        await context.bot.send_message(

            chat_id=ADMIN_ID,

            text=(

                "📥 NEW TASK SUBMISSION\n\n"

                f"🆔 Submission: "
                f"{submission['id']}\n"

                f"👤 User ID: "
                f"{user['id']}\n"

                f"👤 Username: "
                f"@{user.get('username') or 'None'}\n\n"

                f"📋 Task: "
                f"{task.get('title', '')}\n"

                f"💰 Reward: "
                f"{reward:.2f} BDT\n\n"

                f"🆔 UID: "
                f"{uid_display}\n\n"

                f"📄 Report:\n"
                f"{report}"
            ),

            reply_markup=
            InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "✅ Approve",
                        callback_data=
                        f"approve_{submission['id']}",
                    ),

                    InlineKeyboardButton(
                        "❌ Reject",
                        callback_data=
                        f"reject_{submission['id']}",
                    ),
                ]

            ]),
        )

    except Exception:

        logger.exception(
            "Admin notification error"
        )


# =========================================================
# REVIEW TASK
# =========================================================

async def review_submission(update, context):

    query = update.callback_query

    await query.answer()

    if query.from_user.id != ADMIN_ID:

        await query.message.reply_text(
            "❌ Access denied."
        )

        return

    if query.data.startswith("approve_"):

        submission_id = query.data.replace(
            "approve_",
            "",
        )

        action = "approved"

    else:

        submission_id = query.data.replace(
            "reject_",
            "",
        )

        action = "rejected"

    submission = get_submission(
        submission_id
    )

    if not submission:

        await query.message.reply_text(
            "❌ Submission not found."
        )

        return

    if submission.get("status") != "pending":

        await query.message.reply_text(
            "⚠️ Already reviewed."
        )

        return

    user_id = submission["user_id"]

    reward = float(
        submission.get("reward", 0)
    )

    updated = sb_patch(
        "submissions",
        {
            "id":
                f"eq.{submission_id}"
        },
        {
            "status":
                action,

            "reviewed_at":
                datetime.now().isoformat(),

            "reviewed_by":
                ADMIN_ID,
        },
    )

    if not updated:

        await query.message.reply_text(
            "❌ Could not update submission."
        )

        return

    if action == "approved":

        user = get_user_by_id(
            user_id
        )

        if not user:

            await query.message.reply_text(
                "❌ User not found."
            )

            return

        old_balance = float(
            user.get("balance", 0)
        )

        new_balance = (
            old_balance + reward
        )

        updated_user = update_user(
            user_id,
            {
                "balance":
                    new_balance
            },
        )

        if not updated_user:

            await query.message.reply_text(
                "❌ Reward balance update failed."
            )

            return

        # Referral
        referrer_id = user.get(
            "referred_by"
        )

        if referrer_id:

            referrer = get_user_by_id(
                referrer_id
            )

            if referrer:

                commission = (
                    reward *
                    REFERRAL_PERCENT
                )

                ref_balance = float(
                    referrer.get(
                        "balance",
                        0,
                    )
                )

                ref_earnings = float(
                    referrer.get(
                        "referral_earnings",
                        0,
                    )
                )

                update_user(
                    referrer_id,
                    {
                        "balance":
                            ref_balance +
                            commission,

                        "referral_earnings":
                            ref_earnings +
                            commission,
                    },
                )

        await query.message.reply_text(

            "✅ TASK APPROVED\n\n"

            f"👤 User ID: "
            f"{user_id}\n"

            f"💰 Reward Added: "
            f"{reward:.2f} BDT"
        )

        try:

            final_user = get_user_by_id(
                user_id
            )

            language = get_language(
                user_id
            )

            if language == "bn":

                message = (
                    "🎉 কাজ Approved হয়েছে!\n\n"
                    f"💰 Reward: "
                    f"{reward:.2f} BDT\n\n"
                    f"💵 আপনার ব্যালেন্স: "
                    f"{float(final_user.get('balance', 0)):.2f} BDT"
                )

            else:

                message = (
                    "🎉 Task Approved!\n\n"
                    f"💰 Reward: "
                    f"{reward:.2f} BDT\n\n"
                    f"💵 Your Balance: "
                    f"{float(final_user.get('balance', 0)):.2f} BDT"
                )

            await context.bot.send_message(
                chat_id=user_id,
                text=message,
            )

        except Exception:

            logger.exception(
                "Approval notification error"
            )

    else:

        await query.message.reply_text(

            "❌ TASK REJECTED\n\n"

            f"👤 User ID: "
            f"{user_id}"
        )

        try:

            language = get_language(
                user_id
            )

            if language == "bn":

                message = (
                    "❌ কাজ Rejected হয়েছে।\n\n"
                    f"📋 Task ID: "
                    f"{submission.get('task_id')}\n\n"
                    "💰 কোনো Reward যোগ করা হয়নি।"
                )

            else:

                message = (
                    "❌ Task Rejected\n\n"
                    f"📋 Task ID: "
                    f"{submission.get('task_id')}\n\n"
                    "💰 No reward was added."
                )

            await context.bot.send_message(
                chat_id=user_id,
                text=message,
            )

        except Exception:

            logger.exception(
                "Rejection notification error"
            )


# =========================================================
# ADMIN
# =========================================================

async def admin_command(update, context):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            t(
                update.effective_user.id,
                "admin_not_allowed",
            )
        )

        return

    context.user_data.clear()

    await update.message.reply_text(
        t(
            update.effective_user.id,
            "admin_title",
        ) + "\n\n" +
        t(
            update.effective_user.id,
            "admin_select",
        ),
        reply_markup=admin_keyboard(),
    )


# =========================================================
# ADMIN CALLBACK
# =========================================================

async def admin_callback(update, context):

    query = update.callback_query

    await query.answer()

    if query.from_user.id != ADMIN_ID:

        await query.message.reply_text(
            "❌ Access denied."
        )

        return

    action = query.data

    # ADMIN CANCEL
    if action == "admin_cancel":

        context.user_data.clear()

        await query.message.reply_text(
            "❌ Cancelled.",
            reply_markup=admin_keyboard(),
        )

        return

    # MAIN
    if action == "admin_main_menu":

        context.user_data.clear()

        await query.message.reply_text(
            "🏠 Main Menu",
            reply_markup=main_keyboard(
                ADMIN_ID
            ),
        )

        return

    # ADD TASK
    if action == "admin_add_task":

        context.user_data.clear()

        context.user_data[
            "admin_state"
        ] = "task_title"

        await query.message.reply_text(
            "➕ ADD TASK\n\n"
            "📌 Send Task Title:",
            reply_markup=admin_cancel_keyboard(),
        )

        return

    # ALL TASKS
    if action == "admin_all_tasks":

        tasks = get_all_tasks()

        if not tasks:

            await query.message.reply_text(
                "📋 No tasks available."
            )

            return

        for task in tasks:

            await query.message.reply_text(

                "📋 TASK\n\n"

                f"🆔 ID: "
                f"{task.get('id')}\n"

                f"📌 Title: "
                f"{task.get('title', '')}\n"

                f"💰 Reward: "
                f"{float(task.get('reward', 0)):.2f} BDT\n"

                f"⏳ Review: "
                f"{int(task.get('review_hours', 0))} hours\n\n"

                f"📝 Description:\n"
                f"{task.get('description', '')}\n\n"

                f"🆔 UID: "
                f"{task.get('uid', '')}\n\n"

                f"✍️ Report:\n"
                f"{task.get('report_instruction', '')}\n\n"

                f"🟢 Active: "
                f"{task.get('is_active', True)}"
            )

        return

    # DELETE
    if action == "admin_delete_task":

        tasks = get_all_tasks()

        if not tasks:

            await query.message.reply_text(
                "❌ No tasks."
            )

            return

        text = "🗑 DELETE TASK\n\n"

        for task in tasks:

            text += (
                f"🆔 {task.get('id')}\n"
                f"📌 {task.get('title', '')}\n\n"
            )

        context.user_data[
            "admin_state"
        ] = "delete_task"

        await query.message.reply_text(
            text +
            "Send Task ID to delete:",
            reply_markup=admin_cancel_keyboard(),
        )

        return

    # PENDING
    if action == "admin_pending":

        pending = sb_get(
            "submissions",
            {
                "status":
                    "eq.pending",

                "order":
                    "id.asc",
            },
        )

        if not pending:

            await query.message.reply_text(
                "📥 No pending submissions."
            )

            return

        for submission in pending:

            await query.message.reply_text(

                "📥 PENDING SUBMISSION\n\n"

                f"🆔 Submission: "
                f"{submission.get('id')}\n"

                f"👤 User: "
                f"{submission.get('user_id')}\n"

                f"📋 Task ID: "
                f"{submission.get('task_id')}\n"

                f"💰 Reward: "
                f"{float(submission.get('reward', 0)):.2f} BDT\n"

                f"🆔 UID: "
                f"{submission.get('facebook_uid', '')}\n\n"

                f"📄 Report:\n"
                f"{submission.get('written_report', '')}",

                reply_markup=
                InlineKeyboardMarkup([

                    [
                        InlineKeyboardButton(
                            "✅ Approve",
                            callback_data=
                            f"approve_{submission['id']}",
                        ),

                        InlineKeyboardButton(
                            "❌ Reject",
                            callback_data=
                            f"reject_{submission['id']}",
                        ),
                    ]

                ]),
            )

        return

    # USERS
    if action == "admin_users":

        users = sb_get(
            "bot_users",
            {
                "select":
                    "id,first_name,username,balance",

                "order":
                    "id.asc",
            },
        )

        if not users:

            await query.message.reply_text(
                "👥 No users."
            )

            return

        text = (
            "👥 USERS\n\n"
            f"Total Users: "
            f"{len(users)}\n\n"
        )

        for user in users[:50]:

            text += (

                f"🆔 "
                f"{user.get('id')}\n"

                f"👤 "
                f"{user.get('first_name') or 'User'}\n"

                f"@"
                f"{user.get('username') or 'None'}\n"

                f"💰 "
                f"{float(user.get('balance', 0)):.2f} BDT\n\n"
            )

        await query.message.reply_text(
            text
        )

        return

    # ADD BALANCE
    if action == "admin_add_balance":

        context.user_data[
            "admin_state"
        ] = "add_balance"

        await query.message.reply_text(
            "💰 ADD BALANCE\n\n"
            "Format:\n"
            "USER_ID | AMOUNT\n\n"
            "Example:\n"
            "7764329763 | 100",

            reply_markup=admin_cancel_keyboard(),
        )

        return

    # REMOVE BALANCE
    if action == "admin_remove_balance":

        context.user_data[
            "admin_state"
        ] = "remove_balance"

        await query.message.reply_text(
            "➖ REMOVE BALANCE\n\n"
            "Format:\n"
            "USER_ID | AMOUNT",

            reply_markup=admin_cancel_keyboard(),
        )

        return

    # WITHDRAWALS
    if action == "admin_withdrawals":

        pending = sb_get(
            "withdrawals",
            {
                "status":
                    "eq.pending",

                "order":
                    "id.asc",
            },
        )

        if not pending:

            await query.message.reply_text(
                "📤 No pending withdrawals."
            )

            return

        for withdrawal in pending:

            await query.message.reply_text(

                "📤 PENDING WITHDRAWAL\n\n"

                f"🆔 Request: "
                f"{withdrawal.get('id')}\n"

                f"👤 User: "
                f"{withdrawal.get('user_id')}\n"

                f"💰 Amount: "
                f"{float(withdrawal.get('amount', 0)):.2f} BDT\n"

                f"💳 Method: "
                f"{withdrawal.get('method', '')}\n"

                f"🏦 Account: "
                f"{withdrawal.get('account_number', '')}",

                reply_markup=
                InlineKeyboardMarkup([

                    [
                        InlineKeyboardButton(
                            "✅ Approve",
                            callback_data=
                            f"approve_withdraw_{withdrawal['id']}",
                        ),

                        InlineKeyboardButton(
                            "❌ Reject",
                            callback_data=
                            f"reject_withdraw_{withdrawal['id']}",
                        ),
                    ]

                ]),
            )

        return


# =========================================================
# ADMIN TEXT
# =========================================================

async def process_admin_text(update, context):

    if update.effective_user.id != ADMIN_ID:
        return False

    if not update.message:
        return False

    state = context.user_data.get(
        "admin_state"
    )

    if not state:
        return False

    text = update.message.text.strip()

    # TITLE
    if state == "task_title":

        context.user_data[
            "new_task_title"
        ] = text

        context.user_data[
            "admin_state"
        ] = "task_reward"

        await update.message.reply_text(
            "💵 Send Reward in BDT:\n\n"
            "Example:\n"
            "10\n"
            "25.50",
            reply_markup=admin_cancel_keyboard(),
        )

        return True

    # REWARD
    if state == "task_reward":

        try:

            reward = float(text)

            if reward <= 0:
                raise ValueError

        except Exception:

            await update.message.reply_text(
                "❌ Invalid Reward.\n\n"
                "Example: 5.80",
                reply_markup=admin_cancel_keyboard(),
            )

            return True

        context.user_data[
            "new_task_reward"
        ] = reward

        context.user_data[
            "admin_state"
        ] = "task_review"

        await update.message.reply_text(
            "⏳ Send Review Time in hours:\n\n"
            "Example:\n"
            "12",
            reply_markup=admin_cancel_keyboard(),
        )

        return True

    # REVIEW
    if state == "task_review":

        try:

            review_float = float(text)

            if review_float < 0:
                raise ValueError

            if not review_float.is_integer():
                raise ValueError

            review_hours = int(
                review_float
            )

        except Exception:

            await update.message.reply_text(
                "❌ Invalid Review Hours.\n\n"
                "Please send whole number.\n\n"
                "Example: 12",
                reply_markup=admin_cancel_keyboard(),
            )

            return True

        context.user_data[
            "new_task_review"
        ] = review_hours

        context.user_data[
            "admin_state"
        ] = "task_description"

        await update.message.reply_text(
            "📄 Send Task Description:",
            reply_markup=admin_cancel_keyboard(),
        )

        return True

    # DESCRIPTION
    if state == "task_description":

        context.user_data[
            "new_task_description"
        ] = text

        context.user_data[
            "admin_state"
        ] = "task_uid"

        await update.message.reply_text(
            "🆔 UID Requirement:\n\n"
            "Send YES if UID is required.\n"
            "Send NO if UID is not required.",
            reply_markup=admin_cancel_keyboard(),
        )

        return True

    # UID
    if state == "task_uid":

        value = text.lower()

        if value not in (
            "yes",
            "no",
            "হ্যাঁ",
            "না",
        ):

            await update.message.reply_text(
                "❌ Please send YES or NO.",
                reply_markup=admin_cancel_keyboard(),
            )

            return True

        uid_value = (
            "yes"
            if value in (
                "yes",
                "হ্যাঁ",
            )
            else
            "no"
        )

        context.user_data[
            "new_task_uid"
        ] = uid_value

        context.user_data[
            "admin_state"
        ] = "task_report"

        await update.message.reply_text(
            "✍️ Send Report Instruction:",
            reply_markup=admin_cancel_keyboard(),
        )

        return True

    # REPORT + SAVE
    if state == "task_report":

        title = context.user_data.get(
            "new_task_title",
            "",
        )

        reward = context.user_data.get(
            "new_task_reward",
            0,
        )

        review_hours = context.user_data.get(
            "new_task_review",
            0,
        )

        description = context.user_data.get(
            "new_task_description",
            "",
        )

        uid_value = context.user_data.get(
            "new_task_uid",
            "no",
        )

        data = {

            "title":
                title,

            "reward":
                float(reward),

            "review_hours":
                int(review_hours),

            "description":
                description,

            "uid":
                uid_value,

            "report_instruction":
                text,

            "is_active":
                True,

            "created_at":
                datetime.now().isoformat(),
        }

        logger.info(
            "Trying to save task: %s",
            data,
        )

        result = sb_post(
            "tasks",
            data,
        )

        if not result:

            logger.error(
                "TASK SAVE FAILED. DATA=%s",
                data,
            )

            context.user_data.clear()

            await update.message.reply_text(
                "❌ Task save হয়নি।\n\n"
                "Supabase database error হয়েছে।\n"
                "Render Logs দেখুন।",

                reply_markup=admin_keyboard(),
            )

            return True

        task = result[0]

        context.user_data.clear()

        await update.message.reply_text(

            "✅ TASK ADDED SUCCESSFULLY!\n\n"

            f"🆔 Task ID: "
            f"{task.get('id')}\n"

            f"📌 Task: "
            f"{task.get('title', '')}\n"

            f"💰 Reward: "
            f"{float(task.get('reward', 0)):.2f} BDT\n"

            f"⏳ Review: "
            f"{int(task.get('review_hours', 0))} hours\n"

            f"🆔 UID: "
            f"{task.get('uid', '')}",

            reply_markup=admin_keyboard(),
        )

        return True

    # DELETE
    if state == "delete_task":

        try:

            task_id = int(text)

        except Exception:

            await update.message.reply_text(
                "❌ Invalid Task ID.",
                reply_markup=admin_cancel_keyboard(),
            )

            return True

        task = get_task(task_id)

        if not task:

            await update.message.reply_text(
                "❌ Task ID not found.",
                reply_markup=admin_cancel_keyboard(),
            )

            return True

        success = sb_delete(
            "tasks",
            {
                "id":
                    f"eq.{task_id}"
            },
        )

        if not success:

            await update.message.reply_text(
                "❌ Task delete হয়নি।",
                reply_markup=admin_cancel_keyboard(),
            )

            return True

        context.user_data.clear()

        await update.message.reply_text(
            "✅ Task Deleted\n\n"
            f"📌 {task.get('title', '')}",
            reply_markup=admin_keyboard(),
        )

        return True

    # ADD BALANCE
    if state == "add_balance":

        try:

            user_id, amount = text.split(
                "|",
                1,
            )

            user_id = int(
                user_id.strip()
            )

            amount = float(
                amount.strip()
            )

            if amount <= 0:
                raise ValueError

            user = get_user_by_id(
                user_id
            )

            if not user:
                raise ValueError

            current = float(
                user.get("balance", 0)
            )

            new_balance = (
                current + amount
            )

            updated = update_user(
                user_id,
                {
                    "balance":
                        new_balance
                },
            )

            if not updated:
                raise ValueError

            context.user_data.clear()

            await update.message.reply_text(

                "✅ Balance Added\n\n"

                f"👤 User: "
                f"{user_id}\n"

                f"➕ Added: "
                f"{amount:.2f} BDT\n"

                f"💵 New Balance: "
                f"{new_balance:.2f} BDT",

                reply_markup=admin_keyboard(),
            )

        except Exception:

            await update.message.reply_text(
                "❌ Wrong Format.\n\n"
                "USER_ID | AMOUNT",
                reply_markup=admin_cancel_keyboard(),
            )

        return True

    # REMOVE BALANCE
    if state == "remove_balance":

        try:

            user_id, amount = text.split(
                "|",
                1,
            )

            user_id = int(
                user_id.strip()
            )

            amount = float(
                amount.strip()
            )

            if amount <= 0:
                raise ValueError

            user = get_user_by_id(
                user_id
            )

            if not user:
                raise ValueError

            current = float(
                user.get("balance", 0)
            )

            new_balance = max(
                0,
                current - amount,
            )

            updated = update_user(
                user_id,
                {
                    "balance":
                        new_balance
                },
            )

            if not updated:
                raise ValueError

            context.user_data.clear()

            await update.message.reply_text(

                "✅ Balance Removed\n\n"

                f"👤 User: "
                f"{user_id}\n"

                f"➖ Removed: "
                f"{amount:.2f} BDT\n"

                f"💵 Balance: "
                f"{new_balance:.2f} BDT",

                reply_markup=admin_keyboard(),
            )

        except Exception:

            await update.message.reply_text(
                "❌ Wrong Format.\n\n"
                "USER_ID | AMOUNT",
                reply_markup=admin_cancel_keyboard(),
            )

        return True

    return False


# =========================================================
# WITHDRAW
# =========================================================

async def withdraw(update, context):

    user = get_user(
        update.effective_user
    )

    user_id = update.effective_user.id

    balance_value = float(
        user.get("balance", 0)
    )

    if balance_value <= 0:

        await update.message.reply_text(
            f"{t(user_id, 'withdraw_title')}\n\n"
            f"{t(user_id, 'zero_balance')}",
            reply_markup=main_keyboard(
                user_id
            ),
        )

        return

    context.user_data.clear()

    context.user_data[
        "withdraw_step"
    ] = "amount"

    await update.message.reply_text(

        f"{t(user_id, 'withdraw_title')}\n\n"

        f"{t(user_id, 'available_balance')}: "
        f"{balance_value:.2f} BDT\n\n"

        f"{t(user_id, 'send_amount')}",

        reply_markup=cancel_keyboard(
            user_id
        ),
    )


# =========================================================
# WITHDRAW FLOW
# =========================================================

async def process_withdraw(update, context):

    step = context.user_data.get(
        "withdraw_step"
    )

    if not step:
        return False

    if not update.message:
        return False

    user_id = update.effective_user.id

    text = update.message.text.strip()

    if step == "amount":

        try:

            amount = float(text)

            if amount <= 0:
                raise ValueError

        except Exception:

            await update.message.reply_text(
                t(
                    user_id,
                    "invalid_amount",
                ),
                reply_markup=cancel_keyboard(
                    user_id
                ),
            )

            return True

        user = get_user(
            update.effective_user
        )

        balance_value = float(
            user.get("balance", 0)
        )

        if amount > balance_value:

            await update.message.reply_text(

                f"{t(user_id, 'insufficient')}\n\n"

                f"{t(user_id, 'available_balance')}: "
                f"{balance_value:.2f} BDT",

                reply_markup=cancel_keyboard(
                    user_id
                ),
            )

            return True

        context.user_data[
            "withdraw_amount"
        ] = amount

        context.user_data[
            "withdraw_step"
        ] = "method"

        await update.message.reply_text(
            t(
                user_id,
                "send_method",
            ),
            reply_markup=cancel_keyboard(
                user_id
            ),
        )

        return True

    if step == "method":

        context.user_data[
            "withdraw_method"
        ] = text

        context.user_data[
            "withdraw_step"
        ] = "account"

        await update.message.reply_text(
            t(
                user_id,
                "send_account",
            ),
            reply_markup=cancel_keyboard(
                user_id
            ),
        )

        return True

    if step == "account":

        account_number = text

        amount = float(
            context.user_data[
                "withdraw_amount"
            ]
        )

        method = context.user_data[
            "withdraw_method"
        ]

        user = get_user(
            update.effective_user
        )

        balance_value = float(
            user.get("balance", 0)
        )

        if amount > balance_value:

            context.user_data.clear()

            await update.message.reply_text(
                t(
                    user_id,
                    "insufficient",
                ),
                reply_markup=main_keyboard(
                    user_id
                ),
            )

            return True

        new_balance = (
            balance_value - amount
        )

        data = {

            "user_id":
                user["id"],

            "method":
                method,

            "account_number":
                account_number,

            "amount":
                amount,

            "status":
                "pending",

            "created_at":
                datetime.now().isoformat(),
        }

        result = sb_post(
            "withdrawals",
            data,
        )

        if not result:

            await update.message.reply_text(
                t(
                    user_id,
                    "withdraw_created",
                ),
                reply_markup=cancel_keyboard(
                    user_id
                ),
            )

            return True

        updated = update_user(
            user["id"],
            {
                "balance":
                    new_balance
            },
        )

        if not updated:

            withdrawal_id = result[0]["id"]

            sb_delete(
                "withdrawals",
                {
                    "id":
                        f"eq.{withdrawal_id}"
                },
            )

            await update.message.reply_text(
                t(
                    user_id,
                    "balance_update_failed",
                ),
                reply_markup=cancel_keyboard(
                    user_id
                ),
            )

            return True

        withdrawal = result[0]

        context.user_data.clear()

        await update.message.reply_text(

            f"{t(user_id, 'withdraw_success')}\n\n"

            f"💰 Amount: "
            f"{amount:.2f} BDT\n"

            f"💳 Method: "
            f"{method}\n"

            f"🏦 Account: "
            f"{account_number}\n"

            f"🆔 Request ID: "
            f"{withdrawal['id']}",

            reply_markup=main_keyboard(
                user_id
            ),
        )

        try:

            await context.bot.send_message(

                chat_id=ADMIN_ID,

                text=(

                    "📤 NEW WITHDRAWAL\n\n"

                    f"🆔 Request: "
                    f"{withdrawal['id']}\n"

                    f"👤 User: "
                    f"{user['id']}\n"

                    f"💰 Amount: "
                    f"{amount:.2f} BDT\n"

                    f"💳 Method: "
                    f"{method}\n"

                    f"🏦 Account: "
                    f"{account_number}"
                ),

                reply_markup=
                InlineKeyboardMarkup([

                    [
                        InlineKeyboardButton(
                            "✅ Approve",
                            callback_data=
                            f"approve_withdraw_{withdrawal['id']}",
                        ),

                        InlineKeyboardButton(
                            "❌ Reject",
                            callback_data=
                            f"reject_withdraw_{withdrawal['id']}",
                        ),
                    ]

                ]),
            )

        except Exception:

            logger.exception(
                "Withdrawal admin notification error"
            )

        return True

    return False


# =========================================================
# WITHDRAW REVIEW
# =========================================================

async def review_withdrawal(update, context):

    query = update.callback_query

    await query.answer()

    if query.from_user.id != ADMIN_ID:

        await query.message.reply_text(
            "❌ Access denied."
        )

        return

    if query.data.startswith(
        "approve_withdraw_"
    ):

        withdrawal_id = query.data.replace(
            "approve_withdraw_",
            "",
        )

        action = "approved"

    else:

        withdrawal_id = query.data.replace(
            "reject_withdraw_",
            "",
        )

        action = "rejected"

    rows = sb_get(
        "withdrawals",
        {
            "id":
                f"eq.{withdrawal_id}",

            "limit":
                "1",
        },
    )

    if not rows:

        await query.message.reply_text(
            "❌ Withdrawal not found."
        )

        return

    withdrawal = rows[0]

    if withdrawal.get(
        "status"
    ) != "pending":

        await query.message.reply_text(
            "⚠️ Already reviewed."
        )

        return

    user_id = withdrawal["user_id"]

    amount = float(
        withdrawal.get(
            "amount",
            0,
        )
    )

    if action == "approved":

        updated = sb_patch(

            "withdrawals",

            {
                "id":
                    f"eq.{withdrawal_id}"
            },

            {
                "status":
                    "approved",

                "reviewed_at":
                    datetime.now().isoformat(),

                "reviewed_by":
                    ADMIN_ID,

                "approved_at":
                    datetime.now().isoformat(),
            },
        )

        if not updated:

            await query.message.reply_text(
                "❌ Could not approve withdrawal."
            )

            return

        await query.message.reply_text(

            "✅ WITHDRAWAL APPROVED\n\n"

            f"👤 User: "
            f"{user_id}\n"

            f"💰 Amount: "
            f"{amount:.2f} BDT"
        )

        try:

            language = get_language(
                user_id
            )

            if language == "bn":

                message = (

                    "✅ টাকা উত্তোলন Approved হয়েছে!\n\n"

                    f"💰 Amount: "
                    f"{amount:.2f} BDT\n"

                    f"💳 Method: "
                    f"{withdrawal.get('method', '')}\n"

                    f"🏦 Account: "
                    f"{withdrawal.get('account_number', '')}"
                )

            else:

                message = (

                    "✅ Withdrawal Approved!\n\n"

                    f"💰 Amount: "
                    f"{amount:.2f} BDT\n"

                    f"💳 Method: "
                    f"{withdrawal.get('method', '')}\n"

                    f"🏦 Account: "
                    f"{withdrawal.get('account_number', '')}"
                )

            await context.bot.send_message(
                chat_id=user_id,
                text=message,
            )

        except Exception:

            logger.exception(
                "Withdrawal approval notification error"
            )

    else:

        updated = sb_patch(

            "withdrawals",

            {
                "id":
                    f"eq.{withdrawal_id}"
            },

            {
                "status":
                    "rejected",

                "reviewed_at":
                    datetime.now().isoformat(),

                "reviewed_by":
                    ADMIN_ID,
            },
        )

        if not updated:

            await query.message.reply_text(
                "❌ Could not reject withdrawal."
            )

            return

        user = get_user_by_id(
            user_id
        )

        if user:

            old_balance = float(
                user.get("balance", 0)
            )

            update_user(
                user_id,
                {
                    "balance":
                        old_balance + amount
                },
            )

        await query.message.reply_text(

            "❌ WITHDRAWAL REJECTED\n\n"

            f"👤 User: "
            f"{user_id}\n"

            f"💰 Returned: "
            f"{amount:.2f} BDT"
        )

        try:

            language = get_language(
                user_id
            )

            if language == "bn":

                message = (

                    "❌ টাকা উত্তোলন Rejected হয়েছে।\n\n"

                    f"💰 {amount:.2f} BDT "
                    "আপনার ব্যালেন্সে ফেরত দেওয়া হয়েছে।"
                )

            else:

                message = (

                    "❌ Withdrawal Rejected\n\n"

                    f"💰 {amount:.2f} BDT "
                    "has been returned to your balance."
                )

            await context.bot.send_message(
                chat_id=user_id,
                text=message,
            )

        except Exception:

            logger.exception(
                "Withdrawal rejection notification error"
            )


# =========================================================
# TOP
# =========================================================

async def top_users(update, context):

    user_id = update.effective_user.id

    users = sb_get(
        "bot_users",
        {
            "select":
                "id,first_name,balance",

            "order":
                "balance.desc",

            "limit":
                "10",
        },
    )

    if not users:

        await update.message.reply_text(
            t(
                user_id,
                "no_users",
            ),
            reply_markup=main_keyboard(
                user_id
            ),
        )

        return

    text = (
        f"{t(user_id, 'top_title')}\n\n"
    )

    for i, user in enumerate(
        users,
        1,
    ):

        text += (

            f"{i}. "
            f"{user.get('first_name') or 'User'}\n"

            f"💰 "
            f"{float(user.get('balance', 0)):.2f} BDT\n\n"
        )

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard(
            user_id
        ),
    )


# =========================================================
# LANGUAGE
# =========================================================

async def language(update, context):

    user_id = update.effective_user.id

    await update.message.reply_text(

        f"{t(user_id, 'language_title')}\n\n"
        f"{t(user_id, 'select_language')}",

        reply_markup=
        InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "🇧🇩 বাংলা",
                    callback_data="lang_bn",
                ),

                InlineKeyboardButton(
                    "🇬🇧 English",
                    callback_data="lang_en",
                ),
            ]

        ]),
    )


async def language_callback(update, context):

    query = update.callback_query

    await query.answer()

    if query.data == "lang_bn":

        update_user(
            query.from_user.id,
            {
                "language":
                    "bn"
            },
        )

        await query.message.reply_text(

            TEXTS["bn"][
                "bangla_selected"
            ],

            reply_markup=main_keyboard(
                query.from_user.id
            ),
        )

    elif query.data == "lang_en":

        update_user(
            query.from_user.id,
            {
                "language":
                    "en"
            },
        )

        await query.message.reply_text(

            TEXTS["en"][
                "english_selected"
            ],

            reply_markup=main_keyboard(
                query.from_user.id
            ),
        )


# =========================================================
# TEXT HANDLER
# =========================================================

async def text_handler(update, context):

    if not update.effective_user:
        return

    user_id = update.effective_user.id

    # ADMIN FLOW
    if user_id == ADMIN_ID:

        if await process_admin_text(
            update,
            context,
        ):
            return

    # TASK FLOW
    if await process_task_text(
        update,
        context,
    ):
        return

    # WITHDRAW FLOW
    if await process_withdraw(
        update,
        context,
    ):
        return

    if not update.message:
        return

    text = update.message.text

    language = get_language(
        user_id
    )

    # -----------------------------
    # BANGLA
    # -----------------------------

    if text in (
        "💸 ব্যালেন্স",
        "💸 Balance",
    ):

        await balance(
            update,
            context,
        )

    elif text in (
        "💰 কাজ",
        "💰 Tasks",
    ):

        await show_tasks(
            update,
            context,
        )

    elif text in (
        "📤 টাকা উত্তোলন",
        "📤 Withdraw",
    ):

        await withdraw(
            update,
            context,
        )

    elif text in (
        "👤 প্রোফাইল",
        "👤 Profile",
    ):

        await profile(
            update,
            context,
        )

    elif text in (
        "🏆 সেরা ব্যবহারকারী",
        "🏆 Top",
    ):

        await top_users(
            update,
            context,
        )

    elif text in (
        "🫂 আমার রেফারেল",
        "🫂 My Referrals",
    ):

        await referrals(
            update,
            context,
        )

    elif text in (
        "🌏 ভাষা",
        "🌏 Language",
    ):

        await language(
            update,
            context,
        )

    elif text in (
        "👨‍💻 অ্যাডমিন প্যানেল",
        "👨‍💻 Admin Panel",
    ):

        if user_id == ADMIN_ID:

            context.user_data.clear()

            await update.message.reply_text(

                f"{t(user_id, 'admin_title')}\n\n"
                f"{t(user_id, 'admin_select')}",

                reply_markup=admin_keyboard(),
            )

        else:

            await update.message.reply_text(
                t(
                    user_id,
                    "access_denied",
                )
            )

    else:

        await update.message.reply_text(

            t(
                user_id,
                "unknown",
            ),

            reply_markup=main_keyboard(
                user_id
            ),
        )


# =========================================================
# ERROR
# =========================================================

async def error_handler(update, context):

    logger.error(
        "Telegram error: %r",
        context.error,
        exc_info=True,
    )


# =========================================================
# TELEGRAM MENU
# =========================================================

async def post_init(application):

    try:

        await application.bot.set_my_commands([

            BotCommand(
                "start",
                "Start the bot",
            ),

        ])

        logger.info(
            "Telegram Start menu configured."
        )

    except Exception:

        logger.exception(
            "Could not configure Telegram menu."
        )


# =========================================================
# MAIN
# =========================================================

def main():

    logger.info("=" * 60)

    logger.info(
        "Starting Success Income Zone Bot"
    )

    logger.info("=" * 60)

    if not BOT_TOKEN:

        logger.error(
            "BOT_TOKEN is missing!"
        )

        return

    if not SUPABASE_URL:

        logger.error(
            "SUPABASE_URL is missing!"
        )

        return

    if not SUPABASE_KEY:

        logger.error(
            "SUPABASE_KEY is missing!"
        )

        return

    logger.info(
        "Environment variables loaded successfully"
    )

    logger.info(
        "Admin ID: %s",
        ADMIN_ID,
    )

    # HEALTH SERVER
    health_thread = threading.Thread(
        target=run_health_server,
        daemon=True,
    )

    health_thread.start()

    # TELEGRAM
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # =====================================================
    # COMMANDS
    # =====================================================

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "admin",
            admin_command,
        )
    )

    # =====================================================
    # GLOBAL CANCEL
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            global_cancel,
            pattern=r"^global_cancel$",
        )
    )

    # =====================================================
    # ADMIN CANCEL
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^admin_cancel$",
        )
    )

    # =====================================================
    # TASK CALLBACKS
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            select_task,
            pattern=r"^select_task_",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            start_task,
            pattern=r"^start_task_",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            confirm_submission,
            pattern=r"^confirm_submission$",
        )
    )

    # =====================================================
    # ADMIN
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^admin_",
        )
    )

    # =====================================================
    # TASK APPROVE / REJECT
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            review_submission,
            pattern=r"^(approve_|reject_)",
        )
    )

    # =====================================================
    # WITHDRAW
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            review_withdrawal,
            pattern=r"^(approve_withdraw_|reject_withdraw_)",
        )
    )

    # =====================================================
    # LANGUAGE
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            language_callback,
            pattern=r"^lang_",
        )
    )

    # =====================================================
    # TEXT
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler,
        )
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "All handlers registered."
    )

    logger.info(
        "Starting Telegram polling..."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False,
    )


# =========================================================
# ENTRY
# =========================================================

if __name__ == "__main__":
    main()
