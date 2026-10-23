"""Deterministic group triggers: configured names or a structured self mention."""
import json
import re
import unicodedata


def normalized_text(value):
    return unicodedata.normalize('NFKC', str(value or '')).casefold()


def mentions_self(message, own_mid):
    if not own_mid:
        return False
    try:
        metadata = message.get('contentMetadata') or {}
        mention = metadata.get('MENTION')
        if isinstance(mention, str):
            mention = json.loads(mention)
        entries = (mention or {}).get('MENTIONEES', [])
        return isinstance(entries, list) and any(
            isinstance(item, dict) and item.get('M') == own_mid for item in entries)
    except (ValueError, TypeError, AttributeError):
        return False


def should_reply_in_group(message, own_mid, user_names):
    if message.get('from') == own_mid or int(message.get('contentType') or 0) not in (0,1,7):
        return False
    text = normalized_text(message.get('text'))
    names = [normalized_text(name.strip()) for name in re.split(r'[,，、;；\n]+', str(user_names or '')) if name.strip()]
    return mentions_self(message, own_mid) or any(name in text for name in names)
