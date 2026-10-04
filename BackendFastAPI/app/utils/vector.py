import math


def normalize(values: list[float]) -> list[float]:
    mag = math.sqrt(sum(v * v for v in values))  # vector magnitude
    if mag == 0:
        return values  # guard: a zero vector has no direction to normalise
    return [v / mag for v in values]  # unit length, so cosine distance is meaningful


def to_pgvector(values: list[float], dim: int) -> str:
    vals = values[:dim] + [0.0] * max(0, dim - len(values))  # pad or truncate to the fixed width
    return '[' + ','.join(str(v) for v in vals[:dim]) + ']'  # the "[0.1,0.2]" literal pgvector parses
