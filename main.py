import os
import logging
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import openpyxl
from openpyxl.styles import Font, Alignment
import tempfile
import pandas as pd
from flask import Flask
from threading import Thread

# ----------------------------
# Logging
# ----------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------------------
# Telegram Token
# ----------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN environment variable is required")
    exit(1)

# ----------------------------
# Database
# ----------------------------
DB_NAME = "transactions.db"

def init_database():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  username TEXT,
                  date TEXT NOT NULL,
                  amount REAL NOT NULL,
                  category TEXT NOT NULL,
                  description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_preferences
                 (user_id INTEGER PRIMARY KEY,
                  language TEXT DEFAULT 'en')''')
    conn.commit()
    conn.close()

init_database()

# ----------------------------
# Languages
# ----------------------------
LANGUAGES = {
    "en": {
        "start": "Welcome to Personal Finance Bot!",
        "add_success": "Transaction added successfully!",
        "balance": "Your current balance is: {balance}",
        "help": "Available commands: /start, /add, /balance, /history, /export, /report, /setlang, /categories, /clear, /help",
        "error": "An error occurred."
    },
    "ru": {
        "start": "Добро пожаловать в Бот Личных Финансов!",
        "add_success": "Транзакция успешно добавлена!",
        "balance": "Ваш текущий баланс: {balance}",
        "help": "Доступные команды: /start, /add, /balance, /history, /export, /report, /setlang, /categories, /clear, /help",
        "error": "Произошла ошибка."
    },
    "kg": {
        "start": "Жеке Финанс Ботко кош келиңиз!",
        "add_success": "Транзакция ийгиликтүү кошулду!",
        "balance": "Сиздин учурдагы баланс: {balance}",
        "help": "Колдонмодо жеткиликтүү буйруктар: /start, /add, /balance, /history, /export, /report, /setlang, /categories, /clear, /help",
        "error": "Ката кетти."
    }
}

# ----------------------------
# User language
# ----------------------------
def get_user_language(user_id: int) -> str:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT language FROM user_preferences WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "en"

def set_user_language(user_id: int, language: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO user_preferences (user_id, language) VALUES (?, ?)",
        (user_id, language)
    )
    conn.commit()
    conn.close()

# ----------------------------
# Handlers
# ----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_language(update.effective_user.id)
    await update.message.reply_text(LANGUAGES[lang]['start'])

async def add_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Dummy implementation, replace with parsing logic
    lang = get_user_language(update.effective_user.id)
    await update.message.reply_text(LANGUAGES[lang]['add_success'])

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_language(update.effective_user.id)
    # Dummy balance
    balance = 1000
    await update.message.reply_text(LANGUAGES[lang]['balance'].format(balance=balance))

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Transaction history is under development.")

async def export_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Exporting transactions is under development.")

async def generate_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Generating report is under development.")

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Please provide language code (en/ru/kg).")
        return
    lang_code = context.args[0].lower()
    if lang_code not in LANGUAGES:
        await update.message.reply_text("Unsupported language.")
        return
    set_user_language(update.effective_user.id, lang_code)
    await update.message.reply_text(f"Language set to {lang_code}.")

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Categories: Food, Transport, Bills, Other")

async def clear_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Clearing transactions is under development.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_language(update.effective_user.id)
    await update.message.reply_text(LANGUAGES[lang]['help'])

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("File handling is under development.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# ----------------------------
# Main bot
# ----------------------------
def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_transaction))
    application.add_handler(CommandHandler("balance", show_balance))
    application.add_handler(CommandHandler("history", show_history))
    application.add_handler(CommandHandler("export", export_transactions))
    application.add_handler(CommandHandler("report", generate_report))
    application.add_handler(CommandHandler("setlang", set_language))
    application.add_handler(CommandHandler("categories", show_categories))
    application.add_handler(CommandHandler("clear", clear_transactions))
    application.add_handler(CommandHandler("help", help_command))

    # File handler
    application.add_handler(
        MessageHandler(
            filters.Document.FileExtension(["xlsx", "xls", "csv"]),
            handle_file
        )
    )

    # Error handler
    application.add_error_handler(error_handler)

    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=None)

# ----------------------------
# Flask server for Render
# ----------------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# ----------------------------
# Start both
# ----------------------------
if __name__ == '__main__':
    Thread(target=run_flask).start()
    main()
