import redis
import json

# Connect to Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Check Redis state
print("Current Redis State:")
print("-" * 20)

try:
    # Get config
    config = redis_client.get('config')
    print(f"Config: {config}")
    
    # Get monitoring status
    monitoring = redis_client.get('monitoring')
    print(f"Monitoring: {monitoring}")
    
except Exception as e:
    print(f"Error checking Redis: {e}")