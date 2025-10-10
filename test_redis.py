import redis

def test_redis_connection():
    try:
        # Create Redis client
        redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            socket_timeout=2,
            decode_responses=True
        )
        
        # Test connection with ping
        response = redis_client.ping()
        print("Redis connection successful!")
        print(f"Ping response: {response}")
        
        # Test basic operations
        redis_client.set('test_key', 'test_value')
        value = redis_client.get('test_key')
        print(f"Test key-value operation successful. Retrieved: {value}")
        
        # Clean up
        redis_client.delete('test_key')
        
    except redis.ConnectionError as e:
        print(f"Could not connect to Redis: {e}")
        print("Please make sure Redis server is running on localhost:6379")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_redis_connection()