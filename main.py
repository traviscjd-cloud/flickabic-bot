import os
import json
import asyncio
import aiohttp
from datetime import date
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TOKEN = os.getenv('BOT_TOKEN')
XAI_API_KEY = os.getenv('XAI_API_KEY')

ADMINS = ["FLICKABICFLIK", "FLICKABIC", "flickabic"]

X_LINK = "https://x.com/FLICKABICFLIK"
TELEGRAM_GROUP_LINK = "https://t.me/flickabiclounge"
WEBSITE_LINK = "https://flickabic.com"
CA_TEXT = "TBA"

daily_activity = {}

def load_data():
    global daily_activity
    try:
        with open('daily_activity.json', 'r') as f:
            daily_activity.update(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        daily_activity = {}

def save_data():
    try:
        with open('daily_activity.json', 'w') as f:
            json.dump(daily_activity, f, indent=2)
    except Exception as e:
        print(f"[save_data error] {e}")

load_data()

def is_admin(user):
    if not user or not user.username:
        return False
    return any(admin.lower() == user.username.lower() for admin in ADMINS)

async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not update.message or is_admin(update.message.from_user):
        return False
    if update.message.text:
        lower = update.message.text.lower()
        if any(word in lower for word in ["collab", "collaboration"]):
            try:
                await update.message.delete()
            except Exception:
                pass  # Bot may not have delete permissions
            await update.message.reply_text("🚫 'Collab' or 'Collaboration' mentions are not allowed.")
            return True
    return False

async def get_grok_response(query: str, username: str) -> str:
    if not XAI_API_KEY:
        return "🔥 Flik is here! Ask me anything."
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {XAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-3",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are Flik — savage, hype, funny, wise leader of $FLIK."
                        },
                        {
                            "role": "user",
                            "content": f"@{username}: {query}"
                        }
                    ]
                },
                timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                data = await resp.json()
                return data['choices'][0]['message']['content']
    except asyncio.TimeoutError:
        return "🔥 Flik timed out — try again!"
    except Exception as e:
        print(f"[grok error] {e}")
        return "🔥 Flik is cooking... Try again soon!"

# FIX: use filters.StatusUpdate.NEW_CHAT_MEMBERS, not ChatMemberHandler
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return
    for member in update.message.new_chat_members:
        username = member.username or member.first_name
        welcome_text = (
            f"🔥 *WELCOME TO THE $FLIK ARMY* @{username}!\n\n"
            "They said the timeline was dead.\n"
            "We lit the Bic.\n\n"
            "Light it. Send it. Flick to the moon! 🚀"
        )
        await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if await anti_spam(update, context):
        return

    text = update.message.text
    lower = text.lower()
    user = update.message.from_user
    username = user.username if user.username else "unknown"

    # Track activity
    today_str = str(date.today())
    if username not in daily_activity:
        daily_activity[username] = {}
    daily_activity[username][today_str] = daily_activity[username].get(today_str, 0) + 1
    save_data()

    # @flik Grok AI
    try:
        bot_info = await context.bot.get_me()
        bot_mention = "@" + bot_info.username.lower()
    except Exception:
        bot_mention = "@flikbot"

    if bot_mention in lower or "@flik" in lower:
        query_text = (
            text
            .replace(bot_mention, "")
            .replace("@Flik", "")
            .replace("@flik", "")
            .strip()
        )
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
            f"🔥 *Your Personal Referral Link* (from @{username})\n\n"
            f"🔗 {TELEGRAM_GROUP_LINK}\n\n"
            "Share this link with friends!",
            parse_mode="Markdown"
        )
        return

    if "twitter" in lower or " x " in lower or lower == "x":
        await update.message.reply_text(f"🔥 Official X: {X_LINK}")
        return

    if "tg" in lower or "telegram" in lower:
        await update.message.reply_text(f"🔥 Join the group: {TELEGRAM_GROUP_LINK}")
        return

    if lower.strip() == "ca" or " ca " in f" {lower} ":
        await update.message.reply_text(f"🔥 CA: {CA_TEXT}")
        return

    if "narrative" in lower:
        try:
            with open('narrative.jpg', 'rb') as img:
                await update.message.reply_photo(img, caption="🔥 $FLIK Narrative")
        except FileNotFoundError:
            await update.message.reply_text("🔥 $FLIK Narrative image not found yet.")
        return

    if "mascot" in lower:
        try:
            with open('mascot.jpg', 'rb') as img:
                await update.message.reply_photo(img, caption="🔥 $FLIK Mascot")
        except FileNotFoundError:
            await update.message.reply_text("🔥 $FLIK Mascot image not found yet.")
        return

    if "website" in lower or "site" in lower:
        await update.message.reply_text(f"🔥 Official Website: {WEBSITE_LINK}")
        return

    if "rules" in lower:
        try:
            with open('rules.jpg', 'rb') as img:
                await update.message.reply_photo(img, caption="📜 Group Rules")
        except FileNotFoundError:
            await update.message.reply_text("📜 Group Rules image not found yet.")
        return

async def show_help_menu(update: Update):
    menu_text = (
        "🔥 *FLIK BOT MENU — What I Can Do*\n\n"
        "📌 *@flik* \\+ any question → Grok AI\n"
        "🔗 *referral* → Get your personal referral link\n"
        "🐦 *x* or *twitter* → Official X link\n"
        "📱 *tg* or *telegram* → Group link\n"
        "🔢 *ca* → Contract address\n"
        "📖 *narrative* → $FLIK story image\n"
        "🔥 *mascot* → Lighter mascot image\n"
        "🌐 *website* or *site* → Official website\n"
        "📜 *rules* → Group rules image\n\n"
        "Type any of these words anytime — I respond instantly\\!\n"
        "$FLIK ARMY TO THE MOON 🔥"
    )
    await update.message.reply_text(menu_text, parse_mode="MarkdownV2")

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set!")

    app = Application.builder().token(TOKEN).build()

    # FIX: single MessageHandler handles both welcome and messages
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        welcome
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))

    print("🤖 FLIK BOT IS LIVE 🔥")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
