
# Telegram Stars Shop Bot
# Reads token from config.txt (first line)
# Features:
# - Services (add/del/list) by owner
# - Orders table, buy using "stars balance" (owner credits users after receiving Stars via Telegram)
# - Auto/manual activation: services can be set auto->1 to auto-activate via placeholder function
# - VIP roles
# - Admin panel and simple inline UI
#
# Notes:
# - THIS BOT DOES NOT PERFORM REAL TELEGRAM "Stars" PAYMENTS AUTOMATICALLY.
#   To accept real payments using Telegram Payments, supply a provider token and implement payment handlers.
# - Owner must be set in config_owner.txt or hardcoded below.
#
import logging, sqlite3, time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters

# Read token (first line of config.txt)
with open("config.txt", "r") as f:
    TOKEN = f.read().strip()

# Owner username (without @). Change if needed.
OWNER_USERNAME = "giks_ff"
CHANNEL_LINK = "https://t.me/giksxit"
PROFILE_PIC = "/mnt/data/65CB154A-43B2-4D4A-BFA4-6932C034BF97.jpeg"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

conn = sqlite3.connect("shop.db", check_same_thread=False)
cur = conn.cursor()

# Tables: users, services, orders, vip
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    stars INTEGER DEFAULT 0,
    vip_until INTEGER DEFAULT 0
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT,
    price INTEGER,
    auto INTEGER DEFAULT 0
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    service_id INTEGER,
    qty INTEGER,
    price INTEGER,
    status TEXT,
    created INTEGER
)
""")
conn.commit()

def is_owner(update: Update):
    u = update.effective_user
    if not u:
        return False
    return (u.username and u.username.lower() == OWNER_USERNAME.lower()) or u.id == int(u.id)

def get_user(uid, username=None):
    cur.execute("SELECT id, username, stars, vip_until FROM users WHERE id = ?", (uid,))
    row = cur.fetchone()
    if row:
        return {"id": row[0], "username": row[1], "stars": row[2], "vip_until": row[3]}
    cur.execute("INSERT INTO users (id, username, stars) VALUES (?, ?, ?)", (uid, username, 0))
    conn.commit()
    return {"id": uid, "username": username, "stars": 0, "vip_until": 0}

# Admin commands
def add_service(update: Update, context: CallbackContext):
    if not is_owner(update):
        update.message.reply_text("غير للمالك.")
        return
    text = " ".join(context.args)
    parts = text.split("|")
    if len(parts) < 3:
        update.message.reply_text("استعمل: /addservice اسم | وصف | سعر | [auto:0/1]\nمثال: /addservice رفع أعضاء | 100 عضو زيادة | 50 | 1")
        return
    name = parts[0].strip()
    desc = parts[1].strip()
    price = int(parts[2].strip())
    auto = int(parts[3].strip()) if len(parts) >=4 else 0
    cur.execute("INSERT INTO services (name, description, price, auto) VALUES (?, ?, ?, ?)", (name, desc, price, auto))
    conn.commit()
    update.message.reply_text("تم إضافة الخدمة.")

def del_service(update: Update, context: CallbackContext):
    if not is_owner(update):
        update.message.reply_text("غير للمالك.")
        return
    if not context.args:
        update.message.reply_text("استعمل: /delservice <service_id>")
        return
    sid = int(context.args[0])
    cur.execute("DELETE FROM services WHERE id = ?", (sid,))
    conn.commit()
    update.message.reply_text("تم الحذف إن شاء الله.")

def list_services(update: Update, context: CallbackContext):
    cur.execute("SELECT id, name, description, price, auto FROM services ORDER BY id")
    rows = cur.fetchall()
    if not rows:
        update.message.reply_text("لا توجد خدمات بعد.")
        return
    msgs = []
    for r in rows:
        msgs.append(f"ID:{r[0]} • {r[1]}\n{r[2]}\nسعر: {r[3]} ⭐ • auto: {r[4]}")
    update.message.reply_text("\n\n".join(msgs))

def buy(update: Update, context: CallbackContext):
    user = update.effective_user
    uid = user.id
    username = user.username or user.full_name
    get_user(uid, username)
    if not context.args:
        update.message.reply_text("استعمل: /buy <service_id> [quantity]")
        return
    sid = int(context.args[0])
    qty = int(context.args[1]) if len(context.args) >1 else 1
    cur.execute("SELECT price, name, auto FROM services WHERE id = ?", (sid,))
    row = cur.fetchone()
    if not row:
        update.message.reply_text("خدمة غير موجودة.")
        return
    price, name, auto = row
    total = price * qty
    cur.execute("SELECT stars FROM users WHERE id = ?", (uid,))
    stars = cur.fetchone()[0]
    if stars < total:
        update.message.reply_text(f"رصيدك قليل. تحتاج {total} ⭐، رصيدك: {stars} ⭐\nاستعمل /topup لطلب تزويد بالنجوم.")
        return
    # create order
    cur.execute("INSERT INTO orders (user_id, service_id, qty, price, status, created) VALUES (?, ?, ?, ?, ?, ?)",
                (uid, sid, qty, total, "pending", int(time.time())))
    conn.commit()
    oid = cur.lastrowid
    # deduct stars
    cur.execute("UPDATE users SET stars = stars - ? WHERE id = ?", (total, uid))
    conn.commit()
    update.message.reply_text(f"تم إنشاء الطلب #{oid} لخدمة {name} • المبلغ: {total} ⭐\nحالة: pending")
    # auto-activate if service.auto ==1
    if auto:
        activate_order(oid, update, context)

def activate_order(order_id, update: Update, context: CallbackContext):
    # Placeholder auto-activation logic. Customize to call your service APIs.
    cur.execute("SELECT user_id, service_id, qty FROM orders WHERE id = ?", (order_id,))
    r = cur.fetchone()
    if not r:
        return
    user_id, service_id, qty = r
    cur.execute("SELECT name FROM services WHERE id = ?", (service_id,))
    name = cur.fetchone()[0]
    # mark as completed
    cur.execute("UPDATE orders SET status = ? WHERE id = ?", ("completed", order_id))
    conn.commit()
    try:
        context.bot.send_message(chat_id=user_id, text=f"✅ تم تفعيل طلبك #{order_id} - {name} x{qty}")
    except Exception:
        pass

def orders_cmd(update: Update, context: CallbackContext):
    if not is_owner(update):
        update.message.reply_text("غير للمالك.")
        return
    cur.execute("SELECT id, user_id, service_id, qty, price, status, created FROM orders ORDER BY id DESC LIMIT 50")
    rows = cur.fetchall()
    if not rows:
        update.message.reply_text("لا توجد طلبات بعد.")
        return
    msgs = []
    for r in rows:
        msgs.append(f"#{r[0]} • user:{r[1]} • service:{r[2]} • qty:{r[3]} • price:{r[4]} • status:{r[5]}")
    update.message.reply_text("\n".join(msgs))

def fulfill(update: Update, context: CallbackContext):
    if not is_owner(update):
        update.message.reply_text("غير للمالك.")
        return
    if not context.args:
        update.message.reply_text("استعمل: /fulfill <order_id>")
        return
    oid = int(context.args[0])
    cur.execute("SELECT status, user_id, service_id, qty FROM orders WHERE id = ?", (oid,))
    row = cur.fetchone()
    if not row:
        update.message.reply_text("طلب مش موجود.")
        return
    status, user_id, service_id, qty = row
    if status == "completed":
        update.message.reply_text("مكمل من قبل.")
        return
    # mark completed
    cur.execute("UPDATE orders SET status = ? WHERE id = ?", ("completed", oid))
    conn.commit()
    # notify user
    try:
        context.bot.send_message(chat_id=user_id, text=f"✅ طلبك #{oid} تم تفعيله يدوياً.")
    except Exception:
        pass
    update.message.reply_text("تم التفعيل.")

def topup_request(update: Update, context: CallbackContext):
    # User requests top-up (they will pay Stars externally and you credit)
    user = update.effective_user
    uid = user.id
    update.message.reply_text("باش تزود النجوم، صيفط لمالك البوت إثبات الدفع واطلب منه /credit @username amount")
    # optional: notify owner
    try:
        context.bot.send_message(chat_id=f"@{OWNER_USERNAME}", text=f"Topup request from @{user.username} (id:{uid})")
    except Exception:
        pass

def credit_cmd(update: Update, context: CallbackContext):
    # Owner credits stars to a user: /credit @username amount
    if not is_owner(update):
        update.message.reply_text("غير للمالك.")
        return
    if len(context.args) < 2:
        update.message.reply_text("استعمل: /credit @username amount")
        return
    username = context.args[0]
    if username.startswith("@"):
        username = username[1:]
    amount = int(context.args[1])
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if not row:
        update.message.reply_text("هاد المستخدم ما تواصلش مع البوت.")
        return
    uid = row[0]
    cur.execute("UPDATE users SET stars = stars + ? WHERE id = ?", (amount, uid))
    conn.commit()
    update.message.reply_text("تمت الاضافة.")
    try:
        context.bot.send_message(chat_id=uid, text=f"🔔 تمت إضافة {amount} ⭐ لرصيدك من طرف المالك.")
    except Exception:
        pass

def my_balance(update: Update, context: CallbackContext):
    user = update.effective_user
    uid = user.id
    u = get_user(uid, user.username or user.full_name)
    update.message.reply_text(f"رصيدك: {u['stars']} ⭐\nVIP حتى: {datetime.fromtimestamp(u['vip_until']).strftime('%Y-%m-%d') if u['vip_until'] else 'لا'}")

def vip_add(update: Update, context: CallbackContext):
    if not is_owner(update):
        update.message.reply_text("غير للمالك.")
        return
    if len(context.args) < 2:
        update.message.reply_text("استعمل: /vip_add @username days")
        return
    username = context.args[0].lstrip("@")
    days = int(context.args[1])
    cur.execute("SELECT id, vip_until FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if not row:
        update.message.reply_text("المستخدم لم يستعمل البوت بعد.")
        return
    uid, vip_until = row
    now = int(time.time())
    new_until = max(vip_until, now) + days*24*3600
    cur.execute("UPDATE users SET vip_until = ? WHERE id = ?", (new_until, uid))
    conn.commit()
    update.message.reply_text("تمت اضافة VIP.")

def start_cmd(update: Update, context: CallbackContext):
    user = update.effective_user
    uid = user.id
    username = user.username or user.full_name
    get_user(uid, username)
    kb = [
        [InlineKeyboardButton("🛒 المتجر", callback_data="shop")],
        [InlineKeyboardButton("💰 رصيدي", callback_data="balance"),
         InlineKeyboardButton("🎫 طلب تعبئة", callback_data="topup")],
        [InlineKeyboardButton("🔧 معلومات", callback_data="info"),
         InlineKeyboardButton("📣 قناة المالك", url=CHANNEL_LINK)]
    ]
    update.message.reply_text(f"أهلا {username}!\nبوت متجر نجوم تيليجرام ⭐", reply_markup=InlineKeyboardMarkup(kb))

def callback_q(update: Update, context: CallbackContext):
    q = update.callback_query
    data = q.data
    if data == "shop":
        cur.execute("SELECT id, name, price FROM services ORDER BY id")
        rows = cur.fetchall()
        if not rows:
            q.answer("لا توجد خدمات")
            q.edit_message_text("لا توجد خدمات حاليا.")
            return
        text = "📦 المتجر:\n"
        for r in rows:
            text += f"ID:{r[0]} • {r[1]} • {r[2]} ⭐\n"
        text += "\nاستعمل: /buy <ID> [qty]"
        q.edit_message_text(text)
    elif data == "balance":
        user = q.from_user
        u = get_user(user.id, user.username or user.full_name)
        q.edit_message_text(f"رصيدك: {u['stars']} ⭐")
    elif data == "topup":
        q.edit_message_text("اطلب تعبئة عبر /topup وابعث إثبات الدفع للمالك.")
    elif data == "info":
        q.edit_message_text("بوت متجر نجوم. تواصل مع المالك لإتمام الدفعات.")

def unknown(update: Update, context: CallbackContext):
    update.message.reply_text("أمر غير معروف. استعمل /help")

def help_cmd(update: Update, context: CallbackContext):
    update.message.reply_text("/start\n/listservices\n/buy <id>\n/mybalance\n/topup\n\nالمالـك: /addservice /delservice /orders /fulfill /credit /vip_add")

def set_profile_picture(bot):
    try:
        with open(PROFILE_PIC, "rb") as f:
            bot.set_chat_photo(chat_id=bot.get_me().id, photo=f)
    except Exception:
        pass

def main():
    updater = Updater(TOKEN, use_context=True)
    bot = updater.bot
    set_profile_picture(bot)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start_cmd))
    dp.add_handler(CommandHandler("addservice", add_service))
    dp.add_handler(CommandHandler("delservice", del_service))
    dp.add_handler(CommandHandler("listservices", list_services))
    dp.add_handler(CommandHandler("buy", buy))
    dp.add_handler(CommandHandler("orders", orders_cmd))
    dp.add_handler(CommandHandler("fulfill", fulfill))
    dp.add_handler(CommandHandler("topup", topup_request))
    dp.add_handler(CommandHandler("credit", credit_cmd))
    dp.add_handler(CommandHandler("mybalance", my_balance))
    dp.add_handler(CommandHandler("vip_add", vip_add))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CallbackQueryHandler(callback_q))
    dp.add_handler(MessageHandler(Filters.command, unknown))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
