import requests

BASE = "http://127.0.0.1:8000"

# 1. create a session
resp = requests.post(f"{BASE}/get_session", json={"project_name": "demo_project"})
print(resp.json())
session_key = resp.json()["session_key"]

# 2. set a structure
resp = requests.post(f"{BASE}/set_structure", json={
    "session_key": session_key,
    "structure": {
        "name": "user_profile",
        "description": "basic user profile",
        "fields": [
            {"name": "username", "type": "string", "required": True},
            {"name": "age", "type": "int"}
        ]
    }
})
print(resp.json())

# 3. add a message
resp = requests.post(f"{BASE}/set_message", json={
    "session_key": session_key,
    "message": {
        "name": "example_user",
        "content": {
            "payload": {
                "__structure__": "user_profile",
                "data": {"username": "jane", "age": 34}
            }
        }
    }
})
print(resp.json())

# 4. get project data
resp = requests.get(f"{BASE}/get_project_data", params={"session_key": session_key})
print(resp.json())
