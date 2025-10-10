import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import redis
import json

# Load environment variables
load_dotenv(override=True)  # Force reload of environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_USER_ID = os.getenv('TELEGRAM_USER_ID')

print("Environment variables loaded:")
print(f"TELEGRAM_TOKEN (full): {TELEGRAM_TOKEN}")
print(f"TELEGRAM_USER_ID: {TELEGRAM_USER_ID}")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not found in .env file")
print(f"Bot starting with token ending in: ...{TELEGRAM_TOKEN[-10:]}")
print(f"Authorized user ID: {TELEGRAM_USER_ID}")

# Set up initial configuration for Redis
config = {
    "authorized_users": [TELEGRAM_USER_ID],
    "monitoring": "false"
}

# Initialize Redis
print("Connecting to Redis...")
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Set up initial configuration
try:
    redis_client.ping()
    if not redis_client.exists('config'):
        config = {
            "authorized_users": [TELEGRAM_USER_ID],
            "monitoring": "false"
        }
        redis_client.set('config', json.dumps(config))
    print("Redis configuration:", redis_client.get('config'))
except redis.ConnectionError as e:
    print(f"Redis connection error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Start command received from user {update.effective_user.id}")
    user_id = str(update.effective_user.id)
    try:
        config = json.loads(redis_client.get('config') or '{}')
        if user_id not in config.get('authorized_users', []):
            print(f"User {user_id} not authorized")
            await update.message.reply_text("Unauthorized")
            return
        
        redis_client.set('monitoring', 'true')
        print(f"User {user_id} authorized, monitoring started")
        await update.message.reply_text("Monitoring started")
    except Exception as e:
        error_msg = f"Error in start command: {str(e)}"
        print(error_msg)
        await update.message.reply_text(error_msg)

def main():
    # Create application and add handlers
    builder = Application.builder().token(TELEGRAM_TOKEN)
    
    # Configure connection settings
    builder.connection_pool_size(8)
    builder.connect_timeout(30.0)
    builder.read_timeout(30.0)
    builder.get_updates_read_timeout(30.0)
    
    # Configure proxy if needed
    proxy_url = os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')
    if proxy_url:
        print(f"Using proxy: {proxy_url}")
        builder.proxy_url(proxy_url)
    else:
        print("No proxy configured, using default connection")
    
    # Build application
    print("Building application...")
    app = builder.build()
    app.add_handler(CommandHandler("start", start))
    
    # Start bot
    print("Starting bot...")
    try:
        print("Starting bot polling...")
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"Error running bot: {e}")
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())