import os
import json
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler
from telegram.constants import ParseMode

TOKEN = os.getenv('BOT_TOKEN')
XAI_API_KEY = os.getenv('XAI_API_KEY')

# Data
points = {}
referrals = {}
current_raid = None
message_timestamps = {}
energy_cooldown = {}  # New: Cooldown tracker
ADMINS = ["FLICKABICFLIK"]

def load_data():
    global points, referrals, current_raid
    for file, var in [('flick_points.json', 'points'), ('referrals.json', 'referrals'), ('current_raid.json', 'current_raid')]:
        try:
            with open(file, 'r') as f:
                globals()[var] = json.load(f)
        except:
            globals()[var] = {} if var != 'current_raid' else None

def save_data():
    for file, data in [('flick_points.json', points), ('referrals.json', referrals)]:
        with open(file, 'w') as f:
            json.dump(data, f, indent=2)
    if current_raid:
        with open('current_raid.json', 'w') as f:
            json.dump(current_raid, f, indent=2)

load_data()

def is_admin(user):
    return user and user.username and user.username in ADMINS

# ====================== GROK AI ======================
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
                "temperature": 0.85,
                "max_tokens": 350
            }
        )
        return r.json()['choices'][0]['message']['content']
    except:
        return "🔥 Flik is cooking... Try again soon!"

# ====================== HANDLERS ======================
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(f"🔥 Welcome @{member.username or member.first_name}! Mention **@Flik** + any question.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()
    user = update.message.from_user
    original_text = update.message.text
    now = datetime.now().timestamp()

    # Anti-spam
    if not is_admin(user):
        if user.username not in message_timestamps:
            message_timestamps[user.username] = []
        message_timestamps[user.username] = [t for t in message_timestamps[user.username] if now - t < 60]
        message_timestamps[user.username].append(now)
        if len(message_timestamps[user.username]) > 6:
            try:
                await update.message.delete()
            except:
                pass
            return

    # === @FLIK AI TRIGGER ===
    if "@flik" in text or "@Flik" in original_text:
        query = original_text.replace("@Flik", "").replace("@flik", "").strip()
        response = await get_grok_response(query, user.username or "user")
        await update.message.reply_text(response)
        return

    # === ENERGY SYSTEM WITH 60-SECOND COOLDOWN ===
    energy_words = ["flick", "flik", "moon", "fire", "send it", "light it", "bic"]
    if any(word in text for word in energy_words):
        username = user.username
        if username:
            last_energy = energy_cooldown.get(username, 0)
            if now - last_energy > 60:  # 60 second cooldown
                energy_cooldown[username] = now
                points[username] = points.get(username, 0) + 1
                save_data()
                await update.message.reply_text("🔥 THAT'S THE ENERGY! $FLIK TO THE MOON")
            else:
                await update.message.reply_text("⏳ Energy on cooldown! Wait a bit before sending more hype.")
        return

    # Auto-replies
    if "x" in text or "twitter" in text:
        await update.message.reply_text("🔥 Official X: https://x.com/FLICKABICFLIK")
    if "website" in text or "site" in text:
        await update.message.reply_text("🔥 Official Website: https://flickabic.com")

# ====================== COMMANDS ======================
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

async def startraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user):
        await update.message.reply_text("Admin only 🔥")
        return
    global current_raid
    current_raid = {"participants": []}
    save_data()
    await update.message.reply_text("🚨 RAID STARTED! Type /joinraid")

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
        await update.message.reply_text(f"🔥 @{user} joined the raid! +10 points")
    else:
        await update.message.reply_text("Already in raid 🔥")

async def raidstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_raid
    if not current_raid:
        await update.message.reply_text("No active raid.")
        return
    await update.message.reply_text(f"🚨 RAID STATUS\nRaiders: {len(current_raid.get('participants', []))}")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CommandHandler("myreferral", my_referral))
    app.add_handler(CommandHandler("leaderboard", show_leaderboard))
    app.add_handler(CommandHandler("startraid", startraid))
    app.add_handler(CommandHandler("joinraid", joinraid))
    app.add_handler(CommandHandler("raidstatus", raidstatus))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 FLIK BOT IS LIVE 🔥 — FULL ULTIMATE AI MODE WITH COOLDOWN")
    app.run_polling()

if __name__ == '__main__':
    main()
