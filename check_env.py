from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv('TELEGRAM_TOKEN')
print(f"Token from .env: {token}")
print(f"Token length: {len(token) if token else 'N/A'}")
print(f"User ID from .env: {os.getenv('TELEGRAM_USER_ID')}")