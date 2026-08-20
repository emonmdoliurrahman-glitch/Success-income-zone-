import os
import json
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
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

BOT_TOKEN = os.getenv("8393226821:AAHmspHI9QwHZzyh81WGg14uz3C7GrBxH9g")
ADMIN_ID = 7764329763

REFERRAL_PERCENT = 0.20

USERS_FILE = "users.json"
TASKS_FILE = "tasks.json"
WITHDRAW_FILE = "withdrawals.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


# =========================================================
# DATABASE
# =========================================================

def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


users = load_json(USERS_FILE, {})
tasks = load_json(TASKS_FILE, {})
withdrawals = load_json(WITHDRAW_FILE, {})


# =========================================================
# USER FUNCTIONS
# =========================================================

def get_user(user):
    uid = str(user.id)

    if uid not in users:
        users[uid] = {
            "id": user.id,
            "first_name": user.first_name or "",
            "username": user.username or "",
            "balance": 0.0,
            "referrals": [],
            "referred_by": None,
            "referral_earnings": 0.0,
            "completed_tasks": [],
            "joined": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_json(USERS_FILE, users)

    return users[uid]


def save_users():
    save_json(USERS_FILE, users)


def save_tasks():
    save_json(TASKS_FILE, tasks)


def save_withdrawals():
    save_json(WITHDRAW_FILE, withdrawals)


# =========================================================
# KEYBOARD
# =========================================================

def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["💸 Balance", "💰 Tasks"],
            ["📤 Withdraw", "👤 Profile"],
            ["🏆 Top", "🫂 My Referrals"],
            ["🌏 Language"]
        ],
        resize_keyboard=True
    )


def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add Task", callback_data="admin_add_task"),
            InlineKeyboardButton("🗑 Delete Task", callback_data="admin_delete_task")
        ],
        [
            InlineKeyboardButton("💰 Add Balance", callback_data="admin_add_balance"),
            InlineKeyboardButton("➖ Remove Balance", callback_data="admin_remove_balance")
        ],
        [
            InlineKeyboardButton("👥 Users", callback_data="admin_users"),
            InlineKeyboardButton("📤 Withdrawals", callback_data="admin_withdrawals")
        ]
    ])


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    data = get_user(user)

    # Referral
    if context.args:
        ref_id = context.args[0]

        if (
            ref_id.isdigit()
            and ref_id != str(user.id)
            and data["referred_by"] is None
            and ref_id in users
        ):
            data["referred_by"] = int(ref_id)

            if str(user.id) not in users[ref_id]["referrals"]:
                users[ref_id]["referrals"].append(str(user.id))

            save_users()

    text = (
        f"👋 Welcome {user.first_name}!\n\n"
        "🎉 Welcome to Success Income Zone\n\n"
        "💰 Earn money by completing available tasks.\n"
        "👥 Invite friends and earn referral commission.\n\n"
        "👇 Select an option below."
    )

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard()
    )


# =========================================================
# BALANCE
# =========================================================

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = get_user(update.effective_user)

    text = (
        "💸 YOUR BALANCE\n\n"
        f"💰 Balance: {user['balance']:.2f} BDT\n"
        f"👥 Referrals: {len(user['referrals'])}\n"
        f"🎁 Referral Earnings: {user['referral_earnings']:.2f} BDT"
    )

    await update.message.reply_text(text)


# =========================================================
# PROFILE
# =========================================================

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = get_user(update.effective_user)

    username = (
        f"@{user['username']}"
        if user["username"]
        else "No username"
    )

    text = (
        "👤 PROFILE\n\n"
        f"🆔 ID: {user['id']}\n"
        f"👤 Username: {username}\n"
        f"💰 Balance: {user['balance']:.2f} BDT\n"
        f"👥 Referrals: {len(user['referrals'])}\n"
        f"🎁 Referral Earnings: {user['referral_earnings']:.2f} BDT\n"
        f"📅 Joined: {user['joined']}"
    )

    await update.message.reply_text(text)


# =========================================================
# REFERRAL
# =========================================================

async def referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = get_user(update.effective_user)

    bot = await context.bot.get_me()

    link = f"https://t.me/{bot.username}?start={user['id']}"

    text = (
        "🫂 MY REFERRALS\n\n"
        f"👥 Total Referrals: {len(user['referrals'])}\n"
        f"💰 Referral Earnings: {user['referral_earnings']:.2f} BDT\n\n"
        "🎁 Referral Commission: 20%\n\n"
        "🔗 Your Referral Link:\n"
        f"{link}\n\n"
        "📢 Share this link with your friends."
    )

    await update.message.reply_text(text)


# =========================================================
# TASKS
# =========================================================

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = get_user(update.effective_user)

    if not tasks:
        await update.message.reply_text(
            "💰 TASKS\n\n❌ বর্তমানে কোনো Task নেই।"
        )
        return

    keyboard = []

    for task_id, task in tasks.items():

        if task_id in user["completed_tasks"]:
            continue

        keyboard.append([
            InlineKeyboardButton(
                f"💰 {task['title']} - {task['reward']} BDT",
                callback_data=f"task_{task_id}"
            )
        ])

    if not keyboard:
        await update.message.reply_text(
            "✅ আপনি সব Task সম্পন্ন করেছেন।"
        )
        return

    await update.message.reply_text(
        "💰 AVAILABLE TASKS\n\n"
        "একটি Task নির্বাচন করুন:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def task_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = get_user(query.from_user)

    task_id = query.data.replace("task_", "")

    if task_id not in tasks:
        await query.message.reply_text("❌ Task পাওয়া যায়নি।")
        return

    if task_id in user["completed_tasks"]:
        await query.message.reply_text(
            "⚠️ আপনি এই Task ইতিমধ্যে সম্পন্ন করেছেন।"
        )
        return

    task = tasks[task_id]

    # Task completion
    user["completed_tasks"].append(task_id)
    user["balance"] += float(task["reward"])

    # Referral commission
    if user["referred_by"]:

        ref_id = str(user["referred_by"])

        if ref_id in users:

            commission = float(task["reward"]) * REFERRAL_PERCENT

            users[ref_id]["balance"] += commission
            users[ref_id]["referral_earnings"] += commission

    save_users()

    await query.message.reply_text(
        "🎉 TASK COMPLETED!\n\n"
        f"📌 Task: {task['title']}\n"
        f"💰 Reward: {task['reward']:.2f} BDT\n\n"
        f"💵 Your Balance: {user['balance']:.2f} BDT"
    )


# =========================================================
# WITHDRAW
# =========================================================

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = get_user(update.effective_user)

    if user["balance"] <= 0:
        await update.message.reply_text(
            "❌ আপনার Balance 0 BDT।\n\n"
            "প্রথমে Task সম্পন্ন করুন।"
        )
        return

    context.user_data["withdraw_state"] = True

    await update.message.reply_text(
        "📤 WITHDRAW\n\n"
        f"💰 আপনার Balance: {user['balance']:.2f} BDT\n\n"
        "আপনি কত টাকা Withdraw করতে চান লিখুন।\n\n"
        "উদাহরণ:\n"
        "500"
    )


async def process_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("withdraw_state"):
        return False

    user = get_user(update.effective_user)

    try:
        amount = float(update.message.text)

        if amount <= 0:
            raise ValueError

    except ValueError:
        await update.message.reply_text(
            "❌ সঠিক Amount লিখুন।\n\nউদাহরণ: 500"
        )
        return True

    if amount > user["balance"]:
        await update.message.reply_text(
            f"❌ আপনার Balance মাত্র {user['balance']:.2f} BDT।"
        )
        return True

    context.user_data["withdraw_amount"] = amount
    context.user_data["withdraw_state"] = False
    context.user_data["payment_state"] = True

    await update.message.reply_text(
        "💳 PAYMENT METHOD\n\n"
        "আপনার Payment Method লিখুন।\n\n"
        "উদাহরণ:\n"
        "bKash\n"
        "Nagad\n"
        "Rocket"
    )

    return True


async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("payment_state"):
        return False

    user = get_user(update.effective_user)

    method = update.message.text
    amount = context.user_data.get("withdraw_amount", 0)

    withdrawal_id = str(len(withdrawals) + 1)

    withdrawals[withdrawal_id] = {
        "id": withdrawal_id,
        "user_id": user["id"],
        "username": user["username"],
        "amount": amount,
        "method": method,
        "status": "pending",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    save_withdrawals()

    context.user_data["payment_state"] = False

    await update.message.reply_text(
        "✅ WITHDRAW REQUEST SUBMITTED\n\n"
        f"💰 Amount: {amount:.2f} BDT\n"
        f"💳 Method: {method}\n"
        f"🆔 Request ID: {withdrawal_id}\n\n"
        "⏳ Admin আপনার Request যাচাই করবে।"
    )

    try:

        await context.bot.send_message(
            ADMIN_ID,
            "📤 NEW WITHDRAW REQUEST\n\n"
            f"🆔 Request ID: {withdrawal_id}\n"
            f"👤 User ID: {user['id']}\n"
            f"👤 Username: @{user['username']}\n"
            f"💰 Amount: {amount:.2f} BDT\n"
            f"💳 Method: {method}"
        )

    except Exception as e:
        logging.error(e)

    return True


# =========================================================
# TOP USERS
# =========================================================

async def top_users(update: Update, context: ContextTypes.DEFAULT_TYPE):

    sorted_users = sorted(
        users.values(),
        key=lambda x: x["balance"],
        reverse=True
    )

    text = "🏆 TOP USERS\n\n"

    for i, user in enumerate(sorted_users[:10], start=1):

        name = user["first_name"] or "User"

        text += (
            f"{i}. {name}\n"
            f"💰 {user['balance']:.2f} BDT\n\n"
        )

    if len(sorted_users) == 0:
        text = "❌ কোনো User নেই।"

    await update.message.reply_text(text)


# =========================================================
# LANGUAGE
# =========================================================

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🌏 LANGUAGE\n\n"
        "🇧🇩 বাংলা\n"
        "🇬🇧 English\n\n"
        "বর্তমানে বাংলা ভাষা চালু আছে।"
    )


# =========================================================
# ADMIN PANEL
# =========================================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ আপনি Admin নন।")
        return

    await update.message.reply_text(
        "👨‍💻 ADMIN PANEL\n\n"
        "নিচের অপশন নির্বাচন করুন:",
        reply_markup=admin_keyboard()
    )


# =========================================================
# ADMIN CALLBACK
# =========================================================

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.message.reply_text("❌ Access Denied.")
        return

    action = query.data

    if action == "admin_add_task":

        context.user_data["admin_action"] = "add_task"

        await query.message.reply_text(
            "➕ ADD TASK\n\n"
            "এই format-এ Task পাঠান:\n\n"
            "Task Name | Reward\n\n"
            "উদাহরণ:\n"
            "Join Telegram | 10"
        )

    elif action == "admin_delete_task":

        if not tasks:
            await query.message.reply_text(
                "❌ কোনো Task নেই।"
            )
            return

        text = "🗑 DELETE TASK\n\n"

        for tid, task in tasks.items():
            text += (
                f"ID: {tid}\n"
                f"Task: {task['title']}\n"
                f"Reward: {task['reward']} BDT\n\n"
            )

        text += "Task ID লিখে পাঠান।"

        context.user_data["admin_action"] = "delete_task"

        await query.message.reply_text(text)

    elif action == "admin_add_balance":

        context.user_data["admin_action"] = "add_balance"

        await query.message.reply_text(
            "💰 ADD BALANCE\n\n"
            "এই format-এ পাঠান:\n\n"
            "USER_ID | AMOUNT\n\n"
            "উদাহরণ:\n"
            "123456789 | 500"
        )

    elif action == "admin_remove_balance":

        context.user_data["admin_action"] = "remove_balance"

        await query.message.reply_text(
            "➖ REMOVE BALANCE\n\n"
            "এই format-এ পাঠান:\n\n"
            "USER_ID | AMOUNT"
        )

    elif action == "admin_users":

        await query.message.reply_text(
            f"👥 TOTAL USERS: {len(users)}"
        )

    elif action == "admin_withdrawals":

        pending = [
            x for x in withdrawals.values()
            if x["status"] == "pending"
        ]

        if not pending:
            await query.message.reply_text(
                "📤 কোনো Pending Withdrawal নেই।"
            )
            return

        text = "📤 PENDING WITHDRAWALS\n\n"

        for item in pending:
            text += (
                f"🆔 ID: {item['id']}\n"
                f"👤 User: {item['user_id']}\n"
                f"💰 Amount: {item['amount']} BDT\n"
                f"💳 Method: {item['method']}\n\n"
            )

        await query.message.reply_text(text)


# =========================================================
# ADMIN TEXT ACTIONS
# =========================================================

async def process_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return False

    action = context.user_data.get("admin_action")

    if not action:
        return False

    text = update.message.text.strip()

    # ADD TASK
    if action == "add_task":

        try:
            title, reward = text.split("|", 1)

            title = title.strip()
            reward = float(reward.strip())

            task_id = str(len(tasks) + 1)

            tasks[task_id] = {
                "title": title,
                "reward": reward
            }

            save_tasks()

            context.user_data["admin_action"] = None

            await update.message.reply_text(
                "✅ TASK ADDED\n\n"
                f"🆔 ID: {task_id}\n"
                f"📌 {title}\n"
                f"💰 Reward: {reward} BDT"
            )

        except Exception:
            await update.message.reply_text(
                "❌ Format ভুল।\n\n"
                "সঠিক format:\n"
                "Task Name | Reward"
            )

        return True

    # DELETE TASK
    if action == "delete_task":

        if text not in tasks:
            await update.message.reply_text(
                "❌ Task ID পাওয়া যায়নি।"
            )
            return True

        deleted = tasks.pop(text)

        save_tasks()

        context.user_data["admin_action"] = None

        await update.message.reply_text(
            "✅ Task Deleted\n\n"
            f"📌 {deleted['title']}"
        )

        return True

    # ADD BALANCE
    if action == "add_balance":

        try:
            uid, amount = text.split("|", 1)

            uid = uid.strip()
            amount = float(amount.strip())

            if uid not in users:
                await update.message.reply_text(
                    "❌ User পাওয়া যায়নি।"
                )
                return True

            users[uid]["balance"] += amount

            save_users()

            context.user_data["admin_action"] = None

            await update.message.reply_text(
                "✅ BALANCE ADDED\n\n"
                f"👤 User: {uid}\n"
                f"💰 Added: {amount:.2f} BDT\n"
                f"💵 New Balance: {users[uid]['balance']:.2f} BDT"
            )

        except Exception:
            await update.message.reply_text(
                "❌ Format ভুল।\n\n"
                "USER_ID | AMOUNT"
            )

        return True

    # REMOVE BALANCE
    if action == "remove_balance":

        try:
            uid, amount = text.split("|", 1)

            uid = uid.strip()
            amount = float(amount.strip())

            if uid not in users:
                await update.message.reply_text(
                    "❌ User পাওয়া যায়নি।"
                )
                return True

            users[uid]["balance"] = max(
                0,
                users[uid]["balance"] - amount
            )

            save_users()

            context.user_data["admin_action"] = None

            await update.message.reply_text(
                "✅ BALANCE REMOVED\n\n"
                f"👤 User: {uid}\n"
                f"➖ Removed: {amount:.2f} BDT\n"
                f"💵 New Balance: {users[uid]['balance']:.2f} BDT"
            )

        except Exception:
            await update.message.reply_text(
                "❌ Format ভুল।\n\n"
                "USER_ID | AMOUNT"
            )

        return True

    return False


# =========================================================
# TEXT HANDLER
# =========================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Admin action first
    if update.effective_user.id == ADMIN_ID:

        processed = await process_admin_action(
            update,
            context
        )

        if processed:
            return

    # Withdraw amount
    if context.user_data.get("withdraw_state"):

        processed = await process_withdraw(
            update,
            context
        )

        if processed:
            return

    # Payment method
    if context.user_data.get("payment_state"):

        processed = await process_payment(
            update,
            context
        )

        if processed:
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
            "❓ Please select an option from the menu.",
            reply_markup=main_keyboard()
        )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(update, context):

    logging.error(
        "Exception while handling update:",
        exc_info=context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        print("ERROR: BOT_TOKEN সেট করুন।")
        return

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Commands
    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("admin", admin_command)
    )

    # Callbacks
    application.add_handler(
        CallbackQueryHandler(
            task_callback,
            pattern=r"^task_"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^admin_"
        )
    )

    # Messages
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    application.add_error_handler(error_handler)

    print("Bot is running...")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
