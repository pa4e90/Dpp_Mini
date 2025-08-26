from dppmini.validators import gtin_is_valid, normalize_gtin


def test_valid_ean13():
    assert gtin_is_valid("4006381333931")
    assert gtin_is_valid("5901234123457")
    assert gtin_is_valid("1212121212234")


def test_valid_ean8_and_upc():
    assert gtin_is_valid("12345670")  # EAN-8
    assert gtin_is_valid("036000291452")  # GTIN-12/UPC-A


def test_invalid_check_digit():
    assert not gtin_is_valid("4006381333932")
    assert not gtin_is_valid("036000291453")
    assert not gtin_is_valid("55123458")


def test_wrong_length_and_nondigits():
    assert not gtin_is_valid("12345")
    assert not gtin_is_valid("123456789012345")
    assert not gtin_is_valid("40063813339A1")


def test_normalization_helps():
    raw = "4006 3813-33931"
    assert normalize_gtin(raw) == "4006381333931"
    assert gtin_is_valid(raw)
