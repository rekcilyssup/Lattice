import re


def create_snippet(text: str, max_len: int = 320) -> str:
    text = re.sub(r"\s+", " ", text).strip()  # collapse the newlines a PDF leaves behind
    if len(text) <= max_len:
        return text
    return text[:max_len].strip() + '...'  # hard cut, marked so the UI knows it is partial


def overlap_score(query: str, candidate: str) -> float:
    q = set(re.findall(r"[a-zA-Z0-9]+", query.lower()))  # unique query terms
    c = set(re.findall(r"[a-zA-Z0-9]+", candidate.lower()))  # unique candidate terms
    if not q:
        return 0.0
    return len(q.intersection(c)) / len(q)  # Jaccard-style coverage of the query terms
