import os
import json
import requests
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler, CallbackQueryHandler

TOKEN = os.getenv('BOT_TOKEN')
XAI_API_KEY = os.getenv('XAI_API_KEY')

ADMINS = ["FLICKABICFLIK", "FLICKABIC", "flickabic"]

# Change these when ready
X_LINK = "https://x.com/FLICKABICFLIK"
TELEGRAM_GROUP_LINK = "https://t.me/yourgroup"   # ← YOUR ACTUAL GROUP LINK
WEBSITE_LINK = "https://flickabic.com"
CA_TEXT = "TBA"

# Chat history (last 20 messages per group)
chat_history = {}

def load_data():
    global chat_history, daily_activity
    try:
        with open('chat_history.json', 'r') as f:
            chat_history = json.load(f)
    except:
        pass
    try:
        with open('daily_activity.json', 'r') as f:
            daily_activity.update(json.load(f))
    except:
        pass

def save_data():
    with open('chat_history.json', 'w') as f:
        json.dump(chat_history, f, indent=2)
    with open('daily_activity.json', 'w') as f:
        json.dump(daily_activity, f, indent=2)

load_data()

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

async def get_grok_response(query: str, username: str, chat_id: int):
    history_str = ""
    if chat_id in chat_history and chat_history[chat_id]:
        recent = chat_history[chat_id][-20:]
        history_str = "\n\nRecent chat history:\n" + "\n".join([f"@{msg['username']}: {msg['text']}" for msg in recent])

    if not XAI_API_KEY:
        return "🔥 Flik is here! Ask me anything."
    try:
        messages = [
            {"role": "system", "content": "You are Flik — savage, hype, funny, wise leader of $FLIK. You know the group vibe from the chat history."},
            {"role": "user", "content": f"Recent context:{history_str}\n\n@{username} asks: {query}"}
        ]
        r = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"},
            json={"model": "grok-4", "messages": messages}
        )
        return r.json()['choices'][0]['message']['content']
    except:
        return "🔥 Flik is cooking... Try again soon!"

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        keyboard = [[InlineKeyboardButton("✅ I'm not a bot", callback_data="verify_human")]]
        await update.message.reply_text(
            f"🔥 Welcome @{member.username or member.first_name} to the $FLIK Army!\n\nClick the button below to verify you're not a bot.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "verify_human":
        await query.edit_message_text("✅ **Verified!** Welcome to the $FLIK community 🔥")

async def show_help_menu(update: Update):
    menu_text = (
        "🔥 **FLIK BOT MENU — What I Can Do**\n\n"
        "📌 **@flik** + any question → Grok AI (reads recent chat for vibe checks)\n"
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if await anti_spam(update, context):
        return

    text = update.message.text
    lower = text.lower()
    user = update.message.from_user
    username = user.username or "unknown"
    chat_id = str(update.message.chat_id)

    # Save message to chat history
    if chat_id not in chat_history:
        chat_history[chat_id] = []
    chat_history[chat_id].append({"username": username, "text": text})
    if len(chat_history[chat_id]) > 20:
        chat_history[chat_id] = chat_history[chat_id][-20:]
    save_data()

    # @flik Grok AI (with chat history)
    bot_info = await context.bot.get_me()
    bot_mention = "@" + bot_info.username.lower()
    if bot_mention in lower or "@flik" in lower or "@Flik" in text:
        query_text = text.replace(bot_mention, "").replace("@Flik", "").replace("@flik", "").strip()
        if query_text:
            response = await get_grok_response(query_text, username, chat_id)
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("🔥 What's on your mind? Ask me anything.")
        return

    # MENU
    if "menu" in lower or "what can you do" in lower:
        await show_help_menu(update)
        return

    # REFERRAL (leads to group)
    if "referral" in lower:
        bot_info = await context.bot.get_me()
        link = f"https://t.me/{bot_info.username}?start={username}"
        await update.message.reply_text(
            f"🔥 **Your Personal Referral Link**\n\n"
            f"🔗 {TELEGRAM_GROUP_LINK}\n\n"
            f"Referred by @{username}\n\n"
            f"Share this link with friends!\n"
            f"When they join using your link you both get rewards in the $FLIK Army 🔥"
        )
        return

    # RAID HYPE
    if "raid" in lower:
        await update.message.reply_text("🔥 RAID TIME! $FLIK ARMY — LET'S LIGHT THE TIMELINE ON FIRE! DROP THE TWEET, JOIN THE RAID, TO THE MOON! 🚀")
        return

    # GREETINGS → Grok AI (NEW)
    greetings = ["hello", "hey", "hi", "what’s up", "whats up", "anyone here"]
    if any(g in lower for g in greetings):
        response = await get_grok_response(text, username, chat_id)
        await update.message.reply_text(response)
        return

    # Keyword responses
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

    if "narrative" in lower:
        await update.message.reply_photo(open('narrative.jpg', 'rb'), caption="🔥 $FLIK Narrative")
        return

    if "mascot" in lower:
        await update.message.reply_photo(open('mascot.jpg', 'rb'), caption="🔥 $FLIK Mascot")
        return

    if "website" in lower or "site" in lower:
        await update.message.reply_text(f"🔥 Official Website: {WEBSITE_LINK}")
        return

    if "rules" in lower:
        await update.message.reply_photo(open('rules.jpg', 'rb'), caption="📜 Group Rules")
        return

async def hourly_shoutout(context: ContextTypes.DEFAULT_TYPE):
    if not daily_activity:
        return
    today_str = str(date.today())
    today_counts = {u: counts.get(today_str, 0) for u, counts in daily_activity.items() if today_str in counts}
    if not today_counts:
        return
    top_user = max(today_counts, key=today_counts.get)
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=f"🏆 **HOURLY SHOUTOUT!**\n\n@{top_user} is the most active member right now! 🔥 Keep the energy going $FLIK Army!"
    )

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.job_queue.run_repeating(hourly_shoutout, interval=3600, first=60)

    print("🤖 FLIK BOT IS LIVE 🔥 — GREETINGS + CHAT HISTORY + UNLIMITED GROK")
    app.run_polling()

if __name__ == '__main__':
    main()
