import os
import json
import requests
from datetime import datetime, date
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler
from telegram.constants import ParseMode

TOKEN = os.getenv('BOT_TOKEN')
XAI_API_KEY = os.getenv('XAI_API_KEY')

DAILY_GROK_LIMIT = 15

# Data
points = {}
energy_cooldown = {}
daily_streak = {}
last_login_date = {}
grok_usage = {}
ADMINS = ["FLICKABICFLIK"]

def load_data():
    global points, daily_streak, last_login_date, grok_usage
    for file, var in [('points.json', 'points'), ('daily_streak.json', 'daily_streak'),
                      ('last_login_date.json', 'last_login_date'), ('grok_usage.json', 'grok_usage')]:
        try:
            with open(file, 'r') as f:
                globals()[var] = json.load(f)
        except:
            globals()[var] = {}

def save_data():
    for file, data in [('points.json', points), ('daily_streak.json', daily_streak),
                       ('last_login_date.json', last_login_date), ('grok_usage.json', grok_usage)]:
        with open(file, 'w') as f:
            json.dump(data, f, indent=2)

load_data()

def is_admin(user):
    return user and user.username and user.username in ADMINS

async def get_grok_response(query: str, username: str):
    # Admins have unlimited usage
    if is_admin(type('obj', (object,), {'username': username})()):
        pass
    else:
        today = str(date.today())
        if username not in grok_usage:
            grok_usage[username] = {}
        if today not in grok_usage[username]:
            grok_usage[username][today] = 0

        if grok_usage[username][today] >= DAILY_GROK_LIMIT:
            return f"⛔ Daily limit reached ({DAILY_GROK_LIMIT} messages).\nAdmins have unlimited access."

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
                    {"role": "system", "content": "You are Flik — the ultimate savage, hype, funny, and wise AI leader of the $FLIK community."},
                    {"role": "user", "content": f"@{username} asked: {query}"}
                ],
                "temperature": 0.9,
                "max_tokens": 400
            }
        )
        return r.json()['choices'][0]['message']['content']
    except:
        return "🔥 Flik is cooking... Try again soon!"

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(f"🔥 Welcome @{member.username or member.first_name}! Mention **@Flik** + anything.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()
    original_text = update.message.text
    user = update.message.from_user
    now = datetime.now().timestamp()
    today = str(date.today())
    username = user.username

    if not username:
        return

    # Daily Login Reward
    if username not in last_login_date or last_login_date[username] != today:
        last_login_date[username] = today
        streak = daily_streak.get(username, 0) + 1
        daily_streak[username] = streak
        reward = 5 if streak == 1 else 8 if streak == 2 else 12 if streak == 3 else 15
        points[username] = points.get(username, 0) + reward
        save_data()
        await update.message.reply_text(f"🌟 **Daily Login!** +{reward} points | Streak: {streak} days")

    # === @FLIK AI ===
    if "@flik" in text or "@Flik" in original_text:
        query = original_text.replace("@Flik", "").replace("@flik", "").strip()
        if query:
            response = await get_grok_response(query, username)
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("🔥 What's on your mind? Ask me anything.")
        return

    # Energy System
    if any(word in text for word in ["flick", "flik", "moon", "fire", "send it", "light it", "bic"]):
        last = energy_cooldown.get(username, 0)
        if now - last > 60:
            energy_cooldown[username] = now
            points[username] = points.get(username, 0) + 1
            save_data()
            await update.message.reply_text("🔥 THAT'S THE ENERGY! $FLIK TO THE MOON")
        else:
            left = int(60 - (now - last))
            await update.message.reply_text(f"⏳ Cooldown! {left} seconds left.")
        return

    # Auto-replies
    if "x" in text or "twitter" in text:
        await update.message.reply_text("🔥 Official X: https://x.com/FLICKABICFLIK")
    if "website" in text or "site" in text:
        await update.message.reply_text("🔥 Official Website: https://flickabic.com")

# Commands (always available)
async def my_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user.username
    if not user:
        await update.message.reply_text("❌ Set a Telegram username first!")
        return
    bot_info = await context.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user}"
    await update.message.reply_text(f"🔥 <b>Your Referral Link</b>\n\n🔗 {link}", parse_mode=ParseMode.HTML)

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sorted_points = sorted(points.items(), key=lambda x: x[1], reverse=True)
    msg = "🏆 <b>LEADERBOARD</b>\n\n"
    for i, (u, p) in enumerate(sorted_points[:10], 1):
        msg += f"{i}. @{u} — {p} points\n"
    await update.message.reply_text(msg or "No points yet — start grinding!")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CommandHandler("myreferral", my_referral))
    app.add_handler(CommandHandler("leaderboard", show_leaderboard))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 FLIK BOT IS LIVE 🔥 — @Flik AI with Admin Unlimited")
    app.run_polling()

if __name__ == '__main__':
    main()
