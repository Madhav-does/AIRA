"""
ARIA Web Control
Opens URLs and performs web searches in the default browser.
"""

import webbrowser
import urllib.parse

# Search URL prefixes for popular sites
SEARCH_URLS = {
    'youtube': 'https://www.youtube.com/results?search_query=',
    'google': 'https://www.google.com/search?q=',
    'github': 'https://github.com/search?q=',
    'amazon': 'https://www.amazon.in/s?k=',
    'flipkart': 'https://www.flipkart.com/search?q=',
    'twitter': 'https://twitter.com/search?q=',
    'x': 'https://x.com/search?q=',
    'reddit': 'https://www.reddit.com/search/?q=',
    'wikipedia': 'https://en.wikipedia.org/wiki/Special:Search?search=',
    'stackoverflow': 'https://stackoverflow.com/search?q=',
    'bing': 'https://www.bing.com/search?q=',
    'duckduckgo': 'https://duckduckgo.com/?q=',
}

# Direct homepage URLs for popular sites
DIRECT_URLS = {
    'youtube': 'https://www.youtube.com',
    'google': 'https://www.google.com',
    'gmail': 'https://mail.google.com',
    'google drive': 'https://drive.google.com',
    'drive': 'https://drive.google.com',
    'google docs': 'https://docs.google.com',
    'google sheets': 'https://sheets.google.com',
    'google meet': 'https://meet.google.com',
    'meet': 'https://meet.google.com',
    'github': 'https://github.com',
    'amazon': 'https://www.amazon.in',
    'flipkart': 'https://www.flipkart.com',
    'netflix': 'https://www.netflix.com',
    'spotify': 'https://open.spotify.com',
    'twitter': 'https://twitter.com',
    'x': 'https://x.com',
    'reddit': 'https://www.reddit.com',
    'linkedin': 'https://www.linkedin.com',
    'instagram': 'https://www.instagram.com',
    'facebook': 'https://www.facebook.com',
    'whatsapp web': 'https://web.whatsapp.com',
    'whatsapp': 'https://web.whatsapp.com',
    'maps': 'https://maps.google.com',
    'google maps': 'https://maps.google.com',
    'translate': 'https://translate.google.com',
    'google translate': 'https://translate.google.com',
    'chatgpt': 'https://chat.openai.com',
    'openai': 'https://chat.openai.com',
    'stackoverflow': 'https://stackoverflow.com',
    'wikipedia': 'https://www.wikipedia.org',
}


def search_web(query: str, site: str = '') -> str:
    """
    Search the web, optionally on a specific site.

    Args:
        query: Search terms.
        site:  Optional site name (e.g. 'youtube', 'google').

    Returns:
        The URL that was opened.
    """
    encoded = urllib.parse.quote_plus(query)
    site_lower = site.lower().strip() if site else ''

    if site_lower in SEARCH_URLS:
        url = SEARCH_URLS[site_lower] + encoded
    elif site_lower:
        # Generic site search via Google "site:" operator fallback
        url = f'https://www.google.com/search?q={encoded}+site:{site_lower}'
    else:
        url = f'https://www.google.com/search?q={encoded}'

    webbrowser.open(url)
    print(f"[WebControl] Searched: {url}")
    return url


def open_url(url: str) -> str:
    """
    Open a URL or a known site name in the default browser.

    Args:
        url: A full URL or a known site name like 'youtube', 'gmail'.

    Returns:
        The resolved URL.
    """
    url_lower = url.lower().strip()

    # Check direct URL map first
    if url_lower in DIRECT_URLS:
        resolved = DIRECT_URLS[url_lower]
        webbrowser.open(resolved)
        print(f"[WebControl] Opened: {resolved}")
        return resolved

    # Ensure protocol prefix
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    webbrowser.open(url)
    print(f"[WebControl] Opened: {url}")
    return url
