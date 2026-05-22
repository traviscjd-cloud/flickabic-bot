import os
import json
import logging
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

# ====================== CONFIG ======================

BOT_TOKEN = os.getenv("BOT_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

ADMINS = ["flickabicflik"]

POINTS_FILE = "flick_points.json"
REFERRALS_FILE = "referrals.json"
RAID_FILE = "current_raid.json"

points = {}
referrals = {}
current_raid = None
message_timestamps = {}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ====================== DATA ======================

def load_json(filename, default):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(filename, data):
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Failed saving {filename}: {e}")

def load_data():
    global points, referrals, current_raid
    points = load_json(POINTS_FILE, {})
    referrals = load_json(REFERRALS_FILE, {})
    current_raid = load_json(RAID_FILE, None)

def save_data():
    save_json(POINTS_FILE, points)
    save_json(REFERRALS_FILE, referrals)
    save_json(RAID_FILE, current_raid)

def is_admin(user):
    return bool(user and user.username and user.username.lower() in ADMINS)

load_data()

# ====================== GROK API ======================

async def get_grok_response(query: str, username: str):
    if not XAI_API_KEY:
        return "🔥 Grok API not configured yet. Add XAI_API_KEY in Railway Variables."

    try:
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {XAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "grok-4",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are Flik Father — the savage, hype, wise, funny AI leader "
                            "of the $FLIK Solana meme coin community. Keep replies short, "
                            "energetic, and community-focused."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"User @{username} asked: {query}",
                    },
                ],
                "temperature": 0.9,
                "max_tokens": 350,
            },
            timeout=30,
        )

        data = response.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        logging.error(f"Grok error: {e}")
        return "🔥 Flik Father is cooking... Try again soon!"

# ====================== COINGECKO ======================

def get_flik_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "flik",
            "vs_currencies": "usd",
        }

        headers = {}
        if COINGECKO_API_KEY:
            headers["x-cg-demo-api-key"] = COINGECKO_API_KEY

        resp = requests.get(url, params=params, headers=headers, timeout=15)
        data = resp.json()

        return data.get("flik", {}).get("usd", "N/A")

    except Exception as e:
        logging.error(f"CoinGecko error: {e}")
        return "N/A"

# ====================== HANDLERS ======================

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return

    for member in update.message.new_chat_members:
        name = member.username or member.first_name
        await update.message.reply_text(
            f"🔥 Welcome @{name}! Mention @Flik with your question."
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.message.from_user
    username = user.username or str(user.id)
    raw_text = update.message.text
    text = raw_text.lower()

    # Anti-spam
    if not is_admin(user):
        now = datetime.now().timestamp()
        message_timestamps.setdefault(username, [])
        message_timestamps[username] = [
            t for t in message_timestamps[username] if now - t < 60
        ]
        message_timestamps[username].append(now)

        if len(message_timestamps[username]) > 5:
            try:
                await update.message.delete()
            except Exception:
                pass
            return

    # Official AI trigger
    if "@flik" in text:
        query = raw_text.replace("@Flik", "").replace("@flik", "").strip()

        if not query:
            await update.message.reply_text("🔥 Ask me something after @Flik.")
            return

        response = await get_grok_response(query, username)
        await update.message.reply_text(response)
        return

    # Energy points
    energy_words = ["flick", "flik", "moon", "fire", "send it", "light it", "bic"]

    if any(word in text for word in energy_words):
        points[username] = points.get(username, 0) + 1
        save_data()
        await update.message.reply_text("🔥 THAT'S THE ENERGY! SEND IT TO THE MOON $FLIK")
        return

    # Auto replies
    if "twitter" in text or " x " in f" {text} ":
        await update.message.reply_text("🔥 Official X: https://x.com/FLICKABICFLIK")

    if "website" in text or "site" in text:
        await update.message.reply_text("🔥 Official Website: https://flickabic.com")

# ====================== COMMANDS ======================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    username = user.username or str(user.id)

    if context.args:
        referrer = context.args[0]

        if referrer != username:
            referrals[username] = referrer
            points[referrer] = points.get(referrer, 0) + 5
            save_data()

    await update.message.reply_text(
        "🔥 Welcome to FLICKABIC.\n\n"
        "Commands:\n"
        "/myreferral\n"
        "/leaderboard\n"
        "/price\n"
        "/joinraid\n"
        "/raidstatus\n\n"
        "Mention @Flik with a question to summon Flik Father."
    )

async def my_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    if not user.username:
        await update.message.reply_text("❌ Set a Telegram username first.")
        return

    bot_info = await context.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user.username}"

    await update.message.reply_text(
        f"🔥 <b>Your Referral Link</b>\n\n🔗 {link}",
        parse_mode=ParseMode.HTML,
    )

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not points:
        await update.message.reply_text("No points yet — start grinding 🔥")
        return

    sorted_points = sorted(points.items(), key=lambda x: x[1], reverse=True)

    msg = "🏆 <b>LEADERBOARD</b>\n\n"
    for i, (u, p) in enumerate(sorted_points[:10], 1):
        msg += f"{i}. @{u} — {p} points\n"

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flik_price = get_flik_price()
    await update.message.reply_text(
        f"💰 Current $FLIK Price: ${flik_price} USD"
    )

async def startraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_raid

    if not is_admin(update.message.from_user):
        await update.message.reply_text("Admin only 🔥")
        return

    current_raid = {
        "participants": [],
        "started_at": datetime.now().isoformat(),
    }

    save_data()
    await update.message.reply_text("🚨 RAID STARTED! Type /joinraid to earn points!")

async def joinraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_raid

    if not current_raid:
        await update.message.reply_text("No active raid.")
        return

    user = update.message.from_user
    username = user.username or str(user.id)

    if username not in current_raid["participants"]:
        current_raid["participants"].append(username)
        points[username] = points.get(username, 0) + 10
        save_data()
        await update.message.reply_text(f"🔥 @{username} joined the raid! +10 points")
    else:
        await update.message.reply_text("Already in raid 🔥")

async def raidstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not current_raid:
        await update.message.reply_text("No active raid.")
        return

    count = len(current_raid.get("participants", []))
    await update.message.reply_text(f"🚨 RAID STATUS\nRaiders: {count}")

# ====================== MAIN ======================

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing. Add it in Railway Variables.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myreferral", my_referral))
    app.add_handler(CommandHandler("leaderboard", show_leaderboard))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("startraid", startraid))
    app.add_handler(CommandHandler("joinraid", joinraid))
    app.add_handler(CommandHandler("raidstatus", raidstatus))

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("🤖 FLIK FATHER BOT IS LIVE 🔥")
    app.run_polling()

if __name__ == "__main__":
    main()
