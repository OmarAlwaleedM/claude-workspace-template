"""
profanity.py — Player name profanity filter.

Checks player names against a banned words list to prevent offensive
or inappropriate names from appearing on the projector display.
"""

# Banned words list — lowercase. 4+ char words use substring matching,
# 3 or fewer char words only match as the full normalized name.
BANNED_WORDS = {
    # Racial slurs
    "nigger", "nigga", "chink", "spic", "wetback", "kike", "gook",
    "coon", "darkie", "beaner", "paki", "towelhead", "sandnigger",
    "redskin", "zipperhead", "chinaman",
    # Gendered slurs
    "bitch", "whore", "slut", "cunt", "thot",
    # Vulgar
    "fuck", "shit", "dick", "cock", "pussy", "asshole", "bastard",
    "wanker", "twat", "bollocks", "piss", "tits", "boobs", "penis",
    "vagina", "dildo", "butthole",
    # Homophobic
    "faggot", "dyke", "tranny",
    # Other offensive
    "retard", "retarded", "nazi", "hitler", "rape", "molest",
    "pedo", "pedophile", "incel",
    # Impersonation / religious trolling
    "admin", "host", "system", "moderator",
}

# Short words (3 chars or fewer) — only block if the ENTIRE name matches
SHORT_BANNED = {"ass", "fag", "hoe", "cum", "fuk", "nig", "god"}

# Leet-speak substitutions
_LEET_MAP = str.maketrans("013457@$!", "oieastasi")


def _normalize(text: str) -> str:
    """Lowercase, apply leet-speak mapping, strip non-alpha characters."""
    text = text.lower().translate(_LEET_MAP)
    return "".join(ch for ch in text if ch.isalpha())


def is_name_inappropriate(name: str) -> bool:
    """
    Check if a player name is inappropriate.

    Returns True if the name should be blocked.
    """
    normalized = _normalize(name)

    # Reject empty / whitespace-only / symbols-only names
    if not normalized:
        return True

    # Short banned words — full match only
    if normalized in SHORT_BANNED:
        return True

    # Longer banned words — substring match
    for word in BANNED_WORDS:
        if word in normalized:
            return True

    return False
