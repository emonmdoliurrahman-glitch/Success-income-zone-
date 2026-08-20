import os
import json
import logging
import threading
import asyncio
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


# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 7764329763

REFERRAL_PERCENT = 0.20

USERS_FILE = "users.json"
TASKS_FILE = "tasks.json"
WITHDRAWALS_FILE = "withdrawals.json"

PORT = int(os.getenv("PORT", "10000"))


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# RENDER HEALTH SERVER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
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


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def load_json(filename, default):

    if not os.path.exists(filename):
        return default

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

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
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

    except Exception as e:

        logger.error(
            f"Could not save {filename}: {e}"
        )


# ============================================================
# DATABASE
# ============================================================

users = load_json(
    USERS_FILE,
    {}
)

tasks = load_json(
    TASKS_FILE,
    {}
)

withdrawals = load_json(
    WITHDRAWALS_FILE,
    {}
)


# ============================================================
# SAVE HELPERS
# ============================================================

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


def save_withdrawals():
    save_json(
        WITHDRAWALS_FILE,
        withdrawals
    )


# ============================================================
# USER FUNCTIONS
# ============================================================

def get_user(user):

    user_id = str(user.id)

    if user_id not in users:

        users[user_id] = {

            "id": user.id,

            "first_name":
                user.first_name or "",

            "last_name":
                user.last_name or "",

            "username":
                user.username or "",

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

        # Update profile information
        users[user_id]["first_name"] = (
            user.first_name or ""
        )

        users[user_id]["last_name"] = (
            user.last_name or ""
        )

        users[user_id]["username"] = (
            user.username or ""
        )

        save_users()

    return users[user_id]


# ============================================================
# MAIN KEYBOARD
# ============================================================

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


# ============================================================
# ADMIN KEYBOARD
# ============================================================

def admin_keyboard():

    keyboard = [

        [
            InlineKeyboardButton(
                "➕ Add Task",
                callback_data="admin_add_task"
            ),

            InlineKeyboardButton(
                "🗑 Delete Task",
                callback_data="admin_delete_task"
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
                "👥 Users",
                callback_data="admin_users"
            ),

            InlineKeyboardButton(
                "📤 Withdrawals",
                callback_data="admin_withdrawals"
            )
        ],

        [
            InlineKeyboardButton(
                "📋 All Tasks",
                callback_data="admin_all_tasks"
            )
        ]

    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# START COMMAND
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    data = get_user(user)

    # --------------------------------------------------------
    # REFERRAL
    # --------------------------------------------------------

    if context.args:

        referral_id = context.args[0]

        if (
            referral_id.isdigit()
            and referral_id != str(user.id)
            and data["referred_by"] is None
            and referral_id in users
        ):

            data["referred_by"] = int(
                referral_id
            )

            if (
                str(user.id)
                not in users[referral_id]["referrals"]
            ):

                users[referral_id]["referrals"].append(
                    str(user.id)
                )

            save_users()

    # --------------------------------------------------------
    # WELCOME MESSAGE
    # --------------------------------------------------------

    text = (
        "👋 Welcome to Success Income Zone!\n\n"

        "🎉 এখানে বিভিন্ন Task সম্পন্ন করে "
        "Balance Earn করতে পারবেন।\n\n"

        "💰 Task → Reward\n"
        "👥 Referral → 20% Commission\n"
        "📤 Balance → Withdraw\n\n"

        "👇 নিচের Menu থেকে একটি Option নির্বাচন করুন।"
    )

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard()
    )


# ============================================================
# BALANCE
# ============================================================

async def balance(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = get_user(
        update.effective_user
    )

    text = (

        "💸 YOUR BALANCE\n\n"

        f"💰 Balance: "
        f"{user['balance']:.2f} BDT\n\n"

        f"👥 Referrals: "
        f"{len(user['referrals'])}\n\n"

        f"🎁 Referral Earnings: "
        f"{user['referral_earnings']:.2f} BDT"
    )

    await update.message.reply_text(
        text
    )


# ============================================================
# PROFILE
# ============================================================

async def profile(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = get_user(
        update.effective_user
    )

    if user["username"]:

        username = (
            "@" +
            user["username"]
        )

    else:

        username = "No username"

    text = (

        "👤 PROFILE\n\n"

        f"🆔 ID: "
        f"{user['id']}\n"

        f"👤 Username: "
        f"{username}\n"

        f"💰 Balance: "
        f"{user['balance']:.2f} BDT\n"

        f"👥 Referrals: "
        f"{len(user['referrals'])}\n"

        f"🎁 Referral Earnings: "
        f"{user['referral_earnings']:.2f} BDT\n"

        f"📅 Joined: "
        f"{user['joined']}"
    )

    await update.message.reply_text(
        text
    )


# ============================================================
# REFERRALS
# ============================================================

async def referrals(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = get_user(
        update.effective_user
    )

    bot = await context.bot.get_me()

    referral_link = (
        f"https://t.me/"
        f"{bot.username}"
        f"?start={user['id']}"
    )

    text = (

        "🫂 MY REFERRALS\n\n"

        f"👥 Total Referrals: "
        f"{len(user['referrals'])}\n\n"

        f"💰 Referral Earnings: "
        f"{user['referral_earnings']:.2f} BDT\n\n"

        f"🎁 Commission: "
        f"{REFERRAL_PERCENT * 100:.0f}%\n\n"

        "🔗 YOUR REFERRAL LINK:\n"

        f"{referral_link}\n\n"

        "📢 এই Link আপনার বন্ধুদের Share করুন।"
    )

    await update.message.reply_text(
        text
    )


# ============================================================
# SHOW TASKS
# ============================================================

async def show_tasks(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = get_user(
        update.effective_user
    )

    if not tasks:

        await update.message.reply_text(
            "💰 TASKS\n\n"
            "❌ বর্তমানে কোনো Task available নেই।"
        )

        return

    keyboard = []

    for task_id, task in tasks.items():

        if (
            task_id
            in user["completed_tasks"]
        ):
            continue

        button = InlineKeyboardButton(

            f"💰 {task['title']} "
            f"- {task['reward']} BDT",

            callback_data=
                f"task_{task_id}"
        )

        keyboard.append(
            [button]
        )

    if not keyboard:

        await update.message.reply_text(
            "✅ আপনি বর্তমানে সব Task সম্পন্ন করেছেন।"
        )

        return

    await update.message.reply_text(

        "💰 AVAILABLE TASKS\n\n"
        "👇 Task নির্বাচন করুন:",

        reply_markup=
            InlineKeyboardMarkup(keyboard)
    )


# ============================================================
# TASK CALLBACK
# ============================================================

async def task_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = get_user(
        query.from_user
    )

    task_id = query.data.replace(
        "task_",
        ""
    )

    if task_id not in tasks:

        await query.message.reply_text(
            "❌ এই Task আর available নেই।"
        )

        return

    if (
        task_id
        in user["completed_tasks"]
    ):

        await query.message.reply_text(
            "⚠️ আপনি এই Task ইতিমধ্যে সম্পন্ন করেছেন।"
        )

        return

    task = tasks[task_id]

    reward = float(
        task["reward"]
    )

    # Add completed task
    user["completed_tasks"].append(
        task_id
    )

    # Add user reward
    user["balance"] += reward

    # --------------------------------------------------------
    # REFERRAL COMMISSION
    # --------------------------------------------------------

    referral_commission = 0.0

    if user["referred_by"]:

        referrer_id = str(
            user["referred_by"]
        )

        if referrer_id in users:

            referral_commission = (
                reward *
                REFERRAL_PERCENT
            )

            users[referrer_id]["balance"] += (
                referral_commission
            )

            users[referrer_id][
                "referral_earnings"
            ] += referral_commission

    save_users()

    text = (

        "🎉 TASK COMPLETED!\n\n"

        f"📌 Task: "
        f"{task['title']}\n"

        f"💰 Reward: "
        f"{reward:.2f} BDT\n\n"

        f"💵 Your Balance: "
        f"{user['balance']:.2f} BDT"
    )

    if referral_commission > 0:

        text += (

            "\n\n"
            f"👥 Referral Commission: "
            f"{referral_commission:.2f} BDT"
        )

    await query.message.reply_text(
        text
    )


# ============================================================
# WITHDRAW
# ============================================================

async def withdraw(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = get_user(
        update.effective_user
    )

    if user["balance"] <= 0:

        await update.message.reply_text(

            "📤 WITHDRAW\n\n"

            "❌ আপনার Balance 0 BDT।\n\n"

            "💰 প্রথমে Task সম্পন্ন করুন।"
        )

        return

    context.user_data[
        "withdraw_state"
    ] = True

    await update.message.reply_text(

        "📤 WITHDRAW\n\n"

        f"💰 Current Balance: "
        f"{user['balance']:.2f} BDT\n\n"

        "আপনি কত টাকা Withdraw করতে চান "
        "তা লিখুন।\n\n"

        "উদাহরণ:\n"
        "500"
    )


# ============================================================
# WITHDRAW AMOUNT
# ============================================================

async def process_withdraw_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.user_data.get(
        "withdraw_state"
    ):

        return False

    user = get_user(
        update.effective_user
    )

    try:

        amount = float(
            update.message.text.strip()
        )

        if amount <= 0:

            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ সঠিক Amount লিখুন।\n\n"
            "উদাহরণ: 500"
        )

        return True

    if amount > user["balance"]:

        await update.message.reply_text(

            "❌ আপনার পর্যাপ্ত Balance নেই।\n\n"

            f"💰 Current Balance: "
            f"{user['balance']:.2f} BDT"
        )

        return True

    context.user_data[
        "withdraw_amount"
    ] = amount

    context.user_data[
        "withdraw_state"
    ] = False

    context.user_data[
        "payment_state"
    ] = True

    await update.message.reply_text(

        "💳 PAYMENT METHOD\n\n"

        "আপনার Payment Method লিখুন।\n\n"

        "উদাহরণ:\n"
        "bKash\n"
        "Nagad\n"
        "Rocket"
    )

    return True


# ============================================================
# PAYMENT METHOD
# ============================================================

async def process_payment_method(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.user_data.get(
        "payment_state"
    ):

        return False

    user = get_user(
        update.effective_user
    )

    method = update.message.text.strip()

    amount = float(
        context.user_data.get(
            "withdraw_amount",
            0
        )
    )

    request_id = str(
        len(withdrawals) + 1
    )

    withdrawals[request_id] = {

        "id": request_id,

        "user_id": user["id"],

        "username":
            user["username"],

        "amount": amount,

        "method": method,

        "status": "pending",

        "date":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
    }

    save_withdrawals()

    context.user_data[
        "payment_state"
    ] = False

    await update.message.reply_text(

        "✅ WITHDRAW REQUEST SUBMITTED\n\n"

        f"🆔 Request ID: "
        f"{request_id}\n"

        f"💰 Amount: "
        f"{amount:.2f} BDT\n"

        f"💳 Method: "
        f"{method}\n\n"

        "⏳ আপনার Request Admin যাচাই করবে।"
    )

    # Send request to admin
    try:

        username = (
            "@" + user["username"]
            if user["username"]
            else "No username"
        )

        await context.bot.send_message(

            chat_id=ADMIN_ID,

            text=(

                "📤 NEW WITHDRAW REQUEST\n\n"

                f"🆔 Request ID: "
                f"{request_id}\n"

                f"👤 User ID: "
                f"{user['id']}\n"

                f"👤 Username: "
                f"{username}\n"

                f"💰 Amount: "
                f"{amount:.2f} BDT\n"

                f"💳 Method: "
                f"{method}\n\n"

                "⚠️ Status: Pending"
            )
        )

    except Exception as e:

        logger.error(
            f"Admin notification failed: {e}"
        )

    return True


# ============================================================
# TOP USERS
# ============================================================

async def top_users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not users:

        await update.message.reply_text(
            "🏆 এখনো কোনো User নেই।"
        )

        return

    sorted_users = sorted(

        users.values(),

        key=lambda x:
            float(x.get("balance", 0)),

        reverse=True
    )

    text = "🏆 TOP USERS\n\n"

    for position, user in enumerate(
        sorted_users[:10],
        start=1
    ):

        name = (
            user.get("first_name")
            or "User"
        )

        balance_value = float(
            user.get("balance", 0)
        )

        text += (

            f"{position}. "
            f"{name}\n"

            f"💰 "
            f"{balance_value:.2f} BDT\n\n"
        )

    await update.message.reply_text(
        text
    )


# ============================================================
# LANGUAGE
# ============================================================

async def language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "🌏 LANGUAGE\n\n"

        "🇧🇩 বাংলা\n"
        "🇬🇧 English\n\n"

        "বর্তমানে বাংলা ভাষা চালু আছে।"
    )


# ============================================================
# ADMIN COMMAND
# ============================================================

async def admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    logger.info(
        f"Admin command received from {user_id}"
    )

    if user_id != ADMIN_ID:

        await update.message.reply_text(
            "❌ আপনি Admin নন।"
        )

        return

    await update.message.reply_text(

        "👨‍💻 ADMIN PANEL\n\n"

        "আপনার Admin Panel প্রস্তুত।\n\n"

        "👇 নিচের Button ব্যবহার করুন।",

        reply_markup=admin_keyboard()
    )


# ============================================================
# ADMIN CALLBACK
# ============================================================

async def admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    if query.from_user.id != ADMIN_ID:

        await query.message.reply_text(
            "❌ Access Denied."
        )

        return

    action = query.data

    # --------------------------------------------------------
    # ADD TASK
    # --------------------------------------------------------

    if action == "admin_add_task":

        context.user_data[
            "admin_action"
        ] = "add_task"

        await query.message.reply_text(

            "➕ ADD TASK\n\n"

            "এই Format-এ Task পাঠান:\n\n"

            "Task Name | Reward\n\n"

            "উদাহরণ:\n"

            "Join Telegram | 10"
        )

        return

    # --------------------------------------------------------
    # DELETE TASK
    # --------------------------------------------------------

    if action == "admin_delete_task":

        if not tasks:

            await query.message.reply_text(
                "❌ কোনো Task নেই।"
            )

            return

        text = (
            "🗑 DELETE TASK\n\n"
        )

        for task_id, task in tasks.items():

            text += (

                f"🆔 ID: {task_id}\n"

                f"📌 Task: "
                f"{task['title']}\n"

                f"💰 Reward: "
                f"{task['reward']} BDT\n\n"
            )

        text += (
            "Task ID পাঠান।"
        )

        context.user_data[
            "admin_action"
        ] = "delete_task"

        await query.message.reply_text(
            text
        )

        return

    # --------------------------------------------------------
    # ADD BALANCE
    # --------------------------------------------------------

    if action == "admin_add_balance":

        context.user_data[
            "admin_action"
        ] = "add_balance"

        await query.message.reply_text(

            "💰 ADD BALANCE\n\n"

            "Format:\n\n"

            "USER_ID | AMOUNT\n\n"

            "উদাহরণ:\n"

            "123456789 | 500"
        )

        return

    # --------------------------------------------------------
    # REMOVE BALANCE
    # --------------------------------------------------------

    if action == "admin_remove_balance":

        context.user_data[
            "admin_action"
        ] = "remove_balance"

        await query.message.reply_text(

            "➖ REMOVE BALANCE\n\n"

            "Format:\n\n"

            "USER_ID | AMOUNT\n\n"

            "উদাহরণ:\n"

            "123456789 | 100"
        )

        return

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    if action == "admin_users":

        await query.message.reply_text(

            "👥 USERS\n\n"

            f"Total Users: "
            f"{len(users)}"
        )

        return

    # --------------------------------------------------------
    # WITHDRAWALS
    # --------------------------------------------------------

    if action == "admin_withdrawals":

        pending = [

            item

            for item in withdrawals.values()

            if item.get("status")
            == "pending"
        ]

        if not pending:

            await query.message.reply_text(

                "📤 WITHDRAWALS\n\n"

                "❌ কোনো Pending Withdrawal নেই।"
            )

            return

        text = (
            "📤 PENDING WITHDRAWALS\n\n"
        )

        for item in pending:

            text += (

                f"🆔 Request: "
                f"{item['id']}\n"

                f"👤 User: "
                f"{item['user_id']}\n"

                f"💰 Amount: "
                f"{item['amount']} BDT\n"

                f"💳 Method: "
                f"{item['method']}\n"

                f"📅 Date: "
                f"{item['date']}\n\n"
            )

        await query.message.reply_text(
            text
        )

        return

    # --------------------------------------------------------
    # ALL TASKS
    # --------------------------------------------------------

    if action == "admin_all_tasks":

        if not tasks:

            await query.message.reply_text(
                "📋 কোনো Task নেই।"
            )

            return

        text = (
            "📋 ALL TASKS\n\n"
        )

        for task_id, task in tasks.items():

            text += (

                f"🆔 ID: {task_id}\n"

                f"📌 {task['title']}\n"

                f"💰 {task['reward']} BDT\n\n"
            )

        await query.message.reply_text(
            text
        )

        return


# ============================================================
# ADMIN TEXT ACTIONS
# ============================================================

async def process_admin_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:

        return False

    action = context.user_data.get(
        "admin_action"
    )

    if not action:

        return False

    text = update.message.text.strip()

    # --------------------------------------------------------
    # ADD TASK
    # --------------------------------------------------------

    if action == "add_task":

        try:

            title, reward = text.split(
                "|",
                1
            )

            title = title.strip()

            reward = float(
                reward.strip()
            )

            task_id = str(
                len(tasks) + 1
            )

            # Prevent ID collision
            while task_id in tasks:

                task_id = str(
                    int(task_id) + 1
                )

            tasks[task_id] = {

                "title": title,

                "reward": reward
            }

            save_tasks()

            context.user_data[
                "admin_action"
            ] = None

            await update.message.reply_text(

                "✅ TASK ADDED\n\n"

                f"🆔 ID: "
                f"{task_id}\n"

                f"📌 Task: "
                f"{title}\n"

                f"💰 Reward: "
                f"{reward:.2f} BDT"
            )

        except Exception:

            await update.message.reply_text(

                "❌ Format ভুল।\n\n"

                "সঠিক Format:\n"

                "Task Name | Reward\n\n"

                "উদাহরণ:\n"

                "Join Telegram | 10"
            )

        return True

    # --------------------------------------------------------
    # DELETE TASK
    # --------------------------------------------------------

    if action == "delete_task":

        if text not in tasks:

            await update.message.reply_text(
                "❌ Task ID পাওয়া যায়নি।"
            )

            return True

        deleted_task = tasks.pop(
            text
        )

        save_tasks()

        context.user_data[
            "admin_action"
        ] = None

        await update.message.reply_text(

            "✅ TASK DELETED\n\n"

            f"📌 {deleted_task['title']}"
        )

        return True

    # --------------------------------------------------------
    # ADD BALANCE
    # --------------------------------------------------------

    if action == "add_balance":

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

                await update.message.reply_text(
                    "❌ User পাওয়া যায়নি।"
                )

                return True

            if amount <= 0:

                await update.message.reply_text(
                    "❌ Amount অবশ্যই 0-এর বেশি হতে হবে।"
                )

                return True

            users[user_id][
                "balance"
            ] += amount

            save_users()

            new_balance = users[user_id][
                "balance"
            ]

            context.user_data[
                "admin_action"
            ] = None

            await update.message.reply_text(

                "✅ BALANCE ADDED\n\n"

                f"👤 User ID: "
                f"{user_id}\n"

                f"💰 Added: "
                f"{amount:.2f} BDT\n"

                f"💵 New Balance: "
                f"{new_balance:.2f} BDT"
            )

            # Notify user
            try:

                await context.bot.send_message(

                    chat_id=int(user_id),

                    text=(

                        "💰 BALANCE UPDATED\n\n"

                        f"আপনার Balance-এ "
                        f"{amount:.2f} BDT "
                        "যোগ করা হয়েছে।\n\n"

                        f"💵 Current Balance: "
                        f"{new_balance:.2f} BDT"
                    )
                )

            except Exception as e:

                logger.error(
                    f"User balance notification failed: {e}"
                )

        except Exception:

            await update.message.reply_text(

                "❌ Format ভুল।\n\n"

                "USER_ID | AMOUNT"
            )

        return True

    # --------------------------------------------------------
    # REMOVE BALANCE
    # --------------------------------------------------------

    if action == "remove_balance":

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

                await update.message.reply_text(
                    "❌ User পাওয়া যায়নি।"
                )

                return True

            if amount <= 0:

                await update.message.reply_text(
                    "❌ Amount অবশ্যই 0-এর বেশি হতে হবে।"
                )

                return True

            old_balance = float(
                users[user_id]["balance"]
            )

            users[user_id][
                "balance"
            ] = max(
                0,
                old_balance - amount
            )

            save_users()

            new_balance = users[user_id][
                "balance"
            ]

            context.user_data[
                "admin_action"
            ] = None

            await update.message.reply_text(

                "✅ BALANCE REMOVED\n\n"

                f"👤 User ID: "
                f"{user_id}\n"

                f"➖ Removed: "
                f"{amount:.2f} BDT\n"

                f"💵 New Balance: "
                f"{new_balance:.2f} BDT"
            )

        except Exception:

            await update.message.reply_text(

                "❌ Format ভুল।\n\n"

                "USER_ID | AMOUNT"
            )

        return True

    return False


# ============================================================
# NORMAL TEXT HANDLER
# ============================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    # --------------------------------------------------------
    # ADMIN ACTION
    # --------------------------------------------------------

    if update.effective_user.id == ADMIN_ID:

        processed = await process_admin_action(
            update,
            context
        )

        if processed:

            return

    # --------------------------------------------------------
    # WITHDRAW AMOUNT
    # --------------------------------------------------------

    if context.user_data.get(
        "withdraw_state"
    ):

        processed = await process_withdraw_amount(
            update,
            context
        )

        if processed:

            return

    # --------------------------------------------------------
    # PAYMENT METHOD
    # --------------------------------------------------------

    if context.user_data.get(
        "payment_state"
    ):

        processed = await process_payment_method(
            update,
            context
        )

        if processed:

            return

    # --------------------------------------------------------
    # MENU
    # --------------------------------------------------------

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

            "❓ Menu থেকে একটি Option নির্বাচন করুন।",

            reply_markup=main_keyboard()
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(

        "Exception while handling update:",

        exc_info=context.error
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # TOKEN CHECK
    # --------------------------------------------------------

    if not BOT_TOKEN:

        logger.error(
            "BOT_TOKEN Environment Variable পাওয়া যায়নি!"
        )

        return

    # --------------------------------------------------------
    # RENDER HEALTH SERVER
    # --------------------------------------------------------

    health_thread = threading.Thread(

        target=run_health_server,

        daemon=True
    )

    health_thread.start()

    # --------------------------------------------------------
    # BUILD TELEGRAM APPLICATION
    # --------------------------------------------------------

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # --------------------------------------------------------
    # COMMANDS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # TASK CALLBACK
    # --------------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            task_callback,
            pattern=r"^task_"
        )
    )

    # --------------------------------------------------------
    # ADMIN CALLBACK
    # --------------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^admin_"
        )
    )

    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_handler
        )
    )

    # --------------------------------------------------------
    # ERROR
    # --------------------------------------------------------

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Success Income Zone Bot is starting..."
    )

    logger.info(
        f"Admin ID: {ADMIN_ID}"
    )

    # --------------------------------------------------------
    # RUN POLLING
    # --------------------------------------------------------

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
