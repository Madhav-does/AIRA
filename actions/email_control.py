"""
ARIA Email Control
Draft and compose emails via Gmail or default Windows mail client.
"""

import urllib.parse
import webbrowser
import os


def compose_email(to: str = "", subject: str = "", body: str = "", client: str = "gmail") -> str:
    """
    Open an email draft with pre-filled recipient, subject, and message body.
    client can be 'gmail' (opens in browser) or 'default' (opens system mail app).
    """
    encoded_to   = urllib.parse.quote(to)
    encoded_subj = urllib.parse.quote(subject)
    encoded_body = urllib.parse.quote(body)

    if client.lower() == "gmail":
        url = (
            f"https://mail.google.com/mail/?view=cm&fs=1"
            f"&to={encoded_to}&su={encoded_subj}&body={encoded_body}"
        )
        webbrowser.open(url)
        dest = to if to else "a new message"
        print(f"[EmailControl] Opened Gmail draft to: {to} | Subject: {subject}")
        return f"Opened Gmail draft to {dest} with subject '{subject}'."
    else:
        # System mailto protocol
        mailto = f"mailto:{encoded_to}?subject={encoded_subj}&body={encoded_body}"
        try:
            os.startfile(mailto)
            return f"Opened default mail client for {to}."
        except Exception:
            # Fallback to Gmail
            url = f"https://mail.google.com/mail/?view=cm&fs=1&to={encoded_to}&su={encoded_subj}&body={encoded_body}"
            webbrowser.open(url)
            return f"Opened Gmail draft to {to}."
