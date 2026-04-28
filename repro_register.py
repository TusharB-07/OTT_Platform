import requests
import json

def test_register():
    url = "http://127.0.0.1:5000/api/auth/register"
    payload = {
        "Email": "newuser@test.com",
        "Password": "password123",
        "FirstName": "New",
        "LastName": "User",
        "DOB": "1990-01-01"
    }
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_register()
