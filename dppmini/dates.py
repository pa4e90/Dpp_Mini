from datetime import date

def expiry_is_future_or_today(iso: str) -> bool:
    try:
        return date.fromisoformat(str(iso)) >= date.today()
    except Exception:
        return False