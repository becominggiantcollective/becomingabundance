import sys
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

import redis
import json

# Your Telegram user ID
USER_ID = "7096087358"

try:
    # Connect to Redis
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    # Test connection
    print("Testing Redis connection...")
    redis_client.ping()
    print("Redis connection successful!")
    
    # Set up configuration
    config = {
        "authorized_users": [USER_ID],
        "monitoring": "false"
    }
    
    # Store in Redis
    redis_client.set('config', json.dumps(config))
    print(f"Configuration stored successfully: {config}")
    
except Exception as e:
    print(f"Error: {str(e)}")