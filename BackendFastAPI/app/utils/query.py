"""Shared query-classification helpers used by both ai.py and chat.py."""  # Module docstring
from __future__ import annotations  # Future compatibility for annotations

import re  # Regular expressions


def is_metric_query(query: str) -> bool:  # Checks if query is asking for quantities
    q = query.lower()  # Convert to lowercase
    metric_hints = [  # Keywords indicating metric queries
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
    return bool(re.search(r'\d', q)) or any(h in q for h in metric_hints)  # Has numbers or metric keywords


def is_temporal_query(query: str) -> bool:  # Checks if query is asking for time-related info
    q = query.lower()  # Convert to lowercase
    temporal_hints = [  # Keywords indicating temporal queries
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
    return bool(re.search(r'\b(20\d{2}|19\d{2}|\d+\s*-\s*\d+)\b', q)) or any(h in q for h in temporal_hints)  # Has years/ranges or temporal keywords


def is_technical_query(query: str) -> bool:  # Checks if query is asking for technical details
    q = query.lower()  # Convert to lowercase
    technical_hints = [  # Keywords indicating technical queries
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
    return any(h in q for h in technical_hints)  # Contains technical keywords


def is_social_query(query: str) -> bool:  # Checks if query is asking for social/community info
    q = query.lower()  # Convert to lowercase
    social_hints = [  # Keywords indicating social queries
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
    return any(h in q for h in social_hints)  # Contains social keywords


def query_clauses(query: str) -> list[str]:  # Splits query into logical clauses
    parts = re.split(r'\?+|;|,\s+|\s+\band\b\s+|\s+\bbut\b\s+|\s+\bplus\b\s+', query, flags=re.IGNORECASE)  # Split on separators
    return [p.strip() for p in parts if len(p.strip()) >= 8]  # Return clauses with min length


def is_multi_part_query(query: str) -> bool:  # Checks if query has multiple sub-parts
    q = query.lower()  # Convert to lowercase
    if q.count('?') >= 2:  # Multiple question marks
        return True
    if len(re.findall(r'\band\b', q)) >= 1 and len(query_clauses(query)) >= 2:  # "and" with multiple clauses
        return True
    return any(k in q for k in ['first', 'second', 'third', '1)', '2)', '3)', 'part 1', 'part 2'])  # Sequential keywords