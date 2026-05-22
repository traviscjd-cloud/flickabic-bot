import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TOKEN = os.getenv('BOT_TOKEN')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        text = update.message.text.lower()
        if "@flik" in text or "@Flik" in update.message.text:
            await update.message.reply_text("🔥 Flik is here! Ask me anything.")
        elif any(word in text for word in ["flick", "moon", "fire"]):
            await update.message.reply_text("🔥 THAT'S THE ENERGY! $FLIK TO THE MOON")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 FLIK BOT IS LIVE 🔥")
    app.run_polling()

if __name__ == '__main__':
    main()
