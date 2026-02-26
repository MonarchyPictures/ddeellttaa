import requests
import time

def test_telegram_status():
    try:
        response = requests.get("http://localhost:8000/api/telegram/status")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Wait a bit for server to be fully ready if needed
    time.sleep(2)
    test_telegram_status()
