import telebot
import sqlite3
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)  # parse_mode None for stability

# database setup
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

# channel join check
def is_joined(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ["member","administrator","creator"]
    except:
        return False

def join_channel_msg(chat_id):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"),
        InlineKeyboardButton("✅ Joined", callback_data="check_join")
    )
    bot.send_message(chat_id, "🚫 Access locked\nJoin channel first 👇", reply_markup=kb)

# start command
@bot.message_handler(commands=['start'])
def start(msg):
    user_id = msg.from_user.id
    if not is_joined(user_id):
        join_channel_msg(user_id)
        return
    ref = msg.text.split()[1] if len(msg.text.split())>1 else None
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO users(user_id,referred_by) VALUES(?,?)",(user_id,ref))
        if ref and ref.isdigit():
            cur.execute("UPDATE users SET balance = balance + 15 WHERE user_id=?",(int(ref),))
        db.commit()
    bot.send_message(user_id, "🔥 Welcome\n💸 ₹15/referral\n💰 Min withdraw ₹15\nCommands: /balance /refer /addupi /withdraw")

@bot.callback_query_handler(func=lambda c:c.data=="check_join")
def check_join(c):
    if is_joined(c.from_user.id):
        bot.answer_callback_query(c.id,"✅ Access granted")
        bot.send_message(c.from_user.id,"🎉 Channel joined successfully!\nUse /start again")
    else:
        bot.answer_callback_query(c.id,"❌ Join channel first",show_alert=True)

@bot.message_handler(commands=['balance'])
def balance(msg):
    cur.execute("SELECT balance FROM users WHERE user_id=?",(msg.from_user.id,))
    bal = cur.fetchone()[0]
    bot.reply_to(msg,f"💰 Balance: ₹{bal}")

@bot.message_handler(commands=['refer'])
def refer(msg):
    bot.reply_to(msg,f"👥 Referral link:\nhttps://t.me/YOUR_BOT_USERNAME?start={msg.from_user.id}")

@bot.message_handler(commands=['addupi'])
def addupi(msg):
    bot.reply_to(msg,"✍️ Send your UPI ID")
    @bot.message_handler(func=lambda m: True)
    def save_upi(m):
        cur.execute("UPDATE users SET upi=? WHERE user_id=?",(m.text,m.from_user.id))
        db.commit()
        bot.reply_to(m,"✅ UPI added successfully")

@bot.message_handler(commands=['withdraw'])
def withdraw(msg):
    cur.execute("SELECT balance,upi FROM users WHERE user_id=?",(msg.from_user.id,))
    data = cur.fetchone()
    if not data: return bot.reply_to(msg,"❌ User not found")
    bal,upi = data
    if bal<15: return bot.reply_to(msg,"❌ Minimum withdraw ₹15 required")
    if not upi: return bot.reply_to(msg,"⚠️ Add /addupi first")
    bot.send_message(ADMIN_ID,f"💸 Withdraw request\nUser ID: {msg.from_user.id}\nAmount: ₹{bal}\nUPI: {upi}")
    bot.reply_to(msg,"✅ Withdraw request sent, wait for admin approval")

print("🔥 Bot running...")
bot.infinity_polling()
