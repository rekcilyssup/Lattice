"""Shared query-classification helpers used by both ai.py and chat.py."""
from __future__ import annotations

import re


def is_metric_query(query: str) -> bool:
    q = query.lower()
    metric_hints = [
        'how many',
        'how much',
        'number',
        'count',
        'metric',
        'value',
        'figure',
        'projected',
        'current',
        'demand',
        'status',
        'percent',
        'percentage',
        'rate',
        'cost',
        'budget',
        'investment',
        'mld',
        'mgd',
        'km',
        'crore',
        'lakh',
    ]
    return bool(re.search(r'\d', q)) or any(h in q for h in metric_hints)


def is_temporal_query(query: str) -> bool:
    q = query.lower()
    temporal_hints = [
        'year',
        'years',
        'month',
        'months',
        'phase',
        'phases',
        'stage',
        'stages',
        'timeline',
        'latency',
        'transition',
        'roadmap',
        'before',
        'after',
        'during',
        'year 1',
        'year 2',
        'year 3',
        'year 4',
        'year 5',
    ]
    return bool(re.search(r'\b(20\d{2}|19\d{2}|\d+\s*-\s*\d+)\b', q)) or any(h in q for h in temporal_hints)


def is_technical_query(query: str) -> bool:
    q = query.lower()
    technical_hints = [
        'technical architecture',
        'architecture',
        'model',
        'models',
        'algorithm',
        'framework',
        'pipeline',
        'u-net',
        'unet',
        'cnn',
        'lstm',
        'resnet',
        'contrastive',
        'xgboost',
        'how does it work',
        'section 7.3',
    ]
    return any(h in q for h in technical_hints)


def is_social_query(query: str) -> bool:
    q = query.lower()
    social_hints = [
        'social',
        'community',
        'family model',
        'citizen',
        'stakeholder',
        'inclusion',
        'accessibility',
        'adoption',
        'digital literacy',
        'elder',
        'youth',
        'children',
        'training',
        'governance',
    ]
    return any(h in q for h in social_hints)


def query_clauses(query: str) -> list[str]:
    parts = re.split(r'\?+|;|,\s+|\s+\band\b\s+|\s+\bbut\b\s+|\s+\bplus\b\s+', query, flags=re.IGNORECASE)
    return [p.strip() for p in parts if len(p.strip()) >= 8]


def is_multi_part_query(query: str) -> bool:
    q = query.lower()
    if q.count('?') >= 2:
        return True
    if len(re.findall(r'\band\b', q)) >= 1 and len(query_clauses(query)) >= 2:
        return True
    return any(k in q for k in ['first', 'second', 'third', '1)', '2)', '3)', 'part 1', 'part 2'])

