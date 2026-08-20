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

ADMIN_ID = 7764329763

REFERRAL_PERCENT = 0.20

PORT = int(os.getenv("PORT", "10000"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
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
    url = f"{SUPABASE_URL}/rest/v1/{table}"

    response = requests.get(
        url,
        headers=supabase_headers(),
        params=params or {},
        timeout=20,
    )

    if not response.ok:
        logger.error(
            "Supabase GET error %s: %s",
            response.status_code,
            response.text,
        )
        return []

    return response.json()


def sb_post(table, data, return_representation=False):
    url = f"{SUPABASE_URL}/rest/v1/{table}"

    headers = supabase_headers()

    if return_representation:
        headers["Prefer"] = "return=representation"

    response = requests.post(
        url,
        headers=headers,
        json=data,
        timeout=20,
    )

    if not response.ok:
        logger.error(
            "Supabase POST error %s: %s",
            response.status_code,
            response.text,
        )
        return None

    if not response.text:
        return []

    return response.json()


def sb_patch(table, params, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}"

    headers = supabase_headers()
    headers["Prefer"] = "return=representation"

    response = requests.patch(
        url,
        headers=headers,
        params=params,
        json=data,
        timeout=20,
    )

    if not response.ok:
        logger.error(
            "Supabase PATCH error %s: %s",
            response.status_code,
            response.text,
        )
        return None

    if not response.text:
        return []

    return response.json()


def sb_delete(table, params):
    url = f"{SUPABASE_URL}/rest/v1/{table}"

    response = requests.delete(
        url,
        headers=supabase_headers(),
        params=params,
        timeout=20,
    )

    if not response.ok:
        logger.error(
            "Supabase DELETE error %s: %s",
            response.status_code,
            response.text,
        )
        return False

    return True


# =========================================================
# RENDER HEALTH SERVER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.end_headers()

        self.wfile.write(
            b"Success Income Zone Bot is running!"
        )

    def log_message(self, format, *args):
        return


def run_health_server():

    try:
        server = HTTPServer(
            ("0.0.0.0", PORT),
            HealthHandler
        )

        logger.info(
            f"Health server running on port {PORT}"
        )

        server.serve_forever()

    except Exception as e:
        logger.error(
            f"Health server error: {e}"
        )


# =========================================================
# DATABASE HELPERS
# =========================================================

def get_user(tg_user):

    uid = tg_user.id

    rows = sb_get(
        "bot_users",
        {
            "id": f"eq.{uid}",
            "limit": "1",
        }
    )

    if rows:
        user = rows[0]

        # Update profile information
        updated = {
            "first_name": tg_user.first_name or "",
            "last_name": tg_user.last_name or "",
            "username": tg_user.username or "",
        }

        result = sb_patch(
            "bot_users",
            {"id": f"eq.{uid}"},
            updated
        )

        if result:
            user = result[0]

        return user

    data = {
        "id": uid,
        "first_name": tg_user.first_name or "",
        "last_name": tg_user.last_name or "",
        "username": tg_user.username or "",
        "role": "user",
        "language": "bn",
        "balance": 0,
        "referral_earnings": 0,
        "referred_by": None,
        "joined_at": datetime.now().isoformat(),
    }

    result = sb_post(
        "bot_users",
        data,
        return_representation=True
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
        }
    )

    return rows[0] if rows else None


def update_user(user_id, data):

    return sb_patch(
        "bot_users",
        {"id": f"eq.{user_id}"},
        data
    )


def get_tasks():

    return sb_get(
        "tasks",
        {
            "order": "id.asc",
        }
    )


def get_task(task_id):

    rows = sb_get(
        "tasks",
        {
            "id": f"eq.{task_id}",
            "limit": "1",
        }
    )

    return rows[0] if rows else None


def get_submission(submission_id):

    rows = sb_get(
        "submissions",
        {
            "id": f"eq.{submission_id}",
            "limit": "1",
        }
    )

    return rows[0] if rows else None


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard():

    keyboard = [
        ["💸 Balance", "💰 Tasks"],
        ["📤 Withdraw", "👤 Profile"],
        ["🏆 Top", "🫂 My Referrals"],
        ["🌏 Language"],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )


def admin_keyboard():

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ Add Task",
                callback_data="admin_add_task"
            ),
            InlineKeyboardButton(
                "📋 All Tasks",
                callback_data="admin_all_tasks"
            ),
        ],
        [
            InlineKeyboardButton(
                "🗑 Delete Task",
                callback_data="admin_delete_task"
            ),
            InlineKeyboardButton(
                "👥 Users",
                callback_data="admin_users"
            ),
        ],
        [
            InlineKeyboardButton(
                "📥 Pending Tasks",
                callback_data="admin_pending"
            ),
        ],
        [
            InlineKeyboardButton(
                "💰 Add Balance",
                callback_data="admin_add_balance"
            ),
            InlineKeyboardButton(
                "➖ Remove Balance",
                callback_data="admin_remove_balance"
            ),
        ],
        [
            InlineKeyboardButton(
                "📤 Withdrawals",
                callback_data="admin_withdrawals"
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# START
# =========================================================

async def start(update, context):

    tg_user = update.effective_user
    user = get_user(tg_user)

    # Referral
    if context.args:

        referral_id = context.args[0]

        if referral_id.isdigit():

            referral_id = int(referral_id)

            if referral_id != tg_user.id:

                current_referrer = user.get(
                    "referred_by"
                )

                if current_referrer is None:

                    referrer = get_user_by_id(
                        referral_id
                    )

                    if referrer:

                        update_user(
                            tg_user.id,
                            {
                                "referred_by":
                                    referral_id
                            }
                        )

    await update.message.reply_text(
        "👋 Welcome to Success Income Zone!\n\n"
        "💰 Complete tasks and earn BDT.\n"
        "👥 Refer friends and earn 20% commission.\n\n"
        "👇 Select an option:",
        reply_markup=main_keyboard()
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
        f"{float(user.get('referral_earnings', 0)):.2f} BDT"
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

    # Count referrals
    referral_rows = sb_get(
        "bot_users",
        {
            "referred_by":
                f"eq.{user['id']}",
            "select": "id",
        }
    )

    referral_count = len(
        referral_rows
    )

    await update.message.reply_text(

        "👤 PROFILE\n\n"

        f"🆔 ID: {user['id']}\n"
        f"👤 Username: {username}\n"

        f"💰 Balance: "
        f"{float(user.get('balance', 0)):.2f} BDT\n"

        f"👥 Referrals: "
        f"{referral_count}\n"

        f"🎁 Referral Earnings: "
        f"{float(user.get('referral_earnings', 0)):.2f} BDT\n"

        f"📅 Joined: "
        f"{user.get('joined_at', 'N/A')}"
    )


# =========================================================
# REFERRALS
# =========================================================

async def referrals(update, context):

    user = get_user(
        update.effective_user
    )

    bot = await context.bot.get_me()

    referral_rows = sb_get(
        "bot_users",
        {
            "referred_by":
                f"eq.{user['id']}",
            "select": "id",
        }
    )

    link = (
        f"https://t.me/{bot.username}"
        f"?start={user['id']}"
    )

    await update.message.reply_text(

        "🫂 MY REFERRALS\n\n"

        f"👥 Referrals: "
        f"{len(referral_rows)}\n"

        f"🎁 Earnings: "
        f"{float(user.get('referral_earnings', 0)):.2f} BDT\n\n"

        f"🔗 Your Referral Link:\n"
        f"{link}"
    )


# =========================================================
# TASK LIST
# =========================================================

async def show_tasks(update, context):

    user = get_user(
        update.effective_user
    )

    tasks = get_tasks()

    if not tasks:

        await update.message.reply_text(
            "📋 Tasks\n\n"
            "❌ বর্তমানে কোনো Task নেই।"
        )

        return

    keyboard = []

    for task in tasks:

        task_id = str(task["id"])

        # Check already approved submission
        completed = sb_get(
            "submissions",
            {
                "user_id":
                    f"eq.{user['id']}",
                "task_id":
                    f"eq.{task['id']}",
                "status":
                    "eq.approved",
                "select": "id",
                "limit": "1",
            }
        )

        if completed:
            continue

        reward = float(
            task.get("reward", 0)
        )

        keyboard.append([

            InlineKeyboardButton(
                f"{task['title']} ({reward:.2f} BDT)",
                callback_data=
                f"select_task_{task_id}"
            )

        ])

    if not keyboard:

        await update.message.reply_text(
            "📋 Tasks\n\n"
            "❌ আপনি সব available Task complete করেছেন।"
        )

        return

    await update.message.reply_text(
        "📋 Tasks\n\n"
        "👇 Please select a task:",
        reply_markup=
        InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# SELECT TASK
# =========================================================

async def select_task(update, context):

    query = update.callback_query
    await query.answer()

    task_id = query.data.replace(
        "select_task_",
        ""
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

    review_hours = task.get(
        "review_hours",
        0
    )

    text = (

        f"📋 Task: {task['title']}\n\n"

        f"💰 Reward: "
        f"{reward:.2f} BDT\n\n"

        f"⏳ Review time: "
        f"{review_hours} hours\n\n"

        "📄 Please complete the task and "
        "then submit your Facebook UID and report."
    )

    keyboard = [[

        InlineKeyboardButton(
            "▶️ Start",
            callback_data=
            f"start_task_{task_id}"
        )

    ]]

    await query.message.reply_text(
        text,
        reply_markup=
        InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# START TASK
# =========================================================

async def start_task(update, context):

    query = update.callback_query
    await query.answer()

    user = get_user(
        query.from_user
    )

    task_id = query.data.replace(
        "start_task_",
        ""
    )

    task = get_task(task_id)

    if not task:

        await query.message.reply_text(
            "❌ Task not found."
        )

        return

    # Pending submission check
    pending = sb_get(
        "submissions",
        {
            "user_id":
                f"eq.{user['id']}",
            "task_id":
                f"eq.{task['id']}",
            "status":
                "eq.pending",
            "select": "id",
            "limit": "1",
        }
    )

    if pending:

        await query.message.reply_text(
            "⏳ You already submitted this task.\n"
            "Please wait for review."
        )

        return

    context.user_data[
        "task_id"
    ] = task_id

    context.user_data[
        "task_step"
    ] = "uid"

    await query.message.reply_text(
        "🚀 Task Started!\n\n"
        "Send your Facebook UID:"
    )


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

    if not task_id:

        await query.message.reply_text(
            "❌ Task session expired."
        )

        return

    task = get_task(task_id)

    if not task:

        await query.message.reply_text(
            "❌ Task not found."
        )

        return

    if not uid_value or not report:

        await query.message.reply_text(
            "❌ Submission incomplete."
        )

        return

    user = get_user(
        query.from_user
    )

    # Check duplicate Facebook UID
    existing_uid = sb_get(
        "submissions",
        {
            "facebook_uid":
                f"eq.{uid_value}",
            "select":
                "id,status",
            "limit":
                "1",
        }
    )

    if existing_uid:

        await query.message.reply_text(
            "❌ This Facebook UID has already been submitted."
        )

        return

    data = {

        "user_id":
            user["id"],

        "task_id":
            int(task["id"]),

        "facebook_uid":
            uid_value,

        "written_report":
            report,

        "reward":
            float(task["reward"]),

        "status":
            "pending",

        "created_at":
            datetime.now().isoformat(),
    }

    result = sb_post(
        "submissions",
        data,
        return_representation=True
    )

    if not result:

        await query.message.reply_text(
            "❌ Could not submit task. Please try again."
        )

        return

    submission = result[0]

    context.user_data.clear()

    await query.message.reply_text(

        "✅ Your report has been received!\n\n"
        "⏳ Task Pending Review"
    )

    # Notify Admin
    try:

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
                f"{task['title']}\n"

                f"💰 Reward: "
                f"{float(task['reward']):.2f} BDT\n\n"

                f"🆔 Facebook UID: "
                f"{uid_value}\n\n"

                f"📄 Report:\n"
                f"{report}"
            ),

            reply_markup=
            InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(
                        "✅ Approve",
                        callback_data=
                        f"approve_{submission['id']}"
                    ),

                    InlineKeyboardButton(
                        "❌ Reject",
                        callback_data=
                        f"reject_{submission['id']}"
                    )

                ]
            ])
        )

    except Exception as e:

        logger.error(
            f"Admin notification error: {e}"
        )


# =========================================================
# APPROVE / REJECT
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
            ""
        )

        action = "approved"

    else:

        submission_id = query.data.replace(
            "reject_",
            ""
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

    if submission["status"] != "pending":

        await query.message.reply_text(
            "⚠️ Already reviewed."
        )

        return

    user_id = submission["user_id"]

    reward = float(
        submission.get("reward", 0)
    )

    # Update submission
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
        }
    )

    if not updated:

        await query.message.reply_text(
            "❌ Could not update submission."
        )

        return

    # =====================================================
    # APPROVED
    # =====================================================

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

        update_user(
            user_id,
            {
                "balance":
                    new_balance
            }
        )

        # Referral commission
        referrer_id = user.get(
            "referred_by"
        )

        commission = 0

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
                        0
                    )
                )

                ref_earnings = float(
                    referrer.get(
                        "referral_earnings",
                        0
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
                    }
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

            await context.bot.send_message(

                chat_id=user_id,

                text=(

                    "🎉 Task Approved!\n\n"

                    f"📋 Task: "
                    f"{submission.get('task_id')}\n"

                    f"💰 Reward: "
                    f"{reward:.2f} BDT\n\n"

                    f"💵 Your Balance: "
                    f"{float(final_user.get('balance', 0)):.2f} BDT"
                )
            )

        except Exception as e:

            logger.error(e)

    # =====================================================
    # REJECTED
    # =====================================================

    else:

        await query.message.reply_text(

            "❌ TASK REJECTED\n\n"

            f"👤 User ID: "
            f"{user_id}"
        )

        try:

            await context.bot.send_message(

                chat_id=user_id,

                text=(

                    "❌ Task Rejected\n\n"

                    f"📋 Task ID: "
                    f"{submission.get('task_id')}\n\n"

                    "💰 No reward was added."
                )
            )

        except Exception as e:

            logger.error(e)


# =========================================================
# ADMIN COMMAND
# =========================================================

async def admin_command(update, context):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "❌ আপনি Admin নন।"
        )

        return

    await update.message.reply_text(

        "👨‍💻 ADMIN PANEL\n\n"
        "👇 Select an option:",

        reply_markup=admin_keyboard()
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

    # ADD TASK
    if action == "admin_add_task":

        context.user_data[
            "admin_state"
        ] = "task_name"

        await query.message.reply_text(
            "➕ ADD TASK\n\n"
            "📌 Send Task Name:"
        )

        return

    # ALL TASKS
    if action == "admin_all_tasks":

        task_list = get_tasks()

        if not task_list:

            await query.message.reply_text(
                "📋 No tasks available."
            )

            return

        text = "📋 ALL TASKS\n\n"

        for task in task_list:

            text += (

                f"🆔 Task ID: {task['id']}\n"
                f"📌 {task['title']}\n"
                f"💰 {float(task['reward']):.2f} BDT\n"
                f"⏳ Review: {task.get('review_hours', 0)} hours\n\n"
            )

        await query.message.reply_text(
            text
        )

        return

    # DELETE TASK
    if action == "admin_delete_task":

        task_list = get_tasks()

        if not task_list:

            await query.message.reply_text(
                "❌ No tasks."
            )

            return

        text = "🗑 DELETE TASK\n\n"

        for task in task_list:

            text += (
                f"🆔 {task['id']}\n"
                f"📌 {task['title']}\n\n"
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
                "status":
                    "eq.pending",
                "order":
                    "id.asc",
            }
        )

        if not pending:

            await query.message.reply_text(
                "📥 No pending submissions."
            )

            return

        for s in pending:

            keyboard = [[

                InlineKeyboardButton(
                    "✅ Approve",
                    callback_data=
                    f"approve_{s['id']}"
                ),

                InlineKeyboardButton(
                    "❌ Reject",
                    callback_data=
                    f"reject_{s['id']}"
                )

            ]]

            await query.message.reply_text(

                "📥 PENDING SUBMISSION\n\n"

                f"🆔 Submission: {s['id']}\n"
                f"👤 User: {s['user_id']}\n"
                f"📋 Task ID: {s['task_id']}\n"
                f"💰 Reward: "
                f"{float(s['reward']):.2f} BDT\n"
                f"🆔 UID: {s['facebook_uid']}\n\n"
                f"📄 Report:\n"
                f"{s['written_report']}",

                reply_markup=
                InlineKeyboardMarkup(keyboard)
            )

        return

    # USERS
    if action == "admin_users":

        user_list = sb_get(
            "bot_users",
            {
                "select":
                    "id",
            }
        )

        await query.message.reply_text(

            "👥 USERS\n\n"

            f"Total Users: "
            f"{len(user_list)}"
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
                "status":
                    "eq.pending",
                "order":
                    "id.asc",
            }
        )

        if not pending:

            await query.message.reply_text(
                "📤 No pending withdrawals."
            )

            return

        text = "📤 PENDING WITHDRAWALS\n\n"

        for w in pending:

            text += (

                f"🆔 {w['id']}\n"
                f"👤 User: {w['user_id']}\n"
                f"💰 Amount: {float(w['amount']):.2f} BDT\n"
                f"💳 Method: {w.get('method', 'Pending')}\n\n"
            )

        await query.message.reply_text(
            text
        )


# =========================================================
# ADMIN TEXT PROCESSING
# =========================================================

async def process_admin_text(update, context):

    if update.effective_user.id != ADMIN_ID:
        return False

    state = context.user_data.get(
        "admin_state"
    )

    if not state:
        return False

    text = update.message.text.strip()

    # TASK NAME
    if state == "task_name":

        context.user_data[
            "new_task_name"
        ] = text

        context.user_data[
            "admin_state"
        ] = "task_reward"

        await update.message.reply_text(
            "💵 Send Reward in BDT:\n\n"
            "Example: 10"
        )

        return True

    # TASK REWARD
    if state == "task_reward":

        try:

            reward = float(text)

            if reward <= 0:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                "❌ Invalid amount.\n\n"
                "Example: 10 or 25.50"
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
            "Example: 12"
        )

        return True

    # REVIEW HOURS
    if state == "task_review":

        try:

            review_hours = float(text)

            if review_hours < 0:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                "❌ Invalid review hours.\n\n"
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
        ] = "task_report"

        await update.message.reply_text(
            "✍️ Send Report Instruction:"
        )

        return True

    # REPORT
    if state == "task_report":

        # আপনার tasks table-এ description/report_instruction
        # column নেই, তাই শুধু প্রয়োজনীয় 4টি column insert করছি।

        data = {
            "title":
                context.user_data[
                    "new_task_name"
                ],

            "reward":
                context.user_data[
                    "new_task_reward"
                ],

            "review_hours":
                context.user_data[
                    "new_task_review"
                ],
        }

        result = sb_post(
            "tasks",
            data,
            return_representation=True
        )

        if not result:

            await update.message.reply_text(
                "❌ Task save হয়নি।\n"
                "Supabase logs দেখুন।"
            )

            return True

        task = result[0]

        context.user_data.clear()

        await update.message.reply_text(

            "✅ TASK ADDED SUCCESSFULLY!\n\n"

            f"🆔 Task ID: {task['id']}\n"
            f"📌 Task: {task['title']}\n"
            f"💰 Reward: "
            f"{float(task['reward']):.2f} BDT\n"
            f"⏳ Review: "
            f"{task['review_hours']} hours"
        )

        return True

    # DELETE TASK
    if state == "delete_task":

        try:
            task_id = int(text)
        except ValueError:

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

        # Delete task
        success = sb_delete(
            "tasks",
            {
                "id":
                    f"eq.{task_id}"
            }
        )

        if not success:

            await update.message.reply_text(
                "❌ Task delete হয়নি।"
            )

            return True

        context.user_data.clear()

        await update.message.reply_text(

            "✅ Task Deleted\n\n"

            f"📌 {task['title']}"
        )

        return True

    # ADD BALANCE
    if state == "add_balance":

        try:

            user_id, amount = text.split(
                "|",
                1
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

            update_user(
                user_id,
                {
                    "balance":
                        new_balance
                }
            )

            context.user_data.clear()

            await update.message.reply_text(

                "✅ Balance Added\n\n"

                f"👤 User: {user_id}\n"

                f"➕ Added: "
                f"{amount:.2f} BDT\n"

                f"💵 New Balance: "
                f"{new_balance:.2f} BDT"
            )

        except Exception:

            await update.message.reply_text(

                "❌ Wrong Format.\n\n"

                "Correct:\n"
                "USER_ID | AMOUNT"
            )

        return True

    # REMOVE BALANCE
    if state == "remove_balance":

        try:

            user_id, amount = text.split(
                "|",
                1
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
                current - amount
            )

            update_user(
                user_id,
                {
                    "balance":
                        new_balance
                }
            )

            context.user_data.clear()

            await update.message.reply_text(

                "✅ Balance Removed\n\n"

                f"👤 User: {user_id}\n"

                f"➖ Removed: "
                f"{amount:.2f} BDT\n"

                f"💵 Balance: "
                f"{new_balance:.2f} BDT"
            )

        except Exception:

            await update.message.reply_text(
                "❌ Wrong Format.\n\n"
                "Correct:\n"
                "USER_ID | AMOUNT"
            )

        return True

    return False


# =========================================================
# TASK USER TEXT FLOW
# =========================================================

async def process_task_text(update, context):

    step = context.user_data.get(
        "task_step"
    )

    if not step:
        return False

    text = update.message.text.strip()

    # UID
    if step == "uid":

        if len(text) < 3:

            await update.message.reply_text(
                "❌ Please send a valid Facebook UID."
            )

            return True

        context.user_data[
            "task_uid"
        ] = text

        context.user_data[
            "task_step"
        ] = "report"

        await update.message.reply_text(
            "👤 UID received.\n\n"
            "📋 Please send your task report:"
        )

        return True

    # REPORT
    if step == "report":

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
                        "confirm_submission"
                    )

                ]

            ])
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

    context.user_data[
        "withdraw"
    ] = True

    await update.message.reply_text(

        "📤 WITHDRAW\n\n"

        f"💰 Available Balance: "
        f"{balance_value:.2f} BDT\n\n"

        "Send withdrawal amount:"
    )


# =========================================================
# WITHDRAW PROCESS
# =========================================================

async def process_withdraw(update, context):

    if not context.user_data.get(
        "withdraw"
    ):

        return False

    user = get_user(
        update.effective_user
    )

    try:

        amount = float(
            update.message.text.strip()
        )

    except ValueError:

        await update.message.reply_text(
            "❌ Invalid amount."
        )

        return True

    balance_value = float(
        user.get("balance", 0)
    )

    if amount <= 0:

        await update.message.reply_text(
            "❌ Invalid amount."
        )

        return True

    if amount > balance_value:

        await update.message.reply_text(
            f"❌ Insufficient balance.\n\n"
            f"Available: "
            f"{balance_value:.2f} BDT"
        )

        return True

    # Deduct balance when withdrawal is requested
    new_balance = (
        balance_value - amount
    )

    update_user(
        user["id"],
        {
            "balance":
                new_balance
        }
    )

    data = {

        "user_id":
            user["id"],

        "amount":
            amount,

        "method":
            "Pending",

        "status":
            "pending",

        "created_at":
            datetime.now().isoformat(),
    }

    result = sb_post(
        "withdrawals",
        data,
        return_representation=True
    )

    if not result:

        # Restore balance if withdrawal failed
        update_user(
            user["id"],
            {
                "balance":
                    balance_value
            }
        )

        await update.message.reply_text(
            "❌ Withdrawal request তৈরি হয়নি।"
        )

        return True

    withdrawal = result[0]

    context.user_data.clear()

    await update.message.reply_text(

        "✅ Withdrawal Request Submitted!\n\n"

        f"💰 Amount: "
        f"{amount:.2f} BDT\n"

        f"🆔 Request ID: "
        f"{withdrawal['id']}\n\n"

        "⏳ Please wait for Admin review."
    )

    # Notify admin
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

                f"💳 Method: Pending"
            )
        )

    except Exception as e:

        logger.error(e)

    return True


# =========================================================
# TOP USERS
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
        }
    )

    if not users:

        await update.message.reply_text(
            "🏆 No users yet."
        )

        return

    text = "🏆 TOP USERS\n\n"

    for i, user in enumerate(
        users,
        1
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
        "🇧🇩 বাংলা\n"
        "🇬🇧 English"
    )


# =========================================================
# TEXT HANDLER
# =========================================================

async def text_handler(update, context):

    # Admin processing
    if update.effective_user.id == ADMIN_ID:

        if await process_admin_text(
            update,
            context
        ):

            return

    # Task processing
    if await process_task_text(
        update,
        context
    ):

        return

    # Withdraw processing
    if await process_withdraw(
        update,
        context
    ):

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

    else:

        await update.message.reply_text(
            "❓ Please select an option.",
            reply_markup=main_keyboard()
        )


# =========================================================
# ERROR
# =========================================================

async def error_handler(update, context):

    logger.error(
        "Telegram error:",
        exc_info=context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:

        logger.error(
            "❌ BOT_TOKEN is missing!"
        )

        return

    if not SUPABASE_URL:

        logger.error(
            "❌ SUPABASE_URL is missing!"
        )

        return

    if not SUPABASE_KEY:

        logger.error(
            "❌ SUPABASE_KEY is missing!"
        )

        return

    threading.Thread(
        target=run_health_server,
        daemon=True
    ).start()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Commands
    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "admin",
            admin_command
        )
    )

    # Task
    application.add_handler(
        CallbackQueryHandler(
            select_task,
            pattern=r"^select_task_"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            start_task,
            pattern=r"^start_task_"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            confirm_submission,
            pattern=r"^confirm_submission$"
        )
    )

    # Admin
    application.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^admin_"
        )
    )

    # Approve / Reject
    application.add_handler(
        CallbackQueryHandler(
            review_submission,
            pattern=r"^(approve_|reject_)"
        )
    )

    # Text
    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_handler
        )
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Success Income Zone Bot is running..."
    )

    logger.info(
        f"Admin ID: {ADMIN_ID}"
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
