# dppmini/validators.py


def normalize_gtin(s: str) -> str:
    """Keep only digits; trims spaces/dashes/etc."""
    return "".join(ch for ch in str(s).strip() if ch.isdigit())


def gtin_check_digit(body: str) -> int:
    total = 0
    for i, ch in enumerate(reversed(body)):  # right→left
        d = int(ch)
        total += d * (3 if i % 2 == 0 else 1)  # 3,1,3,1...
    return (10 - (total % 10)) % 10


def gtin_is_valid(s: str) -> bool:
    s = normalize_gtin(s)
    if not s.isdigit() or len(s) not in (8, 12, 13, 14):
        return False
    data, check = s[:-1], int(s[-1])
    return gtin_check_digit(data) == check
