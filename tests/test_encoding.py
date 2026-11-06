import pytest

from app.encoding import encode_bnr, format_word, validate_range


def test_validate_range_accepts_boundaries():
    validate_range(-10, -10, 10)
    validate_range(10, -10, 10)


def test_validate_range_rejects_out_of_range_value():
    with pytest.raises(ValueError, match="fuera del rango"):
        validate_range(10.01, -10, 10)


def test_validate_range_rejects_inverted_bounds():
    with pytest.raises(ValueError, match="mínimo"):
        validate_range(0, 5, -5)


def test_encoding_has_32_bits_and_odd_parity():
    word = encode_bnr(12, label=0xA5, sdi=2, ssm=1, scale=0.5)
    binary, hexadecimal = format_word(word)

    assert len(binary) == 32
    assert binary.count("1") % 2 == 1
    assert hexadecimal == f"0x{word:08X}"


def test_encoding_rejects_out_of_range_fields():
    with pytest.raises(ValueError, match="SDI"):
        encode_bnr(0, label=1, sdi=4)


def test_encoding_rejects_unrepresentable_bnr_value():
    with pytest.raises(ValueError, match="19 bits BNR"):
        encode_bnr(1 << 18, label=1)


def test_encoding_rejects_value_not_aligned_to_resolution():
    with pytest.raises(ValueError, match="resolución configurada"):
        encode_bnr(1, label=1, scale=0.3)
