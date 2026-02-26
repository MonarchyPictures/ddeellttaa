import requests
import time

def check_backend():
    url = "http://localhost:8000/health"
    print(f"Checking backend at {url}...")
    for i in range(10):
        try:
            response = requests.get(url, timeout=5)
            print(f"Attempt {i+1}: Success! Status: {response.status_code}")
            print(f"Response: {response.json()}")
            return True
        except Exception as e:
            print(f"Attempt {i+1}: Failed - {e}")
            time.sleep(2)
    return False

if __name__ == "__main__":
    check_backend()
