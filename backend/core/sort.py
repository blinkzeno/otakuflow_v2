"""Natural sort key so page_2 sorts before page_10."""

import re

_SPLIT = re.compile(r"(\d+)")


def natural_key(value: str) -> list[int | str]:
    return [
        int(part) if part.isdigit() else part.lower()
        for part in _SPLIT.split(value)
    ]
