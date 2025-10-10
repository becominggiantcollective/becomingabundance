import redis
import json
import os
from dotenv import load_dotenv

def setup_bot_config():
    try:
        # Load environment variables
        load_dotenv()
        user_id = os.getenv('TELEGRAM_USER_ID')
        
        # Connect to Redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # Test connection
        redis_client.ping()
        
        # Create initial config with your user ID
        config = {
            "authorized_users": [user_id],
            "monitoring": "false"
        }
        
        # Store config in Redis
        redis_client.set('config', json.dumps(config))
        
        # Verify the config was stored
        stored_config = redis_client.get('config')
        print("Configuration stored successfully:")
        print(json.loads(stored_config))
        
    except Exception as e:
        print(f"Error setting up configuration: {e}")

if __name__ == "__main__":
    setup_bot_config()