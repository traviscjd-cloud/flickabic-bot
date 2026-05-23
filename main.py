import os
import json
import requests
import io
from datetime import datetime, date
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, ChatMemberHandler

TOKEN = os.getenv('BOT_TOKEN')
XAI_API_KEY = os.getenv('XAI_API_KEY')

ADMINS = ["FLICKABICFLIK", "FLICKABIC", "flickabic"]

# Change these when ready
X_LINK = "https://x.com/FLICKABICFLIK"
TELEGRAM_GROUP_LINK = "https://t.me/flickabiclounge"
WEBSITE_LINK = "https://flickabic.com"
CA_TEXT = "TBA"

# Persistent data for hourly active user
daily_activity = {}

# Image cache (loaded once at startup)
image_cache = {}

def load_images():
    """Load images once into memory for instant responses"""
    for name in ['narrative.jpg', 'mascot.jpg', 'rules.jpg']:
        try:
            with open(name, 'rb') as f:
                image_cache[name] = f.read()
            print(f"✅ Loaded {name} into cache")
        except Exception as e:
            print(f"⚠️ Could not load {name}: {e}")

def load_data():
    global daily_activity
    try:
        with open('daily_activity.json', 'r') as f:
            daily_activity.update(json.load(f))
    except:
        pass

def save_data():
    with open('daily_activity.json', 'w') as f:
        json.dump(daily_activity, f, indent=2)

load_data()
load_images()   # ← Images cached here

def is_admin(user):
    if not user or not user.username:
        return False
    return any(admin.lower() == user.username.lower() for admin in ADMINS)

async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or is_admin(update.message.from_user):
        return False
    if update.message.text:
        lower = update.message.text.lower()
        if any(word in lower for word in ["collab", "collaboration"]):
            await update.message.delete()
            await update.message.reply_text("🚫 'Collab' or 'Collaboration' mentions are not allowed.", delete_after=10)
            return True
    return False

async def get_grok_response(query: str, username: str):
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

# SIMPLE FIRE WELCOME MESSAGE
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        username = member.username or member.first_name
        welcome_text = (
            f"🔥 **WELCOME TO THE $FLIK ARMY** @{username}!\n\n"
            "They said the timeline was dead.\n"
            "We lit the Bic.\n\n"
            "Light it. Send it. Flick to the moon! 🚀"
        )
        await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if await anti_spam(update, context):
        return

    text = update.message.text
    lower = text.lower()
    user = update.message.from_user
    username = user.username or "unknown"

    # Track activity for hourly shoutout
    today_str = str(date.today())
    if username not in daily_activity:
        daily_activity[username] = {}
    daily_activity[username][today_str] = daily_activity[username].get(today_str, 0) + 1
    save_data()

    # @flik Grok AI
    bot_info = await context.bot.get_me()
    bot_mention = "@" + bot_info.username.lower()
    if bot_mention in lower or "@flik" in lower or "@Flik" in text:
        query_text = text.replace(bot_mention, "").replace("@Flik", "").replace("@flik", "").strip()
        if query_text:
            response = await get_grok_response(query_text, username)
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("🔥 What's on your mind? Ask me anything.")
        return

    # MENU
    if "menu" in lower or "what can you do" in lower:
        await show_help_menu(update)
        return

    # REFERRAL
    if "referral" in lower:
        await update.message.reply_text(
            f"🔥 **Your Personal Referral Link** (from @{username})\n\n"
            f"🔗 {TELEGRAM_GROUP_LINK}\n\n"
            f"Share this link with friends!"
        )
        return

    # RAID HYPE
    if "raid" in lower:
        await update.message.reply_text("🔥 RAID TIME! $FLIK ARMY — LET'S LIGHT THE TIMELINE ON FIRE! DROP THE TWEET, JOIN THE RAID, TO THE MOON! 🚀")
        return

    # GREETINGS → Grok AI
    greetings = ["hello", "hey", "hi", "what’s up", "whats up", "anyone here"]
    if any(g in lower for g in greetings):
        response = await get_grok_response(text, username)
        await update.message.reply_text(response)
        return

    # CACHED IMAGE RESPONSES (instant after first load)
    if "narrative" in lower:
        if 'narrative.jpg' in image_cache:
            await update.message.reply_photo(image_cache['narrative.jpg'], caption="🔥 $FLIK Narrative")
        else:
            await update.message.reply_text("🔥 $FLIK Narrative image not found yet.")
        return

    if "mascot" in lower:
        if 'mascot.jpg' in image_cache:
            await update.message.reply_photo(image_cache['mascot.jpg'], caption="🔥 $FLIK Mascot")
        else:
            await update.message.reply_text("🔥 $FLIK Mascot image not found yet.")
        return

    if "rules" in lower:
        if 'rules.jpg' in image_cache:
            await update.message.reply_photo(image_cache['rules.jpg'], caption="📜 Group Rules")
        else:
            await update.message.reply_text("📜 Group Rules image not found yet.")
        return

    # Other keywords
    if "flik" in lower:
        await update.message.reply_text("🔥 THAT'S THE ENERGY! LFG")
        return

    if "moon" in lower:
        await update.message.reply_text("🔥 THAT'S THE ENERGY! $FLIK on the way")
        return

    if "x" in lower or "twitter" in lower:
        await update.message.reply_text(f"🔥 Official X: {X_LINK}")
        return

    if "tg" in lower or "telegram" in lower:
        await update.message.reply_text(f"🔥 Join the group: {TELEGRAM_GROUP_LINK}")
        return

    if "ca" in lower:
        await update.message.reply_text(f"🔥 CA: {CA_TEXT}")
        return

    if "website" in lower or "site" in lower:
        await update.message.reply_text(f"🔥 Official Website: {WEBSITE_LINK}")
        return

async def show_help_menu(update: Update):
    menu_text = (
        "🔥 **FLIK BOT MENU — What I Can Do**\n\n"
        "📌 **@flik** + any question → Grok AI\n"
        "🔗 **referral** → Get your personal referral link to the group\n"
        "🔥 **flik** → Energy reply (LFG)\n"
        "🌕 **moon** → Energy reply ($FLIK on the way)\n"
        "🚀 **raid** → Raid hype message\n"
        "🐦 **x** or **twitter** → Official X link\n"
        "📱 **tg** or **telegram** → Group link\n"
        "🔢 **ca** → Contract address (TBA for now)\n"
        "📖 **narrative** → Send the big $FLIK story image\n"
        "🔥 **mascot** → Send the lighter mascot image\n"
        "🌐 **website** or **site** → Official website link\n"
        "📜 **rules** → Send the group rules image\n\n"
        "Type any of these words anytime — I respond instantly!\n"
        "$FLIK ARMY TO THE MOON 🔥"
    )
    await update.message.reply_text(menu_text)

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.NEW_CHAT_MEMBERS))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 FLIK BOT IS LIVE 🔥 — IMAGE CACHING ENABLED + SIMPLE WELCOME")
    app.run_polling()

if __name__ == '__main__':
    main()
