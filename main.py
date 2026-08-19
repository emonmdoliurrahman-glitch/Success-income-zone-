টাস্ক এডমিন
import telebot
from telebot import types
import json
import os

TOKEN = "8393226821:AAHmspHI9QwHZzyh81WGg14uz3C7GrBxH9g"

# =========================
# ADMIN ID
# =========================

ADMIN_ID = 7764329763

REFERRAL_PERCENT = 0.20

bot = telebot.TeleBot(TOKEN)

USERS_FILE = "users.json"
TASKS_FILE = "tasks.json"
SUBMISSIONS_FILE = "submissions.json"


# =========================
# JSON FUNCTIONS
# =========================

def load_json(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default

    return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


users = load_json(USERS_FILE, {})
tasks = load_json(TASKS_FILE, {})
submissions = load_json(SUBMISSIONS_FILE, {})


# =========================
# USER
# =========================

def get_user(user_id):

    user_id = str(user_id)

    if user_id not in users:

        users[user_id] = {
            "balance": 0.0,
            "referrals": 0,
            "referred_by": None,
            "referral_earnings": 0.0
        }

        save_json(USERS_FILE, users)

    else:

        users[user_id].setdefault("balance", 0.0)
        users[user_id].setdefault("referrals", 0)
        users[user_id].setdefault("referred_by", None)
        users[user_id].setdefault("referral_earnings", 0.0)

    return users[user_id]


# =========================
# ADD EARNING
# =========================

def add_earning(user_id, amount):

    user_id = str(user_id)

    user = get_user(user_id)

    # Member earning
    user["balance"] += amount

    # Referrer
    referrer_id = user.get("referred_by")

    if referrer_id:

        referrer_id = str(referrer_id)

        if referrer_id in users:

            commission = amount * REFERRAL_PERCENT

            users[referrer_id]["balance"] += commission

            users[referrer_id]["referral_earnings"] += commission

    save_json(USERS_FILE, users)


# =========================
# START
# =========================

@bot.message_handler(commands=["start"])
def start(message):

    user_id = str(message.from_user.id)

    user = get_user(user_id)

    parts = message.text.split()

    # Referral
    if len(parts) > 1:

        try:

            referrer_id = str(int(parts[1]))

            if referrer_id != user_id:

                if user.get("referred_by") is None:

                    if referrer_id in users:

                        user["referred_by"] = referrer_id

                        users[referrer_id]["referrals"] += 1

                        save_json(USERS_FILE, users)

                        try:

                            bot.send_message(
                                int(referrer_id),
                                "🎉 New Referral!\n\n"
                                "👤 Someone joined using your referral link."
                            )

                        except:
                            pass

        except ValueError:
            pass


    # Menu
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    btn1 = types.KeyboardButton("💸 Balance")
    btn2 = types.KeyboardButton("💰 Tasks")
    btn3 = types.KeyboardButton("📤 Withdraw")
    btn4 = types.KeyboardButton("👤 Profile")
    btn5 = types.KeyboardButton("🏆 Top")
    btn6 = types.KeyboardButton("🫂 My Referrals")
    btn7 = types.KeyboardButton("🌏 Language")

    markup.row(btn1, btn2)
    markup.row(btn3, btn4)
    markup.row(btn5)
    markup.row(btn6, btn7)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to Success Income Zone!",
        reply_markup=markup
    )


# ==================================================
# ADMIN - ADD TASK
# ==================================================

@bot.message_handler(commands=["addtask"])
def add_task(message):

    if message.from_user.id != ADMIN_ID:

        bot.reply_to(
            message,
            "❌ You are not authorized."
        )

        return

    text = message.text.replace("/addtask", "", 1).strip()

    parts = text.split("|")

    if len(parts) != 3:

        bot.reply_to(
            message,
            "❌ ভুল format!\n\n"
            "এভাবে লিখুন:\n\n"
            "/addtask Task Name | Task Link | Reward\n\n"
            "উদাহরণ:\n"
            "/addtask Join Channel | https://t.me/example | 0.50"
        )

        return

    title = parts[0].strip()
    link = parts[1].strip()

    try:
        reward = float(parts[2].strip())

    except ValueError:

        bot.reply_to(
            message,
            "❌ Reward অবশ্যই number হতে হবে।"
        )

        return

    task_id = str(len(tasks) + 1)

    while task_id in tasks:

        task_id = str(int(task_id) + 1)

    tasks[task_id] = {

        "title": title,
        "link": link,
        "reward": reward,
        "active": True

    }

    save_json(TASKS_FILE, tasks)

    bot.reply_to(
        message,
        f"✅ Task Added!\n\n"
        f"🆔 Task ID: {task_id}\n"
        f"📌 {title}\n"
        f"💵 Reward: ${reward:.2f}"
    )


# ==================================================
# ADMIN - TASK LIST
# ==================================================

@bot.message_handler(commands=["tasks"])
def admin_tasks(message):

    if message.from_user.id != ADMIN_ID:

        bot.reply_to(
            message,
            "❌ You are not authorized."
        )

        return

    if not tasks:

        bot.reply_to(
            message,
            "📋 No tasks available."
        )

        return

    text = "📋 TASK LIST\n\n"

    for task_id, task in tasks.items():

        status = "🟢 Active" if task["active"] else "🔴 Disabled"

        text += (
            f"🆔 {task_id}\n"
            f"📌 {task['title']}\n"
            f"💵 ${task['reward']:.2f}\n"
            f"{status}\n\n"
        )

    bot.reply_to(message, text)


# ==================================================
# ADMIN - DELETE TASK
# ==================================================

@bot.message_handler(commands=["deltask"])
def delete_task(message):

    if message.from_user.id != ADMIN_ID:

        bot.reply_to(
            message,
            "❌ You are not authorized."
        )

        return

    task_id = message.text.replace("/deltask", "", 1).strip()

    if task_id not in tasks:

        bot.reply_to(
            message,
            "❌ Task ID পাওয়া যায়নি।"
        )

        return

    title = tasks[task_id]["title"]

    del tasks[task_id]

    save_json(TASKS_FILE, tasks)

    bot.reply_to(
        message,
        f"🗑️ Task deleted!\n\n"
        f"📌 {title}"
    )


# ==================================================
# ADMIN - DISABLE TASK
# ==================================================

@bot.message_handler(commands=["disabletask"])
def disable_task(message):

    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ You are not authorized.")
        return

    task_id = message.text.replace("/disabletask", "", 1).strip()

    if task_id not in tasks:
        bot.reply_to(message, "❌ Task ID পাওয়া যায়নি।")
        return

    tasks[task_id]["active"] = False

    save_json(TASKS_FILE, tasks)

    bot.reply_to(
        message,
        f"🔴 Task {task_id} disabled."
    )


# ==================================================
# ADMIN - ENABLE TASK
# ==================================================

@bot.message_handler(commands=["enabletask"])
def enable_task(message):

    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ You are not authorized.")
        return

    task_id = message.text.replace("/enabletask", "", 1).strip()

    if task_id not in tasks:
        bot.reply_to(message, "❌ Task ID পাওয়া যায়নি।")
        return

    tasks[task_id]["active"] = True

    save_json(TASKS_FILE, tasks)

    bot.reply_to(
        message,
        f"🟢 Task {task_id} enabled."
    )


# ==================================================
# ADMIN - PENDING
# ==================================================

@bot.message_handler(commands=["pending"])
def pending(message):

    if message.from_user.id != ADMIN_ID:

        bot.reply_to(
            message,
            "❌ You are not authorized."
        )

        return

    found = False

    for submission_id, submission in submissions.items():

        if submission["status"] == "pending":

            found = True

            markup = types.InlineKeyboardMarkup()

            approve = types.InlineKeyboardButton(
                "✅ Approve",
                callback_data=f"approve_{submission_id}"
            )

            reject = types.InlineKeyboardButton(
                "❌ Reject",
                callback_data=f"reject_{submission_id}"
            )

            markup.row(approve, reject)

            bot.send_message(
                message.chat.id,

                f"⏳ PENDING TASK\n\n"
                f"Submission ID: {submission_id}\n"
                f"User ID: {submission['user_id']}\n"
                f"Task: {submission['task_title']}\n"
                f"Reward: ${submission['reward']:.2f}\n\n"
                f"Proof:\n"
                f"{submission['proof']}",

                reply_markup=markup
            )

    if not found:

        bot.reply_to(
            message,
            "✅ No pending submissions."
        )


# ==================================================
# APPROVE / REJECT
# ==================================================

@bot.callback_query_handler(
    func=lambda call:
    call.data.startswith("approve_")
    or call.data.startswith("reject_")
)
def review_submission(call):

    if call.from_user.id != ADMIN_ID:

        bot.answer_callback_query(
            call.id,
            "❌ Not authorized."
        )

        return

    action, submission_id = call.data.split("_", 1)

    if submission_id not in submissions:

        bot.answer_callback_query(
            call.id,
            "Submission not found."
        )

        return

    submission = submissions[submission_id]

    if submission["status"] != "pending":

        bot.answer_callback_query(
            call.id,
            "Already reviewed."
        )

        return

    user_id = submission["user_id"]

    reward = submission["reward"]

    if action == "approve":

        add_earning(user_id, reward)

        submission["status"] = "approved"

        save_json(
            SUBMISSIONS_FILE,
            submissions
        )

        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )

        bot.send_message(
            int(user_id),

            f"🎉 Task Approved!\n\n"
            f"💰 You earned: ${reward:.2f}\n"
            f"💸 Your balance has been updated."
        )

        bot.answer_callback_query(
            call.id,
            "✅ Approved"
        )

    else:

        submission["status"] = "rejected"

        save_json(
            SUBMISSIONS_FILE,
            submissions
        )

        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )

        bot.send_message(
            int(user_id),

            "❌ Task Rejected.\n\n"
            "Your submission was not approved."
        )

        bot.answer_callback_query(
            call.id,
            "❌ Rejected"
        )


# ==================================================
# MEMBER TASKS
# ==================================================

def show_tasks(message):

    user_id = str(message.from_user.id)

    active_tasks = []

    for task_id, task in tasks.items():

        if task["active"]:

            active_tasks.append(
                (task_id, task)
            )

    if not active_tasks:

        bot.send_message(
            message.chat.id,
            "💰 No tasks available right now."
        )

        return

    for task_id, task in active_tasks:

        # Already submitted?
        already_done = False

        for submission in submissions.values():

            if (
                submission["user_id"] == user_id
                and submission["task_id"] == task_id
                and submission["status"]
                in ["pending", "approved"]
            ):

                already_done = True
                break

        if already_done:

            continue

        markup = types.InlineKeyboardMarkup()

        open_button = types.InlineKeyboardButton(
            "🔗 Open Task",
            url=task["link"]
        )

        complete_button = types.InlineKeyboardButton(
            "✅ Submit Task",
            callback_data=f"submit_{task_id}"
        )

        markup.row(open_button)
        markup.row(complete_button)

        bot.send_message(
            message.chat.id,

            f"💰 Task\n\n"
            f"📌 {task['title']}\n"
            f"💵 Reward: ${task['reward']:.2f}\n\n"
            f"Task সম্পন্ন করার পর Submit চাপুন।",

            reply_markup=markup
        )


# ==================================================
# MEMBER SUBMIT
# ==================================================

@bot.callback_query_handler(
    func=lambda call:
    call.data.startswith("submit_")
)
def submit_task(call):

    user_id = str(call.from_user.id)

    task_id = call.data.replace(
        "submit_",
        "",
        1
    )

    if task_id not in tasks:

        bot.answer_callback_query(
            call.id,
            "Task not found."
        )

        return

    task = tasks[task_id]

    if not task["active"]:

        bot.answer_callback_query(
            call.id,
            "Task is disabled."
        )

        return

    # Already submitted
    for submission in submissions.values():

        if (
            submission["user_id"] == user_id
            and submission["task_id"] == task_id
            and submission["status"]
            in ["pending", "approved"]
        ):

            bot.answer_callback_query(
                call.id,
                "Already submitted."
            )

            return

    # Ask proof
    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "📸 Task-এর প্রমাণ পাঠান।\n\n"
        "Screenshot অথবা প্রয়োজনীয় proof পাঠাতে পারেন।"
    )

    bot.register_next_step_handler(
        msg,
        receive_proof,
        task_id
    )


# ==================================================
# RECEIVE PROOF
# ==================================================

def receive_proof(message, task_id):

    user_id = str(message.from_user.id)

    if task_id not in tasks:

        bot.sen
        print("SUCCESS INCOME ZONE BOT STARTING...")

while True:
    try:
        bot.infinity_polling(
            timeout=60,
            long_polling_timeout=60
        )
    except Exception as e:
        print("BOT ERROR:", e)
        time.sleep(5)
