from app import expiry_is_future_or_today
from dppmini.dates import expiry_is_future_or_today
from datetime import date

def test_expiry_today_ok():
    assert expiry_is_future_or_today(date.today().isoformat())

def test_expiry_past_false():
    assert not expiry_is_future_or_today("2000-01-01")