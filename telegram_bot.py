import json
import sqlite3
import redis
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

redis_client = redis.Redis(host='localhost', port=6379, db=0)
conn = sqlite3.connect('bot.db')
cursor = conn.cursor()

async def check_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    config = json.loads(redis_client.get('config') or '{}')
    if user_id not in config.get('authorized_users', []):
        await update.message.reply_text("Unauthorized")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context): return
    redis_client.set('monitoring', 'true')
    await update.message.reply_text("Monitoring started")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context): return
    redis_client.set('monitoring', 'false')
    await update.message.reply_text("Monitoring stopped")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context): return
    cursor.execute('SELECT SUM(profit), COUNT(*) FROM trades WHERE timestamp > ?', (time.time() - 24*3600,))
    profit, trades = cursor.fetchone()
    hit_rate = float(redis_client.get('ml_hit_rate') or 0)
    chain = redis_client.get('active_chain').decode() if redis_client.get('active_chain') else 'Polygon'
    await update.message.reply_markdown_v2(f"**Status:**\n- Profit: ${profit:.2f}\n- Trades: {trades}\n- Hit Rate: {hit_rate:.1%}\n- Chain: {chain}")

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context): return
    cursor.execute('SELECT * FROM recent_trades LIMIT 20')
    trades = cursor.fetchall()
    buttons = [[InlineKeyboardButton("Next", callback_data='next_page', style={'padding': '10px'}),
                InlineKeyboardButton("Prev", callback_data='prev_page', style={'padding': '10px'})]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(f"Recent Trades:\n{trades}", reply_markup=reply_markup)

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context): return
    cursor.execute('SELECT SUM(profit), COUNT(*) FROM trades WHERE timestamp > ?', (time.time() - 24*3600,))
    profit, trades = cursor.fetchone()
    hit_rate = float(redis_client.get('ml_hit_rate') or 0)
    chain = redis_client.get('active_chain').decode() if redis_client.get('active_chain') else 'Polygon'
    await update.message.reply_markdown_v2(f"**Daily Summary:**\n- Profit: ${profit:.2f}\n- Trades: {trades}\n- Hit Rate: {hit_rate:.1%}\n- Chain: {chain}")

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context): return
    message = ' '.join(context.args)
    cursor.execute('INSERT INTO feedback (timestamp, message) VALUES (?, ?)', (time.time(), message))
    conn.commit()
    await update.message.reply_text("Feedback submitted!")

def main():
    app = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('stop', stop))
    app.add_handler(CommandHandler('status', status))
    app.add_handler(CommandHandler('history', history))
    app.add_handler(CommandHandler('summary', summary))
    app.add_handler(CommandHandler('feedback', feedback))
    app.run_polling()