import os
import json
import logging
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

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

ADMIN_ID = 7764329763

REFERRAL_PERCENT = 0.20

USERS_FILE = "users.json"
TASKS_FILE = "tasks.json"
SUBMISSIONS_FILE = "submissions.json"
WITHDRAWALS_FILE = "withdrawals.json"

PORT = int(os.getenv("PORT", "10000"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


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
# JSON DATABASE
# =========================================================

def load_json(filename, default):

    if not os.path.exists(filename):
        return default

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        logger.error(
            f"Could not load {filename}: {e}"
        )

        return default


def save_json(filename, data):

    try:

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

    except Exception as e:

        logger.error(
            f"Could not save {filename}: {e}"
        )


users = load_json(
    USERS_FILE,
    {}
)

tasks = load_json(
    TASKS_FILE,
    {}
)

submissions = load_json(
    SUBMISSIONS_FILE,
    {}
)

withdrawals = load_json(
    WITHDRAWALS_FILE,
    {}
)


def save_users():
    save_json(
        USERS_FILE,
        users
    )


def save_tasks():
    save_json(
        TASKS_FILE,
        tasks
    )


def save_submissions():
    save_json(
        SUBMISSIONS_FILE,
        submissions
    )


def save_withdrawals():
    save_json(
        WITHDRAWALS_FILE,
        withdrawals
    )


# =========================================================
# USER
# =========================================================

def get_user(tg_user):

    uid = str(tg_user.id)

    if uid not in users:

        users[uid] = {

            "id": tg_user.id,

            "first_name":
                tg_user.first_name or "",

            "last_name":
                tg_user.last_name or "",

            "username":
                tg_user.username or "",

            "balance": 0.0,

            "referrals": [],

            "referred_by": None,

            "referral_earnings": 0.0,

            "completed_tasks": [],

            "joined":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
        }

        save_users()

    else:

        users[uid]["first_name"] = (
            tg_user.first_name or ""
        )

        users[uid]["last_name"] = (
            tg_user.last_name or ""
        )

        users[uid]["username"] = (
            tg_user.username or ""
        )

        save_users()

    return users[uid]


# =========================================================
# MAIN KEYBOARD
# =========================================================

def main_keyboard():

    keyboard = [

        [
            "💸 Balance",
            "💰 Tasks"
        ],

        [
            "📤 Withdraw",
            "👤 Profile"
        ],

        [
            "🏆 Top",
            "🫂 My Referrals"
        ],

        [
            "🌏 Language"
        ]

    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )


# =========================================================
# ADMIN KEYBOARD
# =========================================================

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
            )
        ],

        [
            InlineKeyboardButton(
                "🗑 Delete Task",
                callback_data="admin_delete_task"
            ),

            InlineKeyboardButton(
                "👥 Users",
                callback_data="admin_users"
            )
        ],

        [
            InlineKeyboardButton(
                "📥 Pending Tasks",
                callback_data="admin_pending"
            )
        ],

        [
            InlineKeyboardButton(
                "💰 Add Balance",
                callback_data="admin_add_balance"
            ),

            InlineKeyboardButton(
                "➖ Remove Balance",
                callback_data="admin_remove_balance"
            )
        ],

        [
            InlineKeyboardButton(
                "📤 Withdrawals",
                callback_data="admin_withdrawals"
            )
        ]
    ]

    return InlineKeyboardMarkup(
        keyboard
    )


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = get_user(
        update.effective_user
    )

    if context.args:

        referral_id = context.args[0]

        if (
            referral_id.isdigit()
            and referral_id != str(user["id"])
            and user["referred_by"] is None
            and referral_id in users
        ):

            user["referred_by"] = int(
                referral_id
            )

            if str(user["id"]) not in users[
                referral_id
            ]["referrals"]:

                users[
                    referral_id
                ]["referrals"].append(
                    str(user["id"])
                )

            save_users()

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

async def balance(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = get_user(
        update.effective_user
    )

    await update.message.reply_text(

        "💸 BALANCE\n\n"

        f"💰 Balance: "
        f"{user['balance']:.2f} BDT\n\n"

        f"👥 Referrals: "
        f"{len(user['referrals'])}\n\n"

        f"🎁 Referral Earnings: "
        f"{user['referral_earnings']:.2f} BDT"
    )


# =========================================================
# PROFILE
# =========================================================

async def profile(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = get_user(
        update.effective_user
    )

    username = (
        "@" + user["username"]
        if user["username"]
        else "No username"
    )

    await update.message.reply_text(

        "👤 PROFILE\n\n"

        f"🆔 ID: {user['id']}\n"
        f"👤 Username: {username}\n"
        f"💰 Balance: {user['balance']:.2f} BDT\n"
        f"👥 Referrals: {len(user['referrals'])}\n"
        f"🎁 Referral Earnings: "
        f"{user['referral_earnings']:.2f} BDT\n"
        f"📅 Joined: {user['joined']}"
    )


# =========================================================
# REFERRALS
# =========================================================

async def referrals(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = get_user(
        update.effective_user
    )

    bot = await context.bot.get_me()

    link = (
        f"https://t.me/{bot.username}"
        f"?start={user['id']}"
    )

    await update.message.reply_text(

        "🫂 MY REFERRALS\n\n"

        f"👥 Referrals: "
        f"{len(user['referrals'])}\n"

        f"🎁 Earnings: "
        f"{user['referral_earnings']:.2f} BDT\n\n"

        f"🔗 Your Referral Link:\n{link}"
    )


# =========================================================
# TASK LIST
# =========================================================

async def show_tasks(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = get_user(
        update.effective_user
    )

    keyboard = []

    for task_id, task in tasks.items():

        if task_id in user["completed_tasks"]:
            continue

        reward = float(
            task["reward"]
        )

        button_text = (
            f"{task['title']} "
            f"({reward:.2f} BDT)"
        )

        keyboard.append([

            InlineKeyboardButton(
                button_text,
                callback_data=
                f"select_task_{task_id}"
            )

        ])

    if not keyboard:

        await update.message.reply_text(

            "📋 Tasks\n\n"
            "❌ বর্তমানে কোনো Task নেই।"
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

async def select_task(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    task_id = query.data.replace(
        "select_task_",
        ""
    )

    if task_id not in tasks:

        await query.message.reply_text(
            "❌ Task not found."
        )

        return

    task = tasks[task_id]

    reward = float(
        task["reward"]
    )

    text = (

        f"📋 Task: {task['title']}\n\n"

        f"💰 Reward: "
        f"{reward:.2f} BDT\n\n"

        f"⏳ Review time: "
        f"{task['review_time']}\n\n"

        f"📄 Description:\n"
        f"{task['description']}\n\n"

        f"✍️ Report instruction:\n"
        f"{task['report_instruction']}\n"
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

async def start_task(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = get_user(
        query.from_user
    )

    task_id = query.data.replace(
        "start_task_",
        ""
    )

    if task_id not in tasks:

        await query.message.reply_text(
            "❌ Task not found."
        )

        return

    for submission in submissions.values():

        if (
            submission["user_id"]
            == user["id"]
            and submission["task_id"]
            == task_id
            and submission["status"]
            == "pending"
        ):

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

async def confirm_submission(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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

    if not task_id or task_id not in tasks:

        await query.message.reply_text(
            "❌ Task session expired."
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

    submission_id = str(
        len(submissions) + 1
    )

    while submission_id in submissions:

        submission_id = str(
            int(submission_id) + 1
        )

    submissions[submission_id] = {

        "id": submission_id,

        "user_id": user["id"],

        "username":
            user["username"],

        "task_id": task_id,

        "task_name":
            tasks[task_id]["title"],

        "reward":
            float(tasks[task_id]["reward"]),

        "facebook_uid":
            uid_value,

        "report":
            report,

        "status":
            "pending",

        "created_at":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
    }

    save_submissions()

    context.user_data.clear()

    await query.message.reply_text(

        "✅ Your report has been received!\n"
        "Please wait.\n\n"

        "⏳ Task Pending Review"
    )

    # Notify Admin
    try:

        await context.bot.send_message(

            chat_id=ADMIN_ID,

            text=(

                "📥 NEW TASK SUBMISSION\n\n"

                f"🆔 Submission: "
                f"{submission_id}\n"

                f"👤 User ID: "
                f"{user['id']}\n"

                f"👤 Username: "
                f"@{user['username'] if user['username'] else 'None'}\n\n"

                f"📋 Task: "
                f"{tasks[task_id]['title']}\n"

                f"💰 Reward: "
                f"{float(tasks[task_id]['reward']):.2f} BDT\n\n"

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
                        f"approve_{submission_id}"
                    ),

                    InlineKeyboardButton(
                        "❌ Reject",
                        callback_data=
                        f"reject_{submission_id}"
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

async def review_submission(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    if query.from_user.id != ADMIN_ID:

        await query.message.reply_text(
            "❌ Access denied."
        )

        return

    if query.data.startswith(
        "approve_"
    ):

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

    if submission_id not in submissions:

        await query.message.reply_text(
            "❌ Submission not found."
        )

        return

    submission = submissions[
        submission_id
    ]

    if submission["status"] != "pending":

        await query.message.reply_text(
            "⚠️ Already reviewed."
        )

        return

    submission["status"] = action

    submission["reviewed_at"] = (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    save_submissions()

    user_id = str(
        submission["user_id"]
    )

    reward = float(
        submission["reward"]
    )

    # =====================================================
    # APPROVED
    # =====================================================

    if action == "approved":

        if user_id in users:

            users[user_id]["balance"] += reward

            if (
                submission["task_id"]
                not in
                users[user_id]["completed_tasks"]
            ):

                users[
                    user_id
                ]["completed_tasks"].append(
                    submission["task_id"]
                )

            # Referral commission
            referrer = users[user_id].get(
                "referred_by"
            )

            if referrer:

                referrer_id = str(
                    referrer
                )

                if referrer_id in users:

                    commission = (
                        reward *
                        REFERRAL_PERCENT
                    )

                    users[
                        referrer_id
                    ]["balance"] += commission

                    users[
                        referrer_id
                    ]["referral_earnings"] += commission

            save_users()

        await query.message.reply_text(

            "✅ TASK APPROVED\n\n"

            f"👤 User ID: "
            f"{submission['user_id']}\n"

            f"💰 Reward Added: "
            f"{reward:.2f} BDT"
        )

        try:

            await context.bot.send_message(

                chat_id=submission[
                    "user_id"
                ],

                text=(

                    "🎉 Task Approved!\n\n"

                    f"📋 Task: "
                    f"{submission['task_name']}\n"

                    f"💰 Reward: "
                    f"{reward:.2f} BDT\n\n"

                    f"💵 Your Balance: "
                    f"{users[user_id]['balance']:.2f} BDT"
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
            f"{submission['user_id']}"
        )

        try:

            await context.bot.send_message(

                chat_id=submission[
                    "user_id"
                ],

                text=(

                    "❌ Task Rejected\n\n"

                    f"📋 Task: "
                    f"{submission['task_name']}\n\n"

                    "💰 No reward was added."
                )
            )

        except Exception as e:

            logger.error(e)


# =========================================================
# ADMIN COMMAND
# =========================================================

async def admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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

async def admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    if query.from_user.id != ADMIN_ID:

        await query.message.reply_text(
            "❌ Access denied."
        )

        return

    action = query.data

    # -----------------------------------------------------
    # ADD TASK
    # -----------------------------------------------------

    if action == "admin_add_task":

        context.user_data[
            "admin_state"
        ] = "task_name"

        await query.message.reply_text(

            "➕ ADD TASK\n\n"

            "📌 Send Task Name:"
        )

        return

    # -----------------------------------------------------
    # ALL TASKS
    # -----------------------------------------------------

    if action == "admin_all_tasks":

        if not tasks:

            await query.message.reply_text(
                "📋 No tasks available."
            )

            return

        text = "📋 ALL TASKS\n\n"

        for task_id, task in tasks.items():

            text += (

                f"🆔 Task ID: {task_id}\n"
                f"📌 {task['title']}\n"
                f"💰 {float(task['reward']):.2f} BDT\n"
                f"⏳ {task['review_time']}\n\n"
            )

        await query.message.reply_text(
            text
        )

        return

    # -----------------------------------------------------
    # DELETE TASK
    # -----------------------------------------------------

    if action == "admin_delete_task":

        if not tasks:

            await query.message.reply_text(
                "❌ No tasks."
            )

            return

        text = "🗑 DELETE TASK\n\n"

        for task_id, task in tasks.items():

            text += (

                f"🆔 {task_id}\n"
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

    # -----------------------------------------------------
    # PENDING
    # -----------------------------------------------------

    if action == "admin_pending":

        pending = [

            s for s in submissions.values()

            if s["status"] == "pending"
        ]

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
                f"📋 Task: {s['task_name']}\n"
                f"💰 Reward: "
                f"{float(s['reward']):.2f} BDT\n"
                f"🆔 UID: {s['facebook_uid']}\n\n"
                f"📄 Report:\n{s['report']}",

                reply_markup=
                InlineKeyboardMarkup(keyboard)
            )

        return

    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    if action == "admin_users":

        await query.message.reply_text(

            "👥 USERS\n\n"

            f"Total Users: "
            f"{len(users)}"
        )

        return

    # -----------------------------------------------------
    # ADD BALANCE
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # REMOVE BALANCE
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # WITHDRAWALS
    # -----------------------------------------------------

    if action == "admin_withdrawals":

        pending = [

            w for w in withdrawals.values()

            if w["status"] == "pending"
        ]

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
                f"💰 {w['amount']:.2f} BDT\n"
                f"💳 Method: {w['method']}\n\n"
            )

        await query.message.reply_text(
            text
        )


# =========================================================
# ADMIN TEXT PROCESSING
# =========================================================

async def process_admin_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return False

    state = context.user_data.get(
        "admin_state"
    )

    if not state:
        return False

    text = update.message.text.strip()

    # -----------------------------------------------------
    # TASK NAME
    # -----------------------------------------------------

    if state == "task_name":

        context.user_data[
            "new_task_name"
        ] = text

        context.user_data[
            "admin_state"
        ] = "task_reward"

        await update.message.reply_text(

            "💵 Send Reward in BDT:\n\n"

            "Example:\n"
            "10\n\n"

            "or\n\n"
            "25.50"
        )

        return True

    # -----------------------------------------------------
    # TASK REWARD
    # -----------------------------------------------------

    if state == "task_reward":

        try:

            reward = float(text)

            if reward <= 0:
                raise ValueError

        except ValueError:

            await update.message.reply_text(

                "❌ Invalid amount.\n\n"

                "Example:\n"
                "10\n"
                "25.50"
            )

            return True

        context.user_data[
            "new_task_reward"
        ] = reward

        context.user_data[
            "admin_state"
        ] = "task_review"

        await update.message.reply_text(

            "⏳ Send Review Time:\n\n"

            "Example:\n"
            "12 hours"
        )

        return True

    # -----------------------------------------------------
    # REVIEW TIME
    # -----------------------------------------------------

    if state == "task_review":

        context.user_data[
            "new_task_review"
        ] = text

        context.user_data[
            "admin_state"
        ] = "task_description"

        await update.message.reply_text(

            "📄 Send Task Description:"
        )

        return True

    # -----------------------------------------------------
    # DESCRIPTION
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # REPORT INSTRUCTION
    # -----------------------------------------------------

    if state == "task_report":

        task_id = str(
            len(tasks) + 1
        )

        while task_id in tasks:

            task_id = str(
                int(task_id) + 1
            )

        tasks[task_id] = {

            "title":
                context.user_data[
                    "new_task_name"
                ],

            "reward":
                context.user_data[
                    "new_task_reward"
                ],

            "review_time":
                context.user_data[
                    "new_task_review"
                ],

            "description":
                context.user_data[
                    "new_task_description"
                ],

            "report_instruction":
                text,

            "created_at":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
        }

        save_tasks()

        context.user_data.clear()

        await update.message.reply_text(

            "✅ TASK ADDED SUCCESSFULLY!\n\n"

            f"🆔 Task ID: {task_id}\n"
            f"📌 Task: {tasks[task_id]['title']}\n"
            f"💰 Reward: "
            f"{float(tasks[task_id]['reward']):.2f} BDT\n"
            f"⏳ Review: "
            f"{tasks[task_id]['review_time']}"
        )

        return True

    # -----------------------------------------------------
    # DELETE TASK
    # -----------------------------------------------------

    if state == "delete_task":

        if text not in tasks:

            await update.message.reply_text(
                "❌ Task ID not found."
            )

            return True

        deleted = tasks.pop(
            text
        )

        save_tasks()

        context.user_data.clear()

        await update.message.reply_text(

            "✅ Task Deleted\n\n"

            f"📌 {deleted['title']}"
        )

        return True

    # -----------------------------------------------------
    # ADD BALANCE
    # -----------------------------------------------------

    if state == "add_balance":

        try:

            user_id, amount = text.split(
                "|",
                1
            )

            user_id = user_id.strip()

            amount = float(
                amount.strip()
            )

            if user_id not in users:
                raise ValueError

            if amount <= 0:
                raise ValueError

            users[user_id][
                "balance"
            ] += amount

            save_users()

            context.user_data.clear()

            await update.message.reply_text(

                "✅ Balance Added\n\n"

                f"👤 User: {user_id}\n"

                f"➕ Added: "
                f"{amount:.2f} BDT\n"

                f"💵 New Balance: "
                f"{users[user_id]['balance']:.2f} BDT"
            )

        except Exception:

            await update.message.reply_text(

                "❌ Wrong Format.\n\n"

                "Correct:\n"
                "USER_ID | AMOUNT\n\n"

                "Example:\n"
                "7764329763 | 100"
            )

        return True

    # -----------------------------------------------------
    # REMOVE BALANCE
    # -----------------------------------------------------

    if state == "remove_balance":

        try:

            user_id, amount = text.split(
                "|",
                1
            )

            user_id = user_id.strip()

            amount = float(
                amount.strip()
            )

            if user_id not in users:
                raise ValueError

            if amount <= 0:
                raise ValueError

            users[user_id][
                "balance"
            ] = max(

                0,

                users[user_id]["balance"]
                - amount
            )

            save_users()

            context.user_data.clear()

            await update.message.reply_text(

                "✅ Balance Removed\n\n"

                f"👤 User: {user_id}\n"

                f"➖ Removed: "
                f"{amount:.2f} BDT\n"

                f"💵 Balance: "
                f"{users[user_id]['balance']:.2f} BDT"
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

async def process_task_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    step = context.user_data.get(
        "task_step"
    )

    if not step:
        return False

    text = update.message.text.strip()

    # -----------------------------------------------------
    # UID
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # REPORT
    # -----------------------------------------------------

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
                        "✅ Account registered",
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

async def withdraw(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = get_user(
        update.effective_user
    )

    if user["balance"] <= 0:

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
        f"{user['balance']:.2f} BDT\n\n"

        "Send withdrawal amount:"
    )


# =========================================================
# WITHDRAW PROCESS
# =========================================================

async def process_withdraw(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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

    except:

        await update.message.reply_text(
            "❌ Invalid amount."
        )

        return True

    if amount <= 0:

        await update.message.reply_text(
            "❌ Invalid amount."
        )

        return True

    if amount > user["balance"]:

        await update.message.reply_text(

            f"❌ Insufficient balance.\n\n"

            f"Available: "
            f"{user['balance']:.2f} BDT"
        )

        return True

    request_id = str(
        len(withdrawals) + 1
    )

    while request_id in withdrawals:

        request_id = str(
            int(request_id) + 1
        )

    withdrawals[request_id] = {

        "id": request_id,

        "user_id": user["id"],

        "amount": amount,

        "method": "Pending",

        "status": "pending",

        "date":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
    }

    save_withdrawals()

    context.user_data.clear()

    await update.message.reply_text(

        "✅ Withdrawal Request Submitted!\n\n"

        f"💰 Amount: "
        f"{amount:.2f} BDT\n"

        f"🆔 Request ID: "
        f"{request_id}\n\n"

        "⏳ Please wait for Admin review."
    )

    return True


# =========================================================
# TOP USERS
# =========================================================

async def top_users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not users:

        await update.message.reply_text(
            "🏆 No users yet."
        )

        return

    top = sorted(

        users.values(),

        key=lambda x:
        float(
            x.get("balance", 0)
        ),

        reverse=True

    )[:10]

    text = "🏆 TOP USERS\n\n"

    for i, u in enumerate(
        top,
        1
    ):

        text += (

            f"{i}. "
            f"{u.get('first_name', 'User')}\n"

            f"💰 "
            f"{float(u.get('balance', 0)):.2f} BDT\n\n"
        )

    await update.message.reply_text(
        text
    )


# =========================================================
# LANGUAGE
# =========================================================

async def language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "🌏 LANGUAGE\n\n"

        "🇧🇩 বাংলা\n"
        "🇬🇧 English"
    )


# =========================================================
# TEXT HANDLER
# =========================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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

        await balance(
            update,
            context
        )

    elif text == "💰 Tasks":

        await show_tasks(
            update,
            context
        )

    elif text == "📤 Withdraw":

        await withdraw(
            update,
            context
        )

    elif text == "👤 Profile":

        await profile(
            update,
            context
        )

    elif text == "🏆 Top":

        await top_users(
            update,
            context
        )

    elif text == "🫂 My Referrals":

        await referrals(
            update,
            context
        )

    elif text == "🌏 Language":

        await language(
            update,
            context
        )

    else:

        await update.message.reply_text(

            "❓ Please select an option.",

            reply_markup=main_keyboard()
        )


# =========================================================
# ERROR
# =========================================================

async def error_handler(
    update,
    context
):

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

    # Task select
    application.add_handler(
        CallbackQueryHandler(
            select_task,
            pattern=r"^select_task_"
        )
    )

    # Task start
    application.add_handler(
        CallbackQueryHandler(
            start_task,
            pattern=r"^start_task_"
        )
    )

    # Confirm
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
