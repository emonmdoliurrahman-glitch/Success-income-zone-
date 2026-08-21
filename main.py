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
        logger.exception("Supabase GET exception")
        return []


def sb_post(table, data):
    try:
        headers = supabase_headers()
        headers["Prefer"] = "return=representation"

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
        logger.exception("Supabase POST exception")
        return None


def sb_patch(table, params, data):
    try:
        headers = supabase_headers()
        headers["Prefer"] = "return=representation"

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
        logger.exception("Supabase PATCH exception")
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
        logger.exception("Supabase DELETE exception")
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
        logger.exception("Health server crashed")


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
                "first_name": tg_user.first_name or "",
                "last_name": tg_user.last_name or "",
                "username": tg_user.username or "",
            },
        )

        if updated:
            return updated[0]

        return user

    # IMPORTANT:
    # এখানে role column নেই।
    data = {
        "id": user_id,
        "first_name": tg_user.first_name or "",
        "last_name": tg_user.last_name or "",
        "username": tg_user.username or "",
        "language": "bn",
        "balance": 0,
        "referral_earnings": 0,
        "referred_by": None,
        "joined_at": datetime.now().isoformat(),
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

    keyboard = [
        ["💸 Balance", "💰 Tasks"],
        ["📤 Withdraw", "👤 Profile"],
        ["🏆 Top", "🫂 My Referrals"],
        ["🌏 Language"],
    ]

    if user_id == ADMIN_ID:
        keyboard.append(
            ["👨‍💻 Admin Panel"]
        )

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )


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
        ],
    ])


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.effective_user:
        return

    tg_user = update.effective_user

    user = get_user(tg_user)

    # Referral
    if context.args:

        referral_id = context.args[0]

        if referral_id.isdigit():

            referral_id = int(referral_id)

            if referral_id != tg_user.id:

                if user.get("referred_by") is None:

                    referrer = get_user_by_id(
                        referral_id
                    )

                    if referrer:

                        update_user(
                            tg_user.id,
                            {
                                "referred_by": referral_id
                            },
                        )

    context.user_data.clear()

    await update.message.reply_text(
        "👋 Welcome to Success Income Zone!\n\n"
        "💰 Complete tasks and earn BDT.\n"
        "👥 Refer friends and earn 20% commission.\n\n"
        "👇 Select an option:",
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

    await update.message.reply_text(
        "💸 BALANCE\n\n"
        f"💰 Balance: "
        f"{float(user.get('balance', 0)):.2f} BDT\n\n"
        f"🎁 Referral Earnings: "
        f"{float(user.get('referral_earnings', 0)):.2f} BDT",
        reply_markup=main_keyboard(
            update.effective_user.id
        ),
    )


# =========================================================
# PROFILE
# =========================================================

async def profile(update, context):

    user = get_user(
        update.effective_user
    )

    username = (
        "@" + user.get("username", "")
        if user.get("username")
        else "No username"
    )

    referrals = sb_get(
        "bot_users",
        {
            "referred_by":
                f"eq.{user['id']}",
            "select":
                "id",
        },
    )

    await update.message.reply_text(
        "👤 PROFILE\n\n"
        f"🆔 ID: {user['id']}\n"
        f"👤 Username: {username}\n"
        f"💰 Balance: "
        f"{float(user.get('balance', 0)):.2f} BDT\n"
        f"👥 Referrals: "
        f"{len(referrals)}\n"
        f"🎁 Referral Earnings: "
        f"{float(user.get('referral_earnings', 0)):.2f} BDT\n"
        f"📅 Joined: "
        f"{user.get('joined_at', 'N/A')}",
        reply_markup=main_keyboard(
            update.effective_user.id
        ),
    )


# =========================================================
# REFERRALS
# =========================================================

async def referrals(update, context):

    user = get_user(
        update.effective_user
    )

    bot = await context.bot.get_me()

    rows = sb_get(
        "bot_users",
        {
            "referred_by":
                f"eq.{user['id']}",
            "select":
                "id",
        },
    )

    link = (
        f"https://t.me/{bot.username}"
        f"?start={user['id']}"
    )

    await update.message.reply_text(
        "🫂 MY REFERRALS\n\n"
        f"👥 Referrals: {len(rows)}\n"
        f"🎁 Earnings: "
        f"{float(user.get('referral_earnings', 0)):.2f} BDT\n\n"
        f"🔗 Your Referral Link:\n{link}",
        reply_markup=main_keyboard(
            update.effective_user.id
        ),
    )


# =========================================================
# SHOW TASKS
# =========================================================

async def show_tasks(update, context):

    tasks = get_tasks()

    if not tasks:

        await update.message.reply_text(
            "📋 Tasks\n\n"
            "❌ বর্তমানে কোনো Task নেই।"
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
        "📋 Tasks\n\n"
        "👇 Please select a task:",
        reply_markup=
        InlineKeyboardMarkup(keyboard),
    )


# =========================================================
# SELECT TASK
# =========================================================

async def select_task(update, context):

    query = update.callback_query

    await query.answer()

    task_id = query.data.replace(
        "select_task_",
        "",
    )

    task = get_task(task_id)

    if not task:

        await query.message.reply_text(
            "❌ Task not found."
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
        "Required"
        if uid_required in (
            "yes",
            "true",
            "required",
            "হ্যাঁ",
        )
        else
        "Not Required"
    )

    text = (
        f"📋 Task: {task.get('title', '')}\n\n"
        f"💰 Reward: {reward:.2f} BDT\n\n"
        f"⏳ Review time: "
        f"{review_hours} hours\n\n"
        f"📄 Description:\n"
        f"{description}\n\n"
        f"🆔 UID: {uid_text}\n\n"
        f"✍️ Report instruction:\n"
        f"{report_instruction}"
    )

    keyboard = [[
        InlineKeyboardButton(
            "🚀 Start",
            callback_data=
            f"start_task_{task['id']}",
        )
    ]]

    await query.message.reply_text(
        text,
        reply_markup=
        InlineKeyboardMarkup(keyboard),
    )


# =========================================================
# START TASK
# =========================================================

async def start_task(update, context):

    query = update.callback_query

    await query.answer()

    task_id = query.data.replace(
        "start_task_",
        "",
    )

    task = get_task(task_id)

    if not task:

        await query.message.reply_text(
            "❌ Task not found."
        )

        return

    context.user_data.clear()

    context.user_data["task_id"] = int(task_id)

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
            "🚀 Task Started!\n\n"
            "🆔 Send your required UID:"
        )

    else:

        context.user_data[
            "task_step"
        ] = "report"

        await query.message.reply_text(
            "🚀 Task Started!\n\n"
            "📋 Please send your required report:"
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

    text = update.message.text.strip()

    if step == "uid":

        if len(text) < 3:

            await update.message.reply_text(
                "❌ Please send a valid UID."
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
            "🆔 UID received.\n\n"
            "📋 Please send the required report:"
        )

        if report_instruction:
            message += (
                "\n\n"
                "✍️ Report instruction:\n"
                f"{report_instruction}"
            )

        await update.message.reply_text(
            message
        )

        return True

    if step == "report":

        if len(text) < 1:

            await update.message.reply_text(
                "❌ Report cannot be empty."
            )

            return True

        context.user_data[
            "task_report"
        ] = text

        context.user_data[
            "task_step"
        ] = "confirm"

        await update.message.reply_text(
            "📋 Report received.\n\n"
            "Please confirm your submission:",
            reply_markup=
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "✅ Submit",
                        callback_data=
                        "confirm_submission",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ Cancel",
                        callback_data=
                        "cancel_submission",
                    )
                ],
            ]),
        )

        return True

    return False


# =========================================================
# CONFIRM SUBMISSION
# =========================================================

async def confirm_submission(update, context):

    query = update.callback_query

    await query.answer()

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
            "❌ Submission incomplete."
        )

        return

    task = get_task(task_id)

    if not task:

        await query.message.reply_text(
            "❌ Task not found."
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
            "❌ UID is required."
        )

        return

    user = get_user(
        query.from_user
    )

    reward = float(
        task.get("reward", 0)
    )

    data = {
        "user_id": user["id"],
        "task_id": int(task["id"]),
        "facebook_uid": uid_value or "",
        "written_report": report,
        "reward": reward,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }

    result = sb_post(
        "submissions",
        data,
    )

    if not result:

        await query.message.reply_text(
            "❌ Could not submit task.\n\n"
            "Please check Render logs."
        )

        return

    submission = result[0]

    context.user_data.clear()

    await query.message.reply_text(
        "✅ Your report has been received!\n\n"
        "⏳ Task Pending Review",
        reply_markup=main_keyboard(
            query.from_user.id
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
                f"🆔 Submission: {submission['id']}\n"
                f"👤 User ID: {user['id']}\n"
                f"👤 Username: "
                f"@{user.get('username') or 'None'}\n\n"
                f"📋 Task: {task.get('title', '')}\n"
                f"💰 Reward: {reward:.2f} BDT\n\n"
                f"🆔 UID: {uid_display}\n\n"
                f"📄 Report:\n{report}"
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
# CANCEL
# =========================================================

async def cancel_submission(update, context):

    query = update.callback_query

    await query.answer()

    context.user_data.clear()

    await query.message.reply_text(
        "❌ Submission cancelled.",
        reply_markup=main_keyboard(
            query.from_user.id
        ),
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
            "id": f"eq.{submission_id}"
        },
        {
            "status": action,
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

        new_balance = old_balance + reward

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
            f"👤 User ID: {user_id}\n"
            f"💰 Reward Added: "
            f"{reward:.2f} BDT"
        )

        try:

            final_user = get_user_by_id(
                user_id
            )

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🎉 Task Approved!\n\n"
                    f"💰 Reward: "
                    f"{reward:.2f} BDT\n\n"
                    f"💵 Your Balance: "
                    f"{float(final_user.get('balance', 0)):.2f} BDT"
                ),
            )

        except Exception:
            logger.exception(
                "Approval notification error"
            )

    else:

        await query.message.reply_text(
            "❌ TASK REJECTED\n\n"
            f"👤 User ID: {user_id}"
        )

        try:

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ Task Rejected\n\n"
                    f"📋 Task ID: "
                    f"{submission.get('task_id')}\n\n"
                    "💰 No reward was added."
                ),
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
            "❌ আপনি Admin নন।"
        )

        return

    context.user_data.clear()

    await update.message.reply_text(
        "👨‍💻 ADMIN PANEL\n\n"
        "👇 Select an option:",
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
            "📌 Send Task Title:"
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
                f"🆔 ID: {task.get('id')}\n"
                f"📌 Title: {task.get('title', '')}\n"
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
            "Send Task ID to delete:"
        )

        return

    # PENDING
    if action == "admin_pending":

        pending = sb_get(
            "submissions",
            {
                "status": "eq.pending",
                "order": "id.asc",
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
            f"Total Users: {len(users)}\n\n"
        )

        for user in users[:50]:

            text += (
                f"🆔 {user.get('id')}\n"
                f"👤 {user.get('first_name') or 'User'}\n"
                f"@{user.get('username') or 'None'}\n"
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
            "7764329763 | 100"
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
            "USER_ID | AMOUNT"
        )

        return

    # WITHDRAWALS
    if action == "admin_withdrawals":

        pending = sb_get(
            "withdrawals",
            {
                "status": "eq.pending",
                "order": "id.asc",
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
            "25.50"
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
                "Example: 5.80"
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
            "12"
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
                "Example: 12"
            )

            return True

        context.user_data[
            "new_task_review"
        ] = review_hours

        context.user_data[
            "admin_state"
        ] = "task_description"

        await update.message.reply_text(
            "📄 Send Task Description:"
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
            "Send NO if UID is not required."
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
                "❌ Please send YES or NO."
            )

            return True

        uid_value = (
            "yes"
            if value in ("yes", "হ্যাঁ")
            else "no"
        )

        context.user_data[
            "new_task_uid"
        ] = uid_value

        context.user_data[
            "admin_state"
        ] = "task_report"

        await update.message.reply_text(
            "✍️ Send Report Instruction:"
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

        # =================================================
        # TASK DATA
        # =================================================

        data = {
            "title": title,
            "reward": float(reward),
            "review_hours": int(review_hours),
            "description": description,
            "uid": uid_value,
            "report_instruction": text,
            "is_active": True,
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

        # SAVE FAILED
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

        # SUCCESS
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
                "❌ Invalid Task ID."
            )

            return True

        task = get_task(task_id)

        if not task:

            await update.message.reply_text(
                "❌ Task ID not found."
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
                "❌ Task delete হয়নি।"
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

            new_balance = current + amount

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
                f"👤 User: {user_id}\n"
                f"➕ Added: "
                f"{amount:.2f} BDT\n"
                f"💵 New Balance: "
                f"{new_balance:.2f} BDT",
                reply_markup=admin_keyboard(),
            )

        except Exception:

            await update.message.reply_text(
                "❌ Wrong Format.\n\n"
                "USER_ID | AMOUNT"
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
                f"👤 User: {user_id}\n"
                f"➖ Removed: "
                f"{amount:.2f} BDT\n"
                f"💵 Balance: "
                f"{new_balance:.2f} BDT",
                reply_markup=admin_keyboard(),
            )

        except Exception:

            await update.message.reply_text(
                "❌ Wrong Format.\n\n"
                "USER_ID | AMOUNT"
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

    balance_value = float(
        user.get("balance", 0)
    )

    if balance_value <= 0:

        await update.message.reply_text(
            "📤 Withdraw\n\n"
            "❌ Your balance is 0.00 BDT."
        )

        return

    context.user_data.clear()

    context.user_data[
        "withdraw_step"
    ] = "amount"

    await update.message.reply_text(
        "📤 WITHDRAW\n\n"
        f"💰 Available Balance: "
        f"{balance_value:.2f} BDT\n\n"
        "Send withdrawal amount:"
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

    text = update.message.text.strip()

    if step == "amount":

        try:

            amount = float(text)

            if amount <= 0:
                raise ValueError

        except Exception:

            await update.message.reply_text(
                "❌ Invalid amount."
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
                f"❌ Insufficient balance.\n\n"
                f"Available: "
                f"{balance_value:.2f} BDT"
            )

            return True

        context.user_data[
            "withdraw_amount"
        ] = amount

        context.user_data[
            "withdraw_step"
        ] = "method"

        await update.message.reply_text(
            "💳 Send withdrawal method:\n\n"
            "Example:\n"
            "bKash\n"
            "Nagad\n"
            "Rocket"
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
            "🏦 Send your account number:"
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
                "❌ Insufficient balance."
            )

            return True

        new_balance = balance_value - amount

        data = {
            "user_id": user["id"],
            "method": method,
            "account_number": account_number,
            "amount": amount,
            "status": "pending",
            "created_at":
                datetime.now().isoformat(),
        }

        result = sb_post(
            "withdrawals",
            data,
        )

        if not result:

            await update.message.reply_text(
                "❌ Withdrawal request তৈরি হয়নি।"
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
                "❌ Balance update failed."
            )

            return True

        withdrawal = result[0]

        context.user_data.clear()

        await update.message.reply_text(
            "✅ Withdrawal Request Submitted!\n\n"
            f"💰 Amount: "
            f"{amount:.2f} BDT\n"
            f"💳 Method: {method}\n"
            f"🏦 Account: {account_number}\n"
            f"🆔 Request ID: "
            f"{withdrawal['id']}\n\n"
            "⏳ Please wait for Admin review."
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
                    f"💳 Method: {method}\n"
                    f"🏦 Account: {account_number}"
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

    if withdrawal.get("status") != "pending":

        await query.message.reply_text(
            "⚠️ Already reviewed."
        )

        return

    user_id = withdrawal["user_id"]

    amount = float(
        withdrawal.get("amount", 0)
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
            f"👤 User: {user_id}\n"
            f"💰 Amount: {amount:.2f} BDT"
        )

        try:

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "✅ Withdrawal Approved!\n\n"
                    f"💰 Amount: "
                    f"{amount:.2f} BDT\n"
                    f"💳 Method: "
                    f"{withdrawal.get('method', '')}\n"
                    f"🏦 Account: "
                    f"{withdrawal.get('account_number', '')}"
                ),
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
            f"👤 User: {user_id}\n"
            f"💰 Returned: {amount:.2f} BDT"
        )

        try:

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ Withdrawal Rejected\n\n"
                    f"💰 {amount:.2f} BDT "
                    "has been returned to your balance."
                ),
            )

        except Exception:
            logger.exception(
                "Withdrawal rejection notification error"
            )


# =========================================================
# TOP
# =========================================================

async def top_users(update, context):

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
            "🏆 No users yet."
        )

        return

    text = "🏆 TOP USERS\n\n"

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
        text
    )


# =========================================================
# LANGUAGE
# =========================================================

async def language(update, context):

    await update.message.reply_text(
        "🌏 LANGUAGE\n\n"
        "Select language:",
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
            "🇧🇩 বাংলা ভাষা নির্বাচন করা হয়েছে।",
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
            "🇬🇧 English language selected.",
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

    # ADMIN FLOW
    if update.effective_user.id == ADMIN_ID:

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

    if text == "💸 Balance":

        await balance(update, context)

    elif text == "💰 Tasks":

        await show_tasks(update, context)

    elif text == "📤 Withdraw":

        await withdraw(update, context)

    elif text == "👤 Profile":

        await profile(update, context)

    elif text == "🏆 Top":

        await top_users(update, context)

    elif text == "🫂 My Referrals":

        await referrals(update, context)

    elif text == "🌏 Language":

        await language(update, context)

    elif text == "👨‍💻 Admin Panel":

        if update.effective_user.id == ADMIN_ID:

            context.user_data.clear()

            await update.message.reply_text(
                "👨‍💻 ADMIN PANEL\n\n"
                "👇 Select an option:",
                reply_markup=admin_keyboard(),
            )

        else:

            await update.message.reply_text(
                "❌ Access denied."
            )

    else:

        await update.message.reply_text(
            "❓ Please select an option.",
            reply_markup=main_keyboard(
                update.effective_user.id
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
        .build()
    )

    # COMMANDS
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

    # TASK CALLBACKS
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

    application.add_handler(
        CallbackQueryHandler(
            cancel_submission,
            pattern=r"^cancel_submission$",
        )
    )

    # ADMIN
    application.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^admin_",
        )
    )

    # TASK APPROVE / REJECT
    application.add_handler(
        CallbackQueryHandler(
            review_submission,
            pattern=r"^(approve_|reject_)",
        )
    )

    # WITHDRAW
    application.add_handler(
        CallbackQueryHandler(
            review_withdrawal,
            pattern=r"^(approve_withdraw_|reject_withdraw_)",
        )
    )

    # LANGUAGE
    application.add_handler(
        CallbackQueryHandler(
            language_callback,
            pattern=r"^lang_",
        )
    )

    # TEXT
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
