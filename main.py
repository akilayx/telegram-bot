import os
import logging
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    MessageHandler, filters
)
import openpyxl
from openpyxl.styles import Font, Alignment
import tempfile
import pandas as pd
from flask import Flask, request

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -----------------------------
# Telegram Token
# -----------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN environment variable is required")
    exit(1)

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    logger.error("WEBHOOK_URL environment variable is required")
    exit(1)

# -----------------------------
# Database
# -----------------------------
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

# -----------------------------
# Language support
# -----------------------------
LANGUAGES = {
    "en": {"start": "🤖 Welcome! Use /add, /balance, /history, /export, /report, /clear, /setlang, /categories, /help."},
    "ru": {"start": "🤖 Добро пожаловать! Используйте /add, /balance, /history, /export, /report, /clear, /setlang, /categories, /help."},
    "kg": {"start": "🤖 Кош келдиңиз! /add, /balance, /history, /export, /report, /clear, /setlang, /categories, /help."}
}

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
    c.execute("INSERT OR REPLACE INTO user_preferences (user_id, language) VALUES (?, ?)", (user_id, language))
    conn.commit()
    conn.close()

# -----------------------------
# Telegram Handlers
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    await update.message.reply_text(LANGUAGES[lang]["start"])

# Пример для add, balance и других команд оставим пустым, но структуру можно добавить
async def add_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ /add работает! (добавь логику)")

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💰 /balance работает! (добавь логику)")

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 /history работает! (добавь логику)")

async def export_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 /export работает! (добавь логику)")

async def generate_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📈 /report работает! (добавь логику)")

async def clear_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🗑️ /clear работает! (добавь логику)")

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌐 /setlang работает! (добавь логику)")

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📂 /categories работает! (добавь логику)")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ /help работает! (добавь логику)")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📂 Файл обработан! (добавь логику)")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f'Update {update} caused error {context.error}')

# -----------------------------
# Flask + Webhook
# -----------------------------
app = Flask(__name__)
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("add", add_transaction))
application.add_handler(CommandHandler("balance", show_balance))
application.add_handler(CommandHandler("history", show_history))
application.add_handler(CommandHandler("export", export_transactions))
application.add_handler(CommandHandler("report", generate_report))
application.add_handler(CommandHandler("clear", clear_transactions))
application.add_handler(CommandHandler("setlang", set_language))
application.add_handler(CommandHandler("categories", show_categories))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(
    filters.Document.FileExtension("xlsx") | filters.Document.FileExtension("xls") | filters.Document.FileExtension("csv"),
    handle_file
))
application.add_error_handler(error_handler)

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "OK"

@app.route("/")
def home():
    return "Bot is running!"

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    import asyncio
    asyncio.run(application.bot.set_webhook(WEBHOOK_URL))
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

