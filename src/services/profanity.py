from __future__ import annotations

from typing import List, Tuple


def detect_profanity(transcript: str, profanity_list: List[str], context: int = 40) -> Tuple[bool, list[str], str]:
    lowered = transcript.lower()
    found = []
    excerpt = ""
    for p in profanity_list:
        idx = lowered.find(p)
        if idx != -1:
            found.append(p)
            if not excerpt:
                start = max(0, idx - context)
                end = min(len(transcript), idx + len(p) + context)
                excerpt = transcript[start:end].strip()
    return (len(found) > 0, found, excerpt)
