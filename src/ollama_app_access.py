import requests
import ollama
import json
import logging
import sys
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

BASE = "http://127.0.0.1:8000"


# ---------- API Helpers ----------

def call_api(method, path, **kwargs):
    url = f"{BASE}{path}"
    logger.debug(f"Calling {url} with {kwargs}")
    resp = requests.request(method, url, **kwargs)
    resp.raise_for_status()
    return resp.json()


def show_project(session_key):
    data = call_api("GET", "/get_project_data", params={"session_key": session_key})
    logger.info("\n=== Project Data ===")
    logger.info(json.dumps(data, indent=2))
    return data


# ---------- LLM Helpers ----------

def ask_ollama(prompt):
    response = ollama.chat(
        model="llama3",  # or llama3.1 etc.
        messages=[{"role": "user", "content": prompt}]
    )
    return response["message"]["content"]


def extract_all_json(text: str):
    """Extract all JSON objects from LLM output (handles multiple commands)."""
    blocks = []
    start = None
    depth = 0
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    blocks.append(json.loads(text[start:i+1]))
                except json.JSONDecodeError:
                    pass
                start = None
    return blocks


# ---------- Normalization ----------

def normalize_structure(cmd: dict) -> dict:
    """Ensure set_structure payload matches API contract."""
    if "structure" in cmd and isinstance(cmd["structure"], dict):
        name, fields = cmd["structure"]["name"], cmd["structure"]["fields"]
        return {"name": name, "fields": fields}
    return cmd


def normalize_message(cmd: dict) -> dict:
    """Ensure set_message payload matches API contract."""
    if "message" in cmd and isinstance(cmd["message"], dict):
        name, content = cmd["message"]["name"],cmd["message"]["payload"]
        return {"name": name, "payload": content}
    return cmd


# ---------- Dispatcher ----------

def process_action(action: str, payload: dict, session_key: str):
    """Execute a single action with normalized payload."""
    if action == "set_structure":
        payload = {"session_key": session_key, "structure": normalize_structure(payload)}
        return call_api("POST", "/set_structure", json=payload)

    elif action == "set_message":
        payload = {"session_key": session_key, "message": normalize_message(payload)}
        return call_api("POST", "/set_message", json=payload)

    elif action == "get_project_data":
        return show_project(session_key)

    else:
        return {"error": f"Unknown action {action}"}


# ---------- Demo Workflow ----------

def demo():
    schema = call_api("GET", "/get_schema")

    # 1. Create project session
    sess = call_api("POST", "/get_session", json={"project_name": "demo_project"})
    session_key = sess["session_key"]
    logger.info(f"✅ Session created: {session_key}")

    # 2. Define interactions (natural language)
    instructions = [
        "On project demo_project add structure user_profile with fields username:string(required), age:int, bio:string",
        "On project demo_project add message jane with structure type user_profile {username:'jane', age:34, bio:'hello!'} ",
        "Display project demo_project",
        "Alter struct user_profile on project demo_project add field email:string(required)",
        "Display project demo_project"
    ]

    # 3. Run interactions
    for instr in instructions:
        logger.info(f"\n👉 Instruction: {instr}")
        llm_prompt = f"""
        You are an assistant controlling an API. 
        Here is the schema you MUST follow exactly:

        {json.dumps(schema, indent=2)}

        Instruction: {instr}
        """
        llm_output = ask_ollama(llm_prompt)
        logger.info(f"🔹 LLM Raw Output:\n{llm_output}")

        # Parse all JSON objects
        actions = extract_all_json(llm_output)
        logger.info(f"<UNK> Actions:\n{json.dumps(actions, indent=2)}")
        if not actions:
            logger.error("⚠️ No valid JSON extracted, skipping...")

            continue

        # Execute each command
        for action_block in actions:
            for action, payload in action_block.items():
                result = process_action(action, payload, session_key)
                logger.info(f"✅ API Response: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    demo()
