from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8393226821:AAEo7R3zzFRXXouml6F0fAcIWi7vVcOzt64"

keyboard = [
    ["💸 Balance💸", "💰 Tasks💰"],
    ["📤 Withdraw📤", "👤 Profile👤"],
    ["🏆 Top🏆"],
    ["👥 My Referrals", "🌍 Language"]
]

reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome!",
        reply_markup=reply_markup
    )

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))

print("Bot Started...")
app.run_polling()
