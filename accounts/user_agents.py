"""Turn a raw User-Agent string into a short "Browser on OS" label.

Deliberately small and dependency-free: it only has to recognize the
common browsers and operating systems well enough for a customer to tell
their own sign-ins from someone else's.
"""

# Order matters: most User-Agents name several browsers for compatibility
# (Edge says "Chrome" and "Safari"; Chrome says "Safari"), so the more
# specific tokens are checked first.
BROWSERS = [
    ("Edg", "Edge"),
    ("OPR/", "Opera"),
    ("SamsungBrowser/", "Samsung Internet"),
    ("Firefox/", "Firefox"),
    ("FxiOS/", "Firefox"),
    ("CriOS/", "Chrome"),
    ("Chrome/", "Chrome"),
    ("Safari/", "Safari"),
]

# iOS and Android before macOS and Linux: an iPhone claims to be "like
# Mac OS X", and Android is Linux underneath.
OPERATING_SYSTEMS = [
    ("Windows", "Windows"),
    ("iPhone", "iOS"),
    ("iPad", "iPadOS"),
    ("Android", "Android"),
    ("CrOS", "ChromeOS"),
    ("Macintosh", "macOS"),
    ("Linux", "Linux"),
]

UNKNOWN_DEVICE = "Unknown device"


def _first_match(user_agent: str, table: list[tuple[str, str]]) -> str | None:
    return next((label for token, label in table if token in user_agent), None)


def describe_user_agent(user_agent: str) -> str:
    """A short label such as "Firefox on Windows".

    Falls back to "Unknown browser" or "unknown OS" for whichever half
    isn't recognized, and to "Unknown device" when neither is.
    """
    browser = _first_match(user_agent, BROWSERS)
    system = _first_match(user_agent, OPERATING_SYSTEMS)
    if browser is None and system is None:
        return UNKNOWN_DEVICE
    return f"{browser or 'Unknown browser'} on {system or 'unknown OS'}"
