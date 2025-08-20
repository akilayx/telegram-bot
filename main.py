import os
import logging
import sqlite3
from datetime import datetime
from threading import Thread

from flask import Flask, send_file
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import pandas as pd
import openpyxl

# ----------------- Logging -----------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------- Environment -----------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("❌ TELEGRAM_TOKEN is not set!")
    exit(1)

DB_NAME = "transactions.db"

# ----------------- Flask -----------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# ----------------- Database -----------------
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

# ----------------- Language -----------------
LANGUAGES = {
    "en": {
        "start": "🤖 *Personal Finance Tracker Bot*\n\nWelcome! Use /add to start tracking finances.",
        "added": "✅ Transaction Added: {amount} | {category}\nNew Balance: {balance}",
        "error": "⚠️ Invalid input! Use /add <amount> <category> [description]",
        "balance": "💰 Balance: {balance}\nIncome: {income}\nExpenses: {expenses}\nTransactions: {count}",
        "help": "Commands:\n/add <amount> <category> [description]\n/balance\n/history\n/export\n/report\n/clear\n/setlang <en/ru/kg>\n/categories",
        "cleared": "🗑️ All transactions cleared!",
        "lang_set": "🌐 Language set to {lang}",
        "categories": "📂 Your categories:\n{cats}",
        "history_header": "📜 Transaction History:",
        "no_transactions": "No transactions yet."
    },
    "ru": {
        "start": "🤖 *Бот учёта финансов*\n\nДобро пожаловать! Используй /add для отслеживания расходов.",
        "added": "✅ Транзакция добавлена: {amount} | {category}\nНовый баланс: {balance}",
        "error": "⚠️ Неверный ввод! Используй /add <сумма> <категория> [описание]",
        "balance": "💰 Баланс: {balance}\nДоходы: {income}\nРасходы: {expenses}\nТранзакций: {count}",
        "help": "Команды:\n/add <сумма> <категория> [описание]\n/balance\n/history\n/export\n/report\n/clear\n/setlang <en/ru/kg>\n/categories",
        "cleared": "🗑️ Все транзакции удалены!",
        "lang_set": "🌐 Язык установлен на {lang}",
        "categories": "📂 Ваши категории:\n{cats}",
        "history_header": "📜 История транзакций:",
        "no_transactions": "Транзакций пока нет."
    },
    "kg": {
        "start": "🤖 *Каржы эсеп боту*\n\nКош келдиңиз! /add менен чыгымдарды көзөмөлдөңүз.",
        "added": "✅ Транзакция кошулду: {amount} | {category}\nЖаңы баланс: {balance}",
        "error": "⚠️ Туура эмес! /add <сумма> <категория> [сүрөттөмө]",
        "balance": "💰 Баланс: {balance}\nКиреше: {income}\nЧыгым: {expenses}\nТранзакциялар: {count}",
        "help": "Буйруктар:\n/add <сумма> <категория> [сүрөттөмө]\n/balance\n/history\n/export\n/report\n/clear\n/setlang <en/ru/kg>\n/categories",
        "cleared": "🗑️ Бардык транзакциялар тазаланды!",
        "lang_set": "🌐 Тил орнотулду: {lang}",
        "categories": "📂 Категорияларыңыз:\n{cats}",
        "history_header": "📜 Транзакциялар тарыхы:",
        "no_transactions": "Транзакциялар жок."
    }
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

# ----------------- Bot Handlers -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    await update.message.reply_text(LANGUAGES[lang]["start"], parse_mode='Markdown')

async def add_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    lang = get_user_language(user_id)

    if len(context.args) < 2:
        await update.message.reply_text(LANGUAGES[lang]["error"])
        return

    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text(LANGUAGES[lang]["error"])
        return

    category = context.args[1].lower()
    description = " ".join(context.args[2:]) if len(context.args) > 2 else category

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO transactions (user_id, username, date, amount, category, description) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), amount, category, description)
    )
    conn.commit()
    c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ?", (user_id,))
    balance = c.fetchone()[0] or 0
    conn.close()

    await update.message.reply_text(
        LANGUAGES[lang]["added"].format(amount=amount, category=category, balance=balance),
        parse_mode='Markdown'
    )

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT amount FROM transactions WHERE user_id = ?", (user_id,))
    amounts = [row[0] for row in c.fetchall()]
    conn.close()
    if not amounts:
        await update.message.reply_text(LANGUAGES[lang]["no_transactions"])
        return
    total_balance = sum(amounts)
    income = sum(a for a in amounts if a > 0)
    expenses = sum(a for a in amounts if a < 0)
    await update.message.reply_text(LANGUAGES[lang]["balance"].format(
        balance=total_balance, income=income, expenses=abs(expenses), count=len(amounts)
    ), parse_mode='Markdown')

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT date, amount, category, description FROM transactions WHERE user_id = ? ORDER BY date DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text(LANGUAGES[lang]["no_transactions"])
        return
    msg = LANGUAGES[lang]["history_header"] + "\n"
    for row in rows[:20]:  # Show last 20
        msg += f"{row[0]} | {row[1]} | {row[2]} | {row[3]}\n"
    await update.message.reply_text(msg)

async def clear_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text(LANGUAGES[lang]["cleared"])

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = context.args[0].lower() if context.args else "en"
    if lang_code not in LANGUAGES:
        await update.message.reply_text("Invalid language code. Use: en, ru, kg")
        return
    set_user_language(user_id, lang_code)
    await update.message.reply_text(LANGUAGES[lang_code]["lang_set"].format(lang=lang_code))

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT DISTINCT category FROM transactions WHERE user_id = ?", (user_id,))
    cats = [row[0] for row in c.fetchall()]
    conn.close()
    await update.message.reply_text(LANGUAGES[lang]["categories"].format(cats=", ".join(cats) if cats else "None"))

async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(f"SELECT * FROM transactions WHERE user_id = {user_id}", conn)
    conn.close()
    if df.empty:
        await update.message.reply_text(LANGUAGES[lang]["no_transactions"])
        return
    file_path = f"transactions_{user_id}.xlsx"
    df.to_excel(file_path, index=False)
    await update.message.reply_document(open(file_path, "rb"))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    await update.message.reply_text(LANGUAGES[lang]["help"], parse_mode='Markdown')

# ----------------- Main -----------------
def start_bot():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_transaction))
    application.add_handler(CommandHandler("balance", show_balance))
    application.add_handler(CommandHandler("history", show_history))
    application.add_handler(CommandHandler("clear", clear_transactions))
    application.add_handler(CommandHandler("setlang", set_language))
    application.add_handler(CommandHandler("categories", show_categories))
    application.add_handler(CommandHandler("export", export_excel))
    application.add_handler(CommandHandler("help", help_command))

    logger.info("✅ Telegram Bot is starting...")
    application.run_polling(stop_signals=None)

# ----------------- Run -----------------
if __name__ == "__main__":
    Thread(target=run_flask).start()  # Start Flask for Render
    start_bot()
