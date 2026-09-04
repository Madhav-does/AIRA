"""
ARIA n8n Automation & Assistant Integration
Connects ARIA to Madhav's n8n cloud instance (https://trafal.app.n8n.cloud).
Capabilities:
  - query_n8n: Send queries/tasks to the n8n AI Assistant or workflow
  - trigger_n8n_workflow: Trigger custom webhook automations in n8n
  - open_n8n: Open the n8n Assistant or dashboard in browser
"""

import urllib.request
import urllib.parse
import json
import webbrowser
import os

DEFAULT_BASE_URL      = "https://trafal.app.n8n.cloud"
DEFAULT_ASSISTANT_URL = "https://trafal.app.n8n.cloud/assistant/e52fad6b-2f9c-4fb9-8183-23265a60f071"
DEFAULT_WEBHOOK_URL   = "https://trafal.app.n8n.cloud/webhook/e52fad6b-2f9c-4fb9-8183-23265a60f071"


def _get_n8n_config() -> dict:
    """Load n8n settings from aria_config.json if available."""
    try:
        import config as cfg
        c = cfg.load_config()
        return c.get('n8n', {})
    except Exception:
        return {}


def query_n8n(prompt: str, webhook_url: str = "") -> str:
    """
    Send a prompt or command to your n8n assistant or workflow.
    Returns the answer or execution result returned by n8n.
    """
    conf = _get_n8n_config()
    target_url = webhook_url or conf.get('webhook_url') or DEFAULT_WEBHOOK_URL

    payload = {
        "chatInput": prompt,
        "message": prompt,
        "query": prompt,
        "source": "ARIA",
        "user": conf.get("user_name", "Madhav")
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ARIA-Assistant/1.0"
        }
        api_key = conf.get("api_key")
        if api_key:
            headers["X-N8N-API-KEY"] = api_key

        req = urllib.request.Request(target_url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as res:
            raw = res.read().decode('utf-8', errors='replace')
            try:
                parsed = json.loads(raw)
                # Look for common response fields
                if isinstance(parsed, dict):
                    output = parsed.get('output') or parsed.get('response') or parsed.get('text') or parsed.get('message')
                    if output:
                        return str(output)
                    return json.dumps(parsed, indent=2)
                elif isinstance(parsed, list) and parsed:
                    first = parsed[0]
                    if isinstance(first, dict):
                        return first.get('output') or first.get('text') or json.dumps(first)
                return str(raw)
            except Exception:
                return raw.strip() if raw.strip() else "n8n workflow executed successfully."

    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        if e.code == 404:
            return (
                "Connected to your n8n instance at trafal.app.n8n.cloud, but this workflow is currently inactive. "
                "Please toggle the workflow to 'Active' in your n8n editor, or verify the webhook path!"
            )
        return f"n8n returned HTTP {e.code}: {body[:120]}"
    except Exception as e:
        return f"Could not reach n8n: {e}"


def trigger_n8n_workflow(workflow_name_or_path: str, data: dict = None) -> str:
    """
    Trigger a specific n8n workflow by webhook path or name.
    E.g. workflow_name_or_path='morning-routine' or 'backup'
    """
    conf = _get_n8n_config()
    base = conf.get('base_url') or DEFAULT_BASE_URL

    # If full URL is passed
    if workflow_name_or_path.startswith('http://') or workflow_name_or_path.startswith('https://'):
        target_url = workflow_name_or_path
    else:
        clean_path = workflow_name_or_path.strip().lstrip('/')
        target_url = f"{base}/webhook/{clean_path}"

    payload = data or {}
    payload.setdefault("source", "ARIA")
    payload.setdefault("event", workflow_name_or_path)

    try:
        req_data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ARIA-Assistant/1.0"
        }
        api_key = conf.get("api_key")
        if api_key:
            headers["X-N8N-API-KEY"] = api_key

        req = urllib.request.Request(target_url, data=req_data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as res:
            res_text = res.read().decode('utf-8', errors='replace')
            return f"n8n workflow '{workflow_name_or_path}' triggered successfully. Output: {res_text[:120]}"

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return f"Workflow '{workflow_name_or_path}' is not registered or not activated in n8n."
        return f"n8n error {e.code}: {e}"
    except Exception as e:
        return f"Failed to trigger n8n workflow '{workflow_name_or_path}': {e}"


def open_n8n() -> str:
    """Open your n8n assistant or cloud dashboard in the default browser."""
    conf = _get_n8n_config()
    target = conf.get('assistant_url') or DEFAULT_ASSISTANT_URL
    webbrowser.open(target)
    print(f"[N8N] Opened n8n assistant in browser: {target}")
    return f"Opened your n8n assistant at {target}."
