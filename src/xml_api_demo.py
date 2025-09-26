import json
import os.path
from typing import Any

import requests
from pathlib import Path
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3"  # or whichever model you pulled
xml_file="./resources/ApiDemo.xml"



def _parse_content_obj(o: Any) -> str:
    """Recursively extract a string from common Ollama content shapes."""
    if o is None:
        return ""
    if isinstance(o, str):
        return o
    if isinstance(o, (int, float)):
        return str(o)
    if isinstance(o, dict):
        # common packaging: {"type":"output","parts":["..."]}
        if "parts" in o and isinstance(o["parts"], list):
            return "".join(str(p) for p in o["parts"])
        # sometimes direct text keys:
        for key in ("text", "output", "message", "content", "body", "result"):
            if key in o:
                val = _parse_content_obj(o[key])
                if val:
                    return val
        # fallback: try find first string leaf
        for v in o.values():
            val = _parse_content_obj(v)
            if val:
                return val
    if isinstance(o, list):
        parts = [_parse_content_obj(i) for i in o]
        return "".join(p for p in parts if p)
    return ""

def extract_ollama_content(data: Any) -> str:
    """Extract assistant text from the Ollama response JSON (various possible shapes)."""
    if data is None:
        return ""

    # Case: top-level "message"
    if isinstance(data, dict) and "message" in data:
        return _parse_content_obj(data["message"])

    # Case: choices (openai-like)
    if isinstance(data, dict) and "choices" in data:
        choices = data["choices"]
        if isinstance(choices, list) and len(choices) > 0:
            # prefer first choice
            c0 = choices[0]
            # choice.message.content or choice.content.parts or choice.text
            if isinstance(c0, dict):
                # new style: c0["message"]["content"]
                if "message" in c0:
                    msg = c0.get("message")
                    txt = _parse_content_obj(msg)
                    if txt:
                        return txt
                # older style: c0["content"] or c0["text"]
                if "content" in c0:
                    txt = _parse_content_obj(c0["content"])
                    if txt:
                        return txt
                if "text" in c0:
                    txt = _parse_content_obj(c0["text"])
                    if txt:
                        return txt
            # fallback: parse whole choice
            txt = _parse_content_obj(c0)
            if txt:
                return txt

    # other possible keys
    for key in ("output", "outputs", "result", "data"):
        if isinstance(data, dict) and key in data:
            txt = _parse_content_obj(data[key])
            if txt:
                return txt

    # If none matched, try to stringify first string leaf
    if isinstance(data, (dict, list)):
        txt = _parse_content_obj(data)
        if txt:
            return txt

    # final fallback: pretty-printed JSON or raw text
    try:
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception:
        return str(data)


def query_ollama(prompt: str):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
        },
        stream=False,
    )
    if response.status_code != 200:
        # try to include JSON error if available, otherwise raw text
        err_body = None
        try:
            err_body = response.json()
            err_text = json.dumps(err_body, indent=2, ensure_ascii=False)
        except ValueError:
            err_text = response.text.strip()
        raise RuntimeError(f"Ollama returned HTTP {response.status_code}:\n{err_text}")
    full_response=""
    for line in response.iter_lines():
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

    return full_response
def main():
    demo_requests = {
        "Add_Color":"Add a color option to api 'blue' ",
        "Add_Range":"Modify Year to range from 1950 to 1995",
    "Remove_Field_Mistake_in_spelling":"Remove number of onwners",
    "expend_a_message":"expand GetClientTransactionRequest to include a color selection",
    "suggest_a_message":"suggest a request and response to get car's owner "}


    xml_content = Path(xml_file).read_text()

    for demo_request in demo_requests.keys():
        prompt = f"""Here is an API definition in XML:{xml_content}"""
        print(f"processing {demo_request} {demo_requests[demo_request]}")
        prompt=f"""{prompt} {demo_requests[demo_request]} """
        prompt=f""" {prompt} Return only the updated well-formed XML. if you have notes
         keep them in xml comments"""
        output = query_ollama(prompt)
        print("\n=== Result ===\n")
        print(output)

        with open(os.path.join("..",f"{demo_request}.xml"), "w") as f:
            f.write(output)

if __name__ == "__main__":
    main()
