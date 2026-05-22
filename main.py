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
DEFAULT_RAID_DURATION = 15
RAID_JOIN_POINTS = 10
RAID_END_POINTS = 20

ADMINS = ["FLICKABICFLIK", "FLICKABIC", "flickabic"]

# Data
points = {}
energy_cooldown = {}
daily_streak = {}
last_login_date = {}
grok_usage = {}
referrals = {}
current_raid = None
raid_duration_minutes = DEFAULT_RAID_DURATION
daily_activity = {}
weekly_activity = {}

def load_data():
    global points, daily_streak, last_login_date, grok_usage, referrals, current_raid, raid_duration_minutes, daily_activity, weekly_activity
    files = {
        'points.json': 'points',
        'daily_streak.json': 'daily_streak',
        'last_login_date.json': 'last_login_date',
        'grok_usage.json': 'grok_usage',
        'referrals.json': 'referrals',
        'current_raid.json': 'current_raid',
        'raid_settings.json': 'raid_duration_minutes',
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
                       ('referrals.json', referrals), ('daily_activity.json', daily_activity),
                       ('weekly_activity.json', weekly_activity)]:
        with open(file, 'w') as f:
            json.dump(data, f, indent=2)
    if current_raid:
        with open('current_raid.json', 'w') as f:
            json.dump(current_raid, f, indent=2)
    with open('raid_settings.json', 'w') as f:
        json.dump(raid_duration_minutes, f)

load_data()

def is_admin(user):
    if not user or not user.username:
        return False
    username_lower = user.username.lower()
    return any(admin.lower() == username_lower for admin in ADMINS)

async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or is_admin(update.message.from_user):
        return False
    if update.message.text:
        text = update.message.text
        lower = text.lower()
        if any(word in lower for word in ["collab", "collaboration"]):
            await update.message.delete()
            await update.message.reply_text("🚫 'Collab' or 'Collaboration' mentions are not allowed.", delete_after=10)
            return True
        is_x_link = any(domain in lower for domain in ["x.com", "twitter.com"])
        has_flik_ref = any(word in lower for word in ["flik", "$flik", "flick", "flickabic", "flickabicflik"])
        has_blocked_link = any(word in lower for word in ["http", "t.me", "tco", "telegram.me"])
        if (len(text) > 300 or
            (text.isupper() and len(text) > 50) or
            (has_blocked_link and not (is_x_link and has_flik_ref))):
            await update.message.delete()
            await update.message.reply_text("🚫 Spam detected and removed.", delete_after=10)
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

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        keyboard = [[InlineKeyboardButton("✅ I'm not a bot", callback_data="verify_human")]]
        await update.message.reply_text(
            f"🔥 Welcome @{member.username or member.first_name}!\n\nClick the button below to verify you're not a bot.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "verify_human":
        username = query.from_user.username
        if username and not is_admin(query.from_user):
            points[username] = points.get(username, 0) + 5
            save_data()
        await query.edit_message_text("✅ **Verified!** Welcome to the $FLIK community 🔥")

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

    if username not in daily_activity:
        daily_activity[username] = {}
    daily_activity[username][today_str] = daily_activity[username].get(today_str, 0) + 1
    if username not in weekly_activity:
        weekly_activity[username] = 0
    weekly_activity[username] += 1
    save_data()

    if username not in last_login_date or last_login_date[username] != today_str:
        last_login_date[username] = today_str
        streak = daily_streak.get(username, 0) + 1
        daily_streak[username] = streak
        if not is_admin(user):
            reward = 5 if streak == 1 else 15
            points[username] = points.get(username, 0) + reward
            save_data()
            await update.message.reply_text(f"🌟 Daily login! +{reward} points | Streak: {streak}")
        else:
            await update.message.reply_text(f"🌟 Daily login! Streak: {streak} (no points for admins)")

    bot_info = await context.bot.get_me()
    bot_mention = "@" + bot_info.username.lower()
    if bot_mention in original.lower() or "@flik" in text or "@Flik" in original:
        query_text = original.replace(bot_mention, "").replace("@Flik", "").replace("@flik", "").strip()
        if query_text:
            response = await get_grok_response(query_text, username)
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("🔥 What's on your mind? Ask me anything.")
        return

    if any(w in text for w in ["flick", "flik", "moon", "fire", "send it", "light it", "bic"]):
        last = energy_cooldown.get(username, 0)
        now = datetime.now().timestamp()
        if now - last > 60:
            energy_cooldown[username] = now
            if not is_admin(user):
                points[username] = points.get(username, 0) + 1
                save_data()
                await update.message.reply_text("🔥 THAT'S THE ENERGY! $FLIK TO THE MOON")
            else:
                await update.message.reply_text("🔥 Energy detected")
        else:
            await update.message.reply_text(f"⏳ Cooldown {int(60 - (now - last))}s left.")
        return

    if "x" in text or "twitter" in text:
        await update.message.reply_text("🔥 Official X: https://x.com/FLICKABICFLIK")
    if "website" in text or "site" in text:
        await update.message.reply_text("🔥 Official Website: https://flickabic.com")

async def active_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today_str = str(date.today())
    today_counts = {user: counts.get(today_str, 0) for user, counts in daily_activity.items() if today_str in counts}
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

# ====================== INTERACTIVE RAID POP-UP ======================
async def raid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🚀 Quick Raid (15 min)", callback_data="raid_quick")],
        [InlineKeyboardButton("⚙️ Custom Targets", callback_data="raid_custom")]
    ]
    await update.message.reply_text(
        "🔥 **Raid Setup**\nChoose how you want to run the raid:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def raid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "raid_quick":
        global current_raid
        if current_raid:
            await query.edit_message_text("Raid already active! Use /resetraid first.")
            return
        current_raid = {"participants": [], "tweet_url": None, "duration": DEFAULT_RAID_DURATION}
        save_data()
        await query.edit_message_text("✅ Quick raid started (15 minutes).\nSend the tweet URL now or use /startraid with URL.")
        context.job_queue.run_once(auto_end_raid, DEFAULT_RAID_DURATION * 60, chat_id=query.message.chat_id, name="raid_end")

    elif data == "raid_custom":
        await query.edit_message_text("Custom raid setup coming soon — for now use /startraid <url> <likes> <reposts> <comments> <minutes> or /resetraid first.")

# Raid system (kept for compatibility)
async def startraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user):
        await update.message.reply_text("Admin only 🔥")
        return
    global current_raid
    if current_raid:
        await update.message.reply_text("Raid already active! Use /resetraid first.")
        return
    current_raid = {"participants": []}
    save_data()
    context.job_queue.run_once(auto_end_raid, raid_duration_minutes * 60, chat_id=update.message.chat_id, name="raid_end")
    await update.message.reply_text(f"🚨 **RAID STARTED!** 🚨\nDuration: {raid_duration_minutes} min\n`/joinraid` to join!")

async def resetraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user):
        await update.message.reply_text("Admin only 🔥")
        return
    global current_raid
    current_raid = None
    save_data()
    await update.message.reply_text("✅ Raid reset. Use /raid to start a new one.")

async def joinraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_raid
    if not current_raid:
        await update.message.reply_text("No active raid.")
        return
    user = update.message.from_user
    username = user.username
    if username and username not in current_raid.get("participants", []):
        current_raid.setdefault("participants", []).append(username)
        if not is_admin(user):
            points[username] = points.get(username, 0) + RAID_JOIN_POINTS
            save_data()
        await update.message.reply_text(f"🔥 @{username} joined the raid! **+{RAID_JOIN_POINTS if not is_admin(user) else 0} points**")
    else:
        await update.message.reply_text("Already in raid 🔥")

async def auto_end_raid(context: ContextTypes.DEFAULT_TYPE):
    global current_raid
    if not current_raid:
        return
    participants = current_raid.get("participants", [])
    for username in participants:
        points[username] = points.get(username, 0) + RAID_END_POINTS
    save_data()
    msg = f"🏁 **RAID ENDED** 🏁\nTotal raiders: **{len(participants)}**\n**+{RAID_END_POINTS} points** awarded to every raider!\nGreat job! $FLIK to the moon!"
    await context.bot.send_message(chat_id=context.job.chat_id, text=msg)
    current_raid = None
    save_data()

async def endraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user):
        await update.message.reply_text("Admin only 🔥")
        return
    await auto_end_raid(context)

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

async def myusername(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await update.message.reply_text(f"Bot sees your username as: **@{user.username}**\nADMINS list: {ADMINS}")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(verify_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.add_handler(CommandHandler("startraid", startraid))
    app.add_handler(CommandHandler("raid", raid_command))
    app.add_handler(CommandHandler("resetraid", resetraid))
    app.add_handler(CommandHandler("endraid", endraid))
    app.add_handler(CommandHandler("joinraid", joinraid))
    app.add_handler(CommandHandler("raidstatus", raidstatus))
    app.add_handler(CommandHandler("setraidtime", setraidtime))
    app.add_handler(CommandHandler("createpoll", createpoll))
    app.add_handler(CommandHandler("myreferral", my_referral))
    app.add_handler(CommandHandler("active", active_leaderboard))
    app.add_handler(CommandHandler("dailyactive", active_leaderboard))
    app.add_handler(CommandHandler("leaderboard", active_leaderboard))
    app.add_handler(CommandHandler("myusername", myusername))

    print("🤖 ULTIMATE FLIK BOT IS LIVE 🔥 — INTERACTIVE /raid POP-UP ADDED")
    app.run_polling()

if __name__ == '__main__':
    main()
