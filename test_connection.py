import urllib.request
import json

def test_telegram_connection():
    token = "8167906366:AAH_odDw5rQY8sPe7nw_fkmv5nRtAhzm6DU"
    url = f"https://api.telegram.org/bot{token}/getMe"
    
    print(f"Testing connection to Telegram API...")
    try:
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode())
        print("Connection successful!")
        print(f"Bot info: {data}")
        return True
    except Exception as e:
        print(f"Connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_telegram_connection()