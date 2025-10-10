import json
import sqlite3
import os
import time
import redis
def get_redis_client():
    try:
        client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            socket_timeout=1,
            decode_responses=True
        )
        client.ping()
        return client
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"Redis connection error: {e}")
        return None

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ApplicationBuilder
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TELEGRAM_USER_ID = os.getenv('TELEGRAM_USER_ID')

# Initialize Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
REDIS_AVAILABLE = True

try:
    # Test Redis connection
    redis_client.ping()
    
    # Set up initial configuration if it doesn't exist
    if not redis_client.exists('config'):
        initial_config = {
            "authorized_users": [TELEGRAM_USER_ID],
            "monitoring": "false"
        }
        redis_client.set('config', json.dumps(initial_config))
        print(f"Initial configuration set up with user ID: {TELEGRAM_USER_ID}")
except redis.ConnectionError as e:
    print(f"Redis connection error: {e}")
    REDIS_AVAILABLE = False

# Initialize SQLite database
conn = sqlite3.connect('bot.db')
cursor = conn.cursor()

async def check_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.effective_user.id)
        print(f"Checking auth for user ID: {user_id}")
        config = json.loads(redis_client.get('config') or '{}')
        print(f"Current config: {config}")
        if user_id not in config.get('authorized_users', []):
            print(f"User {user_id} not in authorized users list")
            await update.message.reply_text("Unauthorized")
            return False
        print(f"User {user_id} authorized successfully")
        return True
    except Exception as e:
        print(f"Error in check_auth: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Start command received")
    if not await check_auth(update, context): 
        print("Auth check failed")
        return
    try:
        print("Setting monitoring to true")
        redis_client.set('monitoring', 'true')
        print("Sending response message")
        await update.message.reply_text("Monitoring started")
        print("Start command completed successfully")
    except Exception as e:
        print(f"Error starting bot: {e}")

if __name__ == "__main__":
    print("Script starting...")
    main()

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

async def main():
    try:
        print("Loading environment variables...")
        load_dotenv()
        token = os.getenv('TELEGRAM_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_TOKEN not found in environment or .env file")
        
        print(f"Starting bot with token: {token[:5]}...{token[-5:]}")
        
        # Test Redis connection
        print("Testing Redis connection...")
        try:
            redis_client.ping()
            print("Redis connection successful")
            config = redis_client.get('config')
            print(f"Current Redis config: {config}")
        except redis.ConnectionError as e:
            print(f"Redis connection error: {e}")
            return
        
        # Configure proxy if needed
        proxy_url = os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')
        if proxy_url:
            print(f"Using proxy: {proxy_url}")
            builder = Application.builder().token(token).proxy_url(proxy_url)
        else:
            print("No proxy configured")
            builder = Application.builder().token(token)
        
        # Configure connection pool for reliability
        builder.connection_pool_size(8).connect_timeout(30.0).read_timeout(30.0)
        
        print("Building application...")
        app = builder.build()
        
        print("Adding command handlers...")
        app.add_handler(CommandHandler('start', start))
        app.add_handler(CommandHandler('stop', stop))
        app.add_handler(CommandHandler('status', status))
        app.add_handler(CommandHandler('history', history))
        app.add_handler(CommandHandler('summary', summary))
        app.add_handler(CommandHandler('feedback', feedback))
        
        print("Starting bot polling...")
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"Error in main function: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Script starting...")
    import asyncio
    asyncio.run(main())