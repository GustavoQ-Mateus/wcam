SEPARATOR = " · "
SYSTEMS = (
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Android", "Android"),
    ("Windows", "Windows"),
    ("CrOS", "ChromeOS"),
    ("Mac OS X", "macOS"),
    ("Linux", "Linux"),
)
BROWSERS = (
    ("EdgiOS/", "Edge"),
    ("EdgA/", "Edge"),
    ("Edg/", "Edge"),
    ("SamsungBrowser/", "Samsung Internet"),
    ("OPR/", "Opera"),
    ("FxiOS/", "Firefox"),
    ("Firefox/", "Firefox"),
    ("CriOS/", "Chrome"),
    ("Chrome/", "Chrome"),
    ("Safari/", "Safari"),
)


def describe_device(user_agent: str) -> str | None:
    parts = [part for part in (first_match(user_agent, SYSTEMS), first_match(user_agent, BROWSERS)) if part]
    return SEPARATOR.join(parts) or None


def first_match(user_agent: str, markers: tuple[tuple[str, str], ...]) -> str | None:
    return next((name for marker, name in markers if marker in user_agent), None)
