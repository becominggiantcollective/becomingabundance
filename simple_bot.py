import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import redis
import json

# Load environment variables
load_dotenv(override=True)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_USER_ID = os.getenv('TELEGRAM_USER_ID')

print("Environment variables loaded:")
print(f"TELEGRAM_TOKEN (full): {TELEGRAM_TOKEN}")
print(f"TELEGRAM_USER_ID: {TELEGRAM_USER_ID}")

# Initialize Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

try:
    redis_client.ping()
    config = {
        "authorized_users": [TELEGRAM_USER_ID],
        "monitoring": "false"
    }
    redis_client.set('config', json.dumps(config))
    print("Redis configuration updated:", redis_client.get('config'))
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
    # Create the Application
    print("Building application...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    print("Adding command handlers...")
    app.add_handler(CommandHandler("start", start))
    
    # Start polling
    print("Starting bot polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    print("Script starting...")
    main()