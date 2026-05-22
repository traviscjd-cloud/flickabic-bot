import os
import json
import requests
from datetime import datetime, date
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, ChatMemberHandler
from telegram.constants import ParseMode

TOKEN = os.getenv('BOT_TOKEN')
XAI_API_KEY = os.getenv('XAI_API_KEY')

# Data
points = {}
energy_cooldown = {}
daily_streak = {}
last_login_date = {}
ADMINS = ["FLICKABICFLIK"]

def load_data():
    global points, daily_streak, last_login_date
    for file, var in [('points.json', 'points'), ('daily_streak.json', 'daily_streak'), ('last_login_date.json', 'last_login_date')]:
        try:
            with open(file, 'r') as f:
                globals()[var] = json.load(f)
        except:
            globals()[var] = {}

def save_data():
    for file, data in [('points.json', points), ('daily_streak.json', daily_streak), ('last_login_date.json', last_login_date)]:
        with open(file, 'w') as f:
            json.dump(data, f, indent=2)

load_data()

async def get_grok_response(query: str, username: str):
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

    # === @FLIK MAIN INTERACTION ===
    if "@flik" in text or "@Flik" in original_text:
        query = original_text.replace("@Flik", "").replace("@flik", "").strip().lower()

        if "myreferral" in query or "referral" in query:
            bot_info = await context.bot.get_me()
            link = f"https://t.me/{bot_info.username}?start={username}"
            await update.message.reply_text(f"🔥 <b>Your Referral Link</b>\n\n🔗 {link}", parse_mode=ParseMode.HTML)
            return

        # Normal AI query
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

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 FLIK BOT IS LIVE 🔥 — FULL @FLIK AI MODE")
    app.run_polling()

if __name__ == '__main__':
    main()
