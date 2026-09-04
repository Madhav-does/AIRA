"""
ARIA LinkedIn & Social Media Automation
Create, polish, and auto-publish LinkedIn posts.
Works via:
  1. n8n automation webhook (hands-free automated posting through your n8n workflow)
  2. Browser one-click sharing (copies text to clipboard, opens LinkedIn share modal)
  3. Direct LinkedIn REST API (if access token is configured)
"""

import urllib.parse
import webbrowser
import pyperclip
import json
import os


def generate_linkedin_draft(topic_or_idea: str) -> str:
    """
    Format a high-engagement LinkedIn post from a raw topic or idea.
    Includes hook, structured insights, and hashtags.
    """
    # If the user already provided a full post, keep it
    if len(topic_or_idea.split()) > 25 and any(h in topic_or_idea for h in ['#', '\n\n', '1.']):
        return topic_or_idea

    # Clean and format
    lines = [
        f"🚀 Quick thoughts on {topic_or_idea.strip()}:",
        "",
        "Here are 3 key takeaways I've observed recently:",
        f"1️⃣ Innovation moves faster when you automate the routine tasks.",
        f"2️⃣ Practical AI workflows compound over time.",
        f"3️⃣ The real differentiator is execution and consistency.",
        "",
        "What's your perspective on this? Drop your thoughts below! 👇",
        "",
        "#AI #Productivity #Technology #Automation #FutureOfWork"
    ]
    return "\n".join(lines)


def post_to_linkedin(content: str, via: str = "auto") -> str:
    """
    Publish or prepare a LinkedIn post.
    via options:
      - 'auto': tries n8n webhook first if available, then opens browser with draft
      - 'n8n': sends directly to your n8n workflow for automated posting
      - 'browser': copies content to clipboard and opens LinkedIn composer
      - 'api': calls direct LinkedIn API if access token is present
    """
    if not content:
        return "No content provided to post."

    # 1. Check if direct LinkedIn Access Token is configured in aria_config.json
    try:
        import config as cfg
        c = cfg.load_config()
        li_conf = c.get('linkedin', {})
        api_token = li_conf.get('access_token')
        person_urn = li_conf.get('person_urn')
    except Exception:
        api_token = None
        person_urn = None

    if (via == "api" or via == "auto") and api_token and person_urn:
        res = _publish_via_api(content, api_token, person_urn)
        if res.startswith("[OK]"):
            return res

    # 2. Check if n8n has a linkedin webhook configured
    try:
        from actions.n8n_control import trigger_n8n_workflow, _get_n8n_config
        n8n_cfg = _get_n8n_config()
        li_webhook = n8n_cfg.get('webhooks', {}).get('linkedin', 'linkedin')
        if via in ["n8n", "auto"] and n8n_cfg.get('enabled', True):
            # Attempt sending to n8n linkedin webhook
            n8n_res = trigger_n8n_workflow(li_webhook, {"action": "create_post", "content": content, "platform": "linkedin"})
            if "successfully" in n8n_res.lower():
                return f"Sent post to your n8n workflow for automatic publishing! Content: '{content[:60]}...'"
    except Exception:
        pass

    # 3. Browser one-click sharing (Universal fallback)
    try:
        pyperclip.copy(content)
    except Exception:
        pass

    encoded = urllib.parse.quote(content)
    # LinkedIn feed with active post composer
    url = f"https://www.linkedin.com/feed/?shareActive=true&text={encoded}"
    webbrowser.open(url)
    print(f"[LinkedInControl] Opened LinkedIn composer with draft copied to clipboard.")
    return (
        f"I've drafted your LinkedIn post and copied it to your clipboard. "
        f"LinkedIn is open on your screen—just review and click Post!"
    )


def _publish_via_api(text: str, access_token: str, person_urn: str) -> str:
    """Post directly using LinkedIn Community Management API."""
    import urllib.request
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": text
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as res:
            return f"[OK] Published directly to LinkedIn! (Status: {res.status})"
    except Exception as e:
        return f"[API Error]: {e}"
