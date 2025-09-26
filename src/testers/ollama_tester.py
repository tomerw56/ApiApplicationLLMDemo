import requests
import json

url = "http://localhost:11434/api/chat"

payload = {
    "model": "llama3",
    "messages": [
        {"role": "user", "content": "how are you?"}
    ]
}

resp = requests.post(url, json=payload, stream=True)

full_response = ""

for line in resp.iter_lines():
    if not line:
        continue
    try:
        data = json.loads(line.decode("utf-8"))
    except json.JSONDecodeError:
        continue  # skip bad lines

    # When done, stop
    if data.get("done", False):
        break

    # Append assistant content (if present)
    message = data.get("message", {})
    content = message.get("content")
    if content:
        full_response += content

print("\n=== Final Assistant Response ===\n")
print(full_response)
