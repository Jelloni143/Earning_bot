import telebot
import sqlite3
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ===== CONFIG =====
BOT_TOKEN = "YOUR_BOT_TOKEN"         # render environment variable me daalna better
ADMIN_ID = 7136139393
CHANNEL_USERNAME = "@YOUR_CHANNEL_USERNAME"

bot = telebot.TeleBot(BOT_TOKEN)

# ===== DATABASE =====
db = sqlite3.connect("earning_bot.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    referred_by INTEGER,
    upi TEXT
)
""")
db.commit()

# ===== JOIN CHECK =====
def is_joined(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ["member", "administrator", "creator"]
    except:
        return False

def join_channel_msg(chat_id):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"),
        InlineKeyboardButton("✅ Joined", callback_data="check_join")
    )
    bot.send_message(
        chat_id,
        "🚫 Access locked\n\n"
        "Earning start karne ke liye\npehle channel join karo 👇",
        reply_markup=kb
    )

# ===== START =====
@bot.message_handler(commands=['start'])
def start(msg):
    user_id = msg.from_user.id

    # channel join check
    if not is_joined(user_id):
        join_channel_msg(user_id)
        return

    # referral logic
    ref = msg.text.split()[1] if len(msg.text.split()) > 1 else None

    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (user_id, referred_by) VALUES (?,?)",
            (user_id, ref)
        )
        if ref and ref.isdigit():
            cur.execute(
                "UPDATE users SET balance = balance + 15 WHERE user_id=?",
                (int(ref),)
            )
        db.commit()

    bot.send_message(
        user_id,
        "🔥 Welcome to Earning Bot\n\n"
        "💸 ₹15 per referral\n"
        "💰 Minimum withdraw ₹15\n\n"
        "Commands:\n"
        "/balance - Check Balance\n"
        "/refer   - Get Referral Link\n"
        "/addupi  - Add UPI\n"
        "/withdraw- Request Withdraw"
    )

# ===== CALLBACK =====
@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join(call):
    if is_joined(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Access granted")
        bot.send_message(call.from_user.id, "🎉 Channel joined successfully!\nUse /start again")
    else:
        bot.answer_callback_query(call.id, "❌ Pehle channel join karo", show_alert=True)

# ===== BALANCE =====
@bot.message_handler(commands=['balance'])
def balance(msg):
    cur.execute("SELECT balance FROM users WHERE user_id=?", (msg.from_user.id,))
    bal = cur.fetchone()[0]
    bot.reply_to(msg, f"💰 Your balance: ₹{bal}")

# ===== REFER =====
@bot.message_handler(commands=['refer'])
def refer(msg):
    bot.reply_to(
        msg,
        f"👥 Your referral link:\nhttps://t.me/YOUR_BOT_USERNAME?start={msg.from_user.id}"
    )

# ===== ADD UPI =====
@bot.message_handler(commands=['addupi'])
def addupi(msg):
    bot.reply_to(msg, "✍️ Send your UPI ID")

    @bot.message_handler(func=lambda m: True)
    def save_upi(m):
        cur.execute("UPDATE users SET upi=? WHERE user_id=?", (m.text, m.from_user.id))
        db.commit()
        bot.reply_to(m, "✅ UPI added successfully")

# ===== WITHDRAW =====
@bot.message_handler(commands=['withdraw'])
def withdraw(msg):
    cur.execute("SELECT balance, upi FROM users WHERE user_id=?", (msg.from_user.id,))
    data = cur.fetchone()

    if not data:
        bot.reply_to(msg, "❌ User not found")
        return

    bal, upi = data

    if bal < 15:
        bot.reply_to(msg, "❌ Minimum withdraw ₹15 required")
        return

    if not upi:
        bot.reply_to(msg, "⚠️ Pehle /addupi se UPI add karo")
        return

    bot.send_message(
        ADMIN_ID,
        f"💸 Withdraw request\n\n"
        f"User ID: {msg.from_user.id}\n"
        f"Amount: ₹{bal}\n"
        f"UPI: {upi}"
    )

    bot.reply_to(msg, "✅ Withdraw request sent\nWait for admin approval")

# ===== RUN =====
print("🔥 Bot running...")
bot.infinity_polling()
