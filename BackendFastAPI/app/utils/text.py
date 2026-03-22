import re


def create_snippet(text: str, max_len: int = 320) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].strip() + '...'


def overlap_score(query: str, candidate: str) -> float:
    q = set(re.findall(r"[a-zA-Z0-9]+", query.lower()))
    c = set(re.findall(r"[a-zA-Z0-9]+", candidate.lower()))
    if not q:
        return 0.0
    return len(q.intersection(c)) / len(q)
