import os
import json
import requests
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ChatMemberHandler, CallbackQueryHandler
)

TOKEN = os.getenv('BOT_TOKEN')
XAI_API_KEY = os.getenv('XAI_API_KEY')

DAILY_GROK_LIMIT = 15
RAID_JOIN_POINTS = 10
RAID_END_POINTS = 20
RAID_DURATION_MINUTES = 15

ADMINS = ["FLICKABICFLIK", "FLICKABIC", "flickabic"]

# Persistent data
points = {}
energy_last_time = {}
daily_streak = {}
last_login_date = {}
grok_usage = {}
referrals = {}
current_raid = None
daily_activity = {}
weekly_activity = {}


def load_data():
    global points, energy_last_time, daily_streak, last_login_date
    global grok_usage, referrals, current_raid, daily_activity, weekly_activity
    files = {
        'points.json': points,
        'energy_last_time.json': energy_last_time,
        'daily_streak.json': daily_streak,
        'last_login_date.json': last_login_date,
        'grok_usage.json': grok_usage,
        'referrals.json': referrals,
        'daily_activity.json': daily_activity,
        'weekly_activity.json': weekly_activity,
    }
    for file, target in files.items():
        try:
            with open(file, 'r') as f:
                target.update(json.load(f))
        except Exception:
            pass
    try:
        with open('current_raid.json', 'r') as f:
            current_raid = json.load(f)
    except Exception:
        current_raid = None


def save_data():
    data_map = {
        'points.json': points,
        'energy_last_time.json': energy_last_time,
        'daily_streak.json': daily_streak,
        'last_login_date.json': last_login_date,
        'grok_usage.json': grok_usage,
        'referrals.json': referrals,
        'daily_activity.json': daily_activity,
        'weekly_activity.json': weekly_activity,
    }
    for file, d in data_map.items():
        with open(file, 'w') as f:
            json.dump(d, f, indent=2)
    if current_raid:
        with open('current_raid.json', 'w') as f:
            json.dump(current_raid, f, indent=2)
    else:
        try:
            os.remove('current_raid.json')
        except Exception:
            pass


load_data()


def is_admin(user):
    """Accept a user object or a plain username string."""
    if user is None:
        return False
    username = user if isinstance(user, str) else getattr(user, 'username', None)
    if not username:
        return False
    return any(admin.lower() == username.lower() for admin in ADMINS)


async def delete_message_later(context: ContextTypes.DEFAULT_TYPE):
    """Job callback to delete a message after a delay."""
    chat_id, message_id = context.job.data
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or is_admin(update.message.from_user):
        return False
    if update.message.text:
        text = update.message.text
        lower = text.lower()
        if any(word in lower for word in ["collab", "collaboration"]):
            await update.message.delete()
            msg = await update.message.reply_text("🚫 'Collab' or 'Collaboration' mentions are not allowed.")
            context.job_queue.run_once(
                delete_message_later, 10,
                data=(msg.chat_id, msg.message_id)
            )
            return True
        is_x_link = any(domain in lower for domain in ["x.com", "twitter.com"])
        has_flik_ref = any(word in lower for word in ["flik", "$flik", "flick", "flickabic", "flickabicflik"])
        has_blocked_link = (
            any(word in lower for word in ["http", "t.me", "tco", "telegram.me"])
            and not (is_x_link and has_flik_ref)
        )
        if len(text) > 300 or (text.isupper() and len(text) > 50) or has_blocked_link:
            await update.message.delete()
            msg = await update.message.reply_text("🚫 Links without $FLIK / flickabic references are not allowed.")
            context.job_queue.run_once(
                delete_message_later, 10,
                data=(msg.chat_id, msg.message_id)
            )
            return True
    if update.message.photo or update.message.sticker or update.message.animation or update.message.video:
        await update.message.delete()
        await update.message.reply_text("📸 Media sent to admins for approval.")
        return True
    return False


async def get_grok_response(query: str, username: str):
    # Use string-based admin check
    if not is_admin(username):
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
            json={
                "model": "grok-4",
                "messages": [
                    {"role": "system", "content": "You are Flik — savage, hype, funny, wise leader of $FLIK."},
                    {"role": "user", "content": f"@{username}: {query}"}
                ]
            }
        )
        return r.json()['choices'][0]['message']['content']
    except Exception:
        return "🔥 Flik is cooking... Try again soon!"


async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fires when a new member joins the group."""
    result = update.chat_member
    if result.new_chat_member.status not in ("member", "restricted"):
        return
    member = result.new_chat_member.user
    keyboard = [[InlineKeyboardButton("✅ I'm not a bot", callback_data="verify_human")]]
    await context.bot.send_message(
        chat_id=result.chat.id,
        text=f"🔥 Welcome @{member.username or member.first_name}!\n\nClick the button below to verify you're not a bot.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "verify_human":
        username = query.from_user.username
        if username and not is_admin(query.from_user):
            points[username] = points.get(username, 0) + 5
            save_data()
        await query.edit_message_text("✅ **Verified!** Welcome to the $FLIK community 🔥")

    elif data == "start_raid":
        if not is_admin(query.from_user):
            await query.edit_message_text("Admin only 🔥")
            return
        global current_raid
        current_raid = {"participants": [], "tweet_url": None, "duration": RAID_DURATION_MINUTES}
        save_data()
        await query.edit_message_text("🚨 **RAID SETUP STARTED**\n\n**Paste the full tweet URL now.**")

    elif data == "leaderboard":
        # Use query.message so this works in a callback context
        await _send_leaderboard(query.message)

    elif data == "my_referral":
        await _send_referral(query.message, query.from_user.username, context)

    elif data == "raid_status":
        await _send_raid_status(query.message)


# --- Shared helpers that work with any message object ---

async def _send_leaderboard(message):
    today_str = str(date.today())
    today_counts = {u: c.get(today_str, 0) for u, c in daily_activity.items() if today_str in c}
    weekly_counts = weekly_activity.copy()
    msg = "🏆 **MOST ACTIVE LEADERBOARD**\n\n**📅 TODAY**\n"
    if today_counts:
        for i, (u, c) in enumerate(sorted(today_counts.items(), key=lambda x: x[1], reverse=True)[:10], 1):
            msg += f"{i}. @{u} — {c} messages\n"
    else:
        msg += "No activity yet today.\n"
    msg += "\n**📅 THIS WEEK**\n"
    if weekly_counts:
        for i, (u, c) in enumerate(sorted(weekly_counts.items(), key=lambda x: x[1], reverse=True)[:10], 1):
            msg += f"{i}. @{u} — {c} messages\n"
    else:
        msg += "No weekly activity yet.\n"
    await message.reply_text(msg)


async def _send_raid_status(message):
    global current_raid
    if not current_raid:
        await message.reply_text("No active raid.")
        return
    url = current_raid.get("tweet_url", "No URL yet")
    await message.reply_text(
        f"🚨 RAID STATUS\nRaiders: {len(current_raid.get('participants', []))}\nTweet: {url}"
    )


async def _send_referral(message, username, context):
    if not username:
        await message.reply_text("Set username first!")
        return
    bot_info = await context.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={username}"
    await message.reply_text(f"🔥 **Your Referral Link**\n🔗 {link}")


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE = None):
    keyboard = [
        [InlineKeyboardButton("🚀 Start New Raid", callback_data="start_raid")],
        [InlineKeyboardButton("📊 Raid Status", callback_data="raid_status")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("🔥 My Points & Referral", callback_data="my_referral")],
    ]
    await update.message.reply_text(
        "🔥 **FLIK DASHBOARD** — Choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if await anti_spam(update, context):
        return

    text = update.message.text
    lower = text.lower()
    user = update.message.from_user
    username = user.username
    if not username:
        return

    today_str = str(date.today())

    daily_activity.setdefault(username, {})
    daily_activity[username][today_str] = daily_activity[username].get(today_str, 0) + 1
    weekly_activity[username] = weekly_activity.get(username, 0) + 1
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

    # RAID SETUP — URL CAPTURE (high priority)
    global current_raid
    if current_raid and current_raid.get("tweet_url") is None and ("x.com" in lower or "twitter.com" in lower):
        current_raid["tweet_url"] = text
        save_data()
        await update.message.reply_text(
            "✅ **Tweet URL saved!**\n\nType **/raidlaunch** when ready to start the raid "
            "(or /setraidtime <minutes> to change duration)."
        )
        return

    # @flik menu
    bot_info = await context.bot.get_me()
    bot_mention = "@" + bot_info.username.lower()
    if bot_mention in lower or "@flik" in lower or "@Flik" in text:
        query_text = text.replace(bot_mention, "").replace("@Flik", "").replace("@flik", "").strip()
        if not query_text:
            await show_main_menu(update, context)
            return
        response = await get_grok_response(query_text, username)
        await update.message.reply_text(response)
        return

    # Energy system
    if any(w in lower for w in ["flick", "flik", "moon", "fire", "send it", "light it", "bic"]):
        now = datetime.now().timestamp()
        last = energy_last_time.get(username, 0)
        if now - last > 3600:
            energy_last_time[username] = now
            if not is_admin(user):
                points[username] = points.get(username, 0) + 1
                save_data()
        await update.message.reply_text("🔥 THAT'S THE ENERGY! $FLIK TO THE MOON")
        return

    # Auto-replies
    if "x" in lower or "twitter" in lower:
        await update.message.reply_text("🔥 Official X: https://x.com/FLICKABICFLIK")
    if "website" in lower or "site" in lower:
        await update.message.reply_text("🔥 Official Website: https://flickabic.com")


# --- Command handlers ---

async def active_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_leaderboard(update.message)


async def raidstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_raid_status(update.message)


async def my_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_referral(update.message, update.message.from_user.username, context)


async def startraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user):
        await update.message.reply_text("Admin only 🔥")
        return
    global current_raid
    if current_raid:
        await update.message.reply_text("Raid already active! Use /resetraid first.")
        return
    current_raid = {"participants": [], "tweet_url": None, "duration": RAID_DURATION_MINUTES}
    save_data()
    await update.message.reply_text("🚨 **RAID SETUP STARTED**\n\nPaste the full tweet URL now.")


async def raidlaunch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user):
        await update.message.reply_text("Admin only 🔥")
        return
    global current_raid
    if not current_raid or not current_raid.get("tweet_url"):
        await update.message.reply_text("Setup not complete. Send tweet URL first.")
        return
    context.job_queue.run_once(
        auto_end_raid,
        current_raid["duration"] * 60,
        chat_id=update.message.chat_id
    )
    await update.message.reply_text(
        f"🚨 **RAID IS NOW LIVE!** 🚨\n"
        f"Tweet: {current_raid['tweet_url']}\n"
        f"Duration: {current_raid['duration']} minutes\n\n"
        f"Type /joinraid to participate!"
    )
    save_data()


async def resetraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user):
        await update.message.reply_text("Admin only 🔥")
        return
    global current_raid
    current_raid = None
    save_data()
    await update.message.reply_text("✅ Raid reset. Type /menu")


async def joinraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_raid
    if not current_raid or not current_raid.get("tweet_url"):
        await update.message.reply_text("No active raid yet.")
        return
    user = update.message.from_user
    username = user.username
    if not username:
        await update.message.reply_text("Set a username first!")
        return
    if username not in current_raid.get("participants", []):
        current_raid.setdefault("participants", []).append(username)
        reward = 0
        if not is_admin(user):
            points[username] = points.get(username, 0) + RAID_JOIN_POINTS
            reward = RAID_JOIN_POINTS
            save_data()
        await update.message.reply_text(f"🔥 @{username} joined the raid! **+{reward} points**")
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

    # chat_id comes from job when scheduled, or job.data when called via endraid
    chat_id = getattr(context.job, 'chat_id', None) or getattr(context.job, 'data', {}).get('chat_id')
    msg = (
        f"🏁 **RAID ENDED** 🏁\n"
        f"Total raiders: **{len(participants)}**\n"
        f"**+{RAID_END_POINTS} points** awarded!\n"
        f"$FLIK to the moon!"
    )
    if chat_id:
        await context.bot.send_message(chat_id=chat_id, text=msg)
    current_raid = None
    save_data()


async def endraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user):
        await update.message.reply_text("Admin only 🔥")
        return
    global current_raid
    if not current_raid:
        await update.message.reply_text("No active raid.")
        return
    participants = current_raid.get("participants", [])
    for username in participants:
        points[username] = points.get(username, 0) + RAID_END_POINTS
    save_data()
    await update.message.reply_text(
        f"🏁 **RAID ENDED** 🏁\n"
        f"Total raiders: **{len(participants)}**\n"
        f"**+{RAID_END_POINTS} points** awarded!\n"
        f"$FLIK to the moon!"
    )
    current_raid = None
    save_data()


async def setraidtime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user):
        await update.message.reply_text("Admin only 🔥")
        return
    try:
        global RAID_DURATION_MINUTES
        RAID_DURATION_MINUTES = int(context.args[0])
        if current_raid:
            current_raid["duration"] = RAID_DURATION_MINUTES
            save_data()
        await update.message.reply_text(f"✅ Raid duration set to **{RAID_DURATION_MINUTES} minutes**")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /setraidtime <minutes>")


async def createpoll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user):
        await update.message.reply_text("Admin only!")
        return
    question = " ".join(context.args) or "Community vote?"
    await update.message.reply_poll(
        question=question,
        options=["Yes 🔥", "No", "To the Moon 🌕"],
        is_anonymous=False
    )


async def myusername(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await update.message.reply_text(f"Bot sees your username as: **@{user.username}**\nADMINS list: {ADMINS}")


def main():
    app = Application.builder().token(TOKEN).build()

    # FIX: Use CHAT_MEMBER (not MY_CHAT_MEMBER) to detect new members joining
    app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.add_handler(CommandHandler("menu", show_main_menu))
    app.add_handler(CommandHandler("startraid", startraid))
    app.add_handler(CommandHandler("raidlaunch", raidlaunch))
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

    print("🤖 ULTIMATE FLIK BOT IS LIVE 🔥")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
