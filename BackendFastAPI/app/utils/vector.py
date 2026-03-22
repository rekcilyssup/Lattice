import math


def normalize(values: list[float]) -> list[float]:
    mag = math.sqrt(sum(v * v for v in values))
    if mag == 0:
        return values
    return [v / mag for v in values]


def to_pgvector(values: list[float], dim: int) -> str:
    vals = values[:dim] + [0.0] * max(0, dim - len(values))
    return '[' + ','.join(str(v) for v in vals[:dim]) + ']'
