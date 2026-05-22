import os
import json
import requests
import random
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler, CallbackQueryHandler
from telegram.constants import ParseMode

TOKEN = os.getenv('BOT_TOKEN')
XAI_API_KEY = os.getenv('XAI_API_KEY')

DAILY_GROK_LIMIT = 15
RAID_DURATION_MINUTES = 15
RAID_BONUS_POINTS = 40

ADMINS = ["FLICKABICFLIK"]

# Data
points = {}
energy_cooldown = {}
daily_streak = {}
last_login_date = {}
grok_usage = {}
referrals = {}
current_raid = None
raid_duration_minutes = 15
missions_completed = {}
daily_activity = {}
weekly_activity = {}

def load_data():
    global points, daily_streak, last_login_date, grok_usage, referrals, current_raid, raid_duration_minutes, missions_completed, daily_activity, weekly_activity
    files = {
        'points.json': 'points',
        'daily_streak.json': 'daily_streak',
        'last_login_date.json': 'last_login_date',
        'grok_usage.json': 'grok_usage',
        'referrals.json': 'referrals',
        'current_raid.json': 'current_raid',
        'raid_settings.json': 'raid_duration_minutes',
        'missions.json': 'missions_completed',
        'daily_activity.json': 'daily_activity',
        'weekly_activity.json': 'weekly_activity'
    }
    for file, var in files.items():
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                if var == 'raid_duration_minutes':
                    globals()['raid_duration_minutes'] = data
                else:
                    globals()[var] = data
        except:
            globals()[var] = {} if var != 'current_raid' else None

def save_data():
    for file, data in [('points.json', points), ('daily_streak.json', daily_streak),
                       ('last_login_date.json', last_login_date), ('grok_usage.json', grok_usage),
                       ('referrals.json', referrals), ('missions.json', missions_completed),
                       ('daily_activity.json', daily_activity), ('weekly_activity.json', weekly_activity)]:
        with open(file, 'w') as f:
            json.dump(data, f, indent=2)
    if current_raid:
        with open('current_raid.json', 'w') as f:
            json.dump(current_raid, f, indent=2)
    with open('raid_settings.json', 'w') as f:
        json.dump(raid_duration_minutes, f)

load_data()

def is_admin(user):
    return user and user.username and user.username in ADMINS

# ====================== ANTI-SPAM ======================
async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or is_admin(update.message.from_user):
        return False

    if update.message.text:
        text = update.message.text
        lower = text.lower()

        if any(word in lower for word in ["collab", "collaboration"]):
            await update.message.delete()
            try:
                await update.message.reply_text("🚫 'Collab' or 'Collaboration' mentions are not allowed.", delete_after=10)
            except:
                pass
            return True

        is_x_link = any(domain in lower for domain in ["x.com", "twitter.com"])
        has_flik_ref = any(word in lower for word in ["flik", "$flik", "flick", "flickabic", "flickabicflik"])
        has_blocked_link = any(word in lower for word in ["http", "t.me", "tco", "telegram.me"])

        if (len(text) > 300 or
            (text.isupper() and len(text) > 50) or
            (has_blocked_link and not (is_x_link and has_flik_ref))):
            await update.message.delete()
            try:
                await update.message.reply_text("🚫 Spam detected and removed.", delete_after=10)
            except:
                pass
            return True

    if update.message.photo or update.message.sticker or update.message.animation or update.message.video:
        await update.message.delete()
        await update.message.reply_text("📸 Media sent to admins for approval.")
        return True

    return False

async def get_grok_response(query: str, username: str):
    if is_admin(type('obj', (object,), {'username': username})()):
        pass
    else:
        today = str(date.today())
        grok_usage.setdefault(username, {}).setdefault(today, 0)
        if grok_usage[username][today] >= DAILY_GROK_LIMIT:
            return f"⛔ Daily @Flik limit reached ({DAILY_GROK_LIMIT} messages). Try again tomorrow!"
        grok_usage[username][today] += 1
        save_data()

    if not XAI_API_KEY:
        return "🔥 Flik is here! Ask me anything."
    try:
        r = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"},
            json={"model": "grok-4", "messages": [{"role": "system", "content": "You are Flik — savage, hype, funny, wise leader of $FLIK."}, {"role": "user", "content": f"@{username}: {query}"}]}
        )
        return r.json()['choices'][0]['message']['content']
    except:
        return "🔥 Flik is cooking... Try again soon!"

# ====================== VERIFICATION BUTTON ON JOIN ======================
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        keyboard = [[InlineKeyboardButton("✅ I'm not a bot", callback_data="verify_human")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"🔥 Welcome @{member.username or member.first_name}!\n\n"
            "Click the button below to verify you're not a bot.",
            reply_markup=reply_markup
        )

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "verify_human":
        await query.edit_message_text(
            text="✅ **Verified!** Welcome to the $FLIK community 🔥\n+5 points added!"
        )
        username = query.from_user.username
        if username:
            points[username] = points.get(username, 0) + 5
            save_data()

# ====================== REST OF THE BOT (unchanged) ======================
# (handle_message, raid commands, active leaderboard, etc.)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if await anti_spam(update, context):
        return

    if not update.message.text:
        return

    text = update.message.text.lower()
    original = update.message.text
    user = update.message.from_user
    username = user.username
    if not username:
        return

    today_str = str(date.today())

    # Daily + Weekly activity tracking
    if username not in daily_activity:
        daily_activity[username] = {}
    daily_activity[username][today_str] = daily_activity[username].get(today_str, 0) + 1

    if username not in weekly_activity:
        weekly_activity[username] = 0
    weekly_activity[username] += 1
    save_data()

    # Daily login
    if username not in last_login_date or last_login_date[username] != today_str:
        last_login_date[username] = today_str
        streak = daily_streak.get(username, 0) + 1
        daily_streak[username] = streak
        reward = 5 if streak == 1 else 15
        points[username] = points.get(username, 0) + reward
        save_data()
        await update.message.reply_text(f"🌟 Daily login! +{reward} points | Streak: {streak}")

    # @Flik AI + smart commands
    if "@flik" in text or "@Flik" in original:
        query = original.replace("@Flik", "").replace("@flik", "").strip().lower()
        if "price" in query:
            await update.message.reply_text("📈 $FLIK is in pre-launch phase.\nPrice will appear here once listed!")
            return
        elif "meme" in query:
            theme = query.replace("meme", "").strip() or "moon"
            meme_text = random.choice([f"🚀 {theme.upper()} TO THE MOON! $FLIK", f"🔥 ONE FLICK = {theme.upper()}", f"🌕 $FLIK {theme.upper()} MISSION"])
            await update.message.reply_text(f"🖼 **MEME GENERATED**\n\n{meme_text}")
            return
        elif "referral" in query or "myreferral" in query:
            bot_info = await context.bot.get_me()
            link = f"https://t.me/{bot_info.username}?start={username}"
            await update.message.reply_text(f"🔥 **Your Referral Link**\n🔗 {link}")
            return
        elif "leaderboard" in query or "active" in query or "mostactive" in query:
            await active_leaderboard(update, context)
            return
        elif "poll" in query:
            await createpoll(update, context)
            return
        response = await get_grok_response(query, username)
        await update.message.reply_text(response)
        return

    # Energy system
    if any(w in text for w in ["flick", "flik", "moon", "fire", "send it", "light it", "bic"]):
        last = energy_cooldown.get(username, 0)
        now = datetime.now().timestamp()
        if now - last > 60:
            energy_cooldown[username] = now
            points[username] = points.get(username, 0) + 1
            save_data()
            await update.message.reply_text("🔥 THAT'S THE ENERGY! $FLIK TO THE MOON")
        else:
            await update.message.reply_text(f"⏳ Cooldown {int(60 - (now - last))}s left.")
        return

    # Auto-replies
    if "x" in text or "twitter" in text:
        await update.message.reply_text("🔥 Official X: https://x.com/FLICKABICFLIK")
    if "website" in text or "site" in text:
        await update.message.reply_text("🔥 Official Website: https://flickabic.com")

# ====================== DAILY + WEEKLY MOST ACTIVE LEADERBOARD ======================
async def active_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today_str = str(date.today())
    today_counts = {}
    for user, dates in daily_activity.items():
        if today_str in dates:
            today_counts[user] = dates[today_str]

    weekly_counts = weekly_activity.copy()

    msg = "🏆 **MOST ACTIVE LEADERBOARD**\n\n**📅 TODAY**\n"
    if today_counts:
        sorted_today = sorted(today_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for i, (u, c) in enumerate(sorted_today, 1):
            msg += f"{i}. @{u} — {c} messages\n"
    else:
        msg += "No activity yet today.\n"

    msg += "\n**📅 THIS WEEK**\n"
    if weekly_counts:
        sorted_week = sorted(weekly_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for i, (u, c) in enumerate(sorted_week, 1):
            msg += f"{i}. @{u} — {c} messages\n"
    else:
        msg += "No weekly activity yet.\n"

    await update.message.reply_text(msg)

# ====================== RAID COMMANDS ======================
async def startraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user):
        await update.message.reply_text("Admin only 🔥")
        return
    global current_raid
    if current_raid:
        await update.message.reply_text("Raid already active!")
        return
    current_raid = {"participants": []}
    save_data()
    context.job_queue.run_once(auto_end_raid, raid_duration_minutes * 60, chat_id=update.message.chat_id, name="raid_end")
    await update.message.reply_text(f"🚨 **RAID STARTED!** 🚨\nDuration: {raid_duration_minutes} min\n`/joinraid` to join!")

async def endraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user):
        await update.message.reply_text("Admin only 🔥")
        return
    global current_raid
    if not current_raid:
        await update.message.reply_text("No active raid.")
        return
    await auto_end_raid(context)

async def auto_end_raid(context: ContextTypes.DEFAULT_TYPE):
    global current_raid
    if not current_raid:
        return
    participants = current_raid.get("participants", [])
    for user in participants:
        points[user] = points.get(user, 0) + 20
    save_data()
    msg = f"🏁 **RAID ENDED** 🏁\nTotal raiders: **{len(participants)}**\n**+20 points** awarded to every raider! 🔥\n\nGreat job everyone! $FLIK to the moon!"
    await context.bot.send_message(chat_id=context.job.chat_id, text=msg)
    current_raid = None
    save_data()

async def joinraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_raid
    if not current_raid:
        await update.message.reply_text("No active raid.")
        return
    user = update.message.from_user.username
    if user and user not in current_raid.get("participants", []):
        current_raid.setdefault("participants", []).append(user)
        points[user] = points.get(user, 0) + 10
        save_data()
        await update.message.reply_text(f"🔥 @{user} joined the raid! **+10 points**")
    else:
        await update.message.reply_text("Already in raid 🔥")

async def raidstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_raid
    if not current_raid:
        await update.message.reply_text("No active raid.")
        return
    await update.message.reply_text(f"🚨 RAID STATUS\nRaiders: {len(current_raid.get('participants', []))}")

async def setraidtime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user):
        await update.message.reply_text("Admin only 🔥")
        return
    try:
        global raid_duration_minutes
        raid_duration_minutes = int(context.args[0])
        save_data()
        await update.message.reply_text(f"✅ Raid duration set to **{raid_duration_minutes} minutes**")
    except:
        await update.message.reply_text("Usage: /setraidtime <minutes>")

async def createpoll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user):
        await update.message.reply_text("Admin only!")
        return
    question = " ".join(context.args) or "Community vote?"
    await update.message.reply_poll(question=question, options=["Yes 🔥", "No", "To the Moon 🌕"], is_anonymous=False)

async def my_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user.username
    if not user:
        await update.message.reply_text("Set username first!")
        return
    bot_info = await context.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user}"
    await update.message.reply_text(f"🔥 **Your Referral Link**\n🔗 {link}")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(verify_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.add_handler(CommandHandler("startraid", startraid))
    app.add_handler(CommandHandler("endraid", endraid))
    app.add_handler(CommandHandler("joinraid", joinraid))
    app.add_handler(CommandHandler("raidstatus", raidstatus))
    app.add_handler(CommandHandler("setraidtime", setraidtime))
    app.add_handler(CommandHandler("createpoll", createpoll))
    app.add_handler(CommandHandler("myreferral", my_referral))
    app.add_handler(CommandHandler("active", active_leaderboard))
    app.add_handler(CommandHandler("dailyactive", active_leaderboard))
    app.add_handler(CommandHandler("leaderboard", active_leaderboard))

    print("🤖 ULTIMATE FLIK BOT IS LIVE 🔥 — VERIFICATION BUTTON ADDED ON JOIN")
    app.run_polling()

if __name__ == '__main__':
    main()
