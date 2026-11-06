from decimal import Decimal, InvalidOperation


def validate_range(value, minimum, maximum):
    if minimum > maximum:
        raise ValueError("El valor mínimo no puede superar al máximo.")
    if not minimum <= value <= maximum:
        raise ValueError("El valor está fuera del rango permitido.")


def encode_bnr(value, label, sdi=0, ssm=0, scale=1, offset=0):
    """Encode a demo BNR word with a signed 19-bit two's-complement data field."""
    if not 0 <= label <= 0xFF:
        raise ValueError("Label debe estar entre 0 y 255.")
    if not 0 <= sdi <= 0b11:
        raise ValueError("SDI debe estar entre 0 y 3.")
    if not 0 <= ssm <= 0b11:
        raise ValueError("SSM debe estar entre 0 y 3.")
    try:
        value = Decimal(str(value))
        scale = Decimal(str(scale))
        offset = Decimal(str(offset))
    except InvalidOperation as error:
        raise ValueError("El valor, la escala y el offset deben ser numéricos.") from error

    if not all(number.is_finite() for number in (value, scale, offset)):
        raise ValueError("El valor, la escala y el offset deben ser finitos.")
    if scale <= 0:
        raise ValueError("La escala debe ser mayor que cero.")

    scaled_value = (value - offset) / scale
    if scaled_value != scaled_value.to_integral_value():
        raise ValueError("El valor no es representable con la resolución configurada.")
    data_value = int(scaled_value)
    data_minimum = -(1 << 18)
    data_maximum = (1 << 18) - 1
    if not data_minimum <= data_value <= data_maximum:
        raise ValueError("El valor codificado no cabe en los 19 bits BNR.")

    word = label | (sdi << 8) | ((data_value & 0x7FFFF) << 10) | (ssm << 29)
    if word.bit_count() % 2 == 0:
        word |= 1 << 31

    return word


def format_word(word):
    if not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("La palabra debe ocupar exactamente 32 bits.")
    return f"{word:032b}", f"0x{word:08X}"


def describe_word(word):
    binary, hexadecimal = format_word(word)
    data_bits = (word >> 10) & 0x7FFFF
    data_value = data_bits - (1 << 19) if data_bits & (1 << 18) else data_bits
    return {
        "binario": binary,
        "hexadecimal": hexadecimal,
        "label": word & 0xFF,
        "label_bits": f"{word & 0xFF:08b}",
        "sdi": (word >> 8) & 0b11,
        "sdi_bits": f"{(word >> 8) & 0b11:02b}",
        "data_bits": f"{data_bits:019b}",
        "data_value": data_value,
        "ssm": (word >> 29) & 0b11,
        "ssm_bits": f"{(word >> 29) & 0b11:02b}",
        "paridad": (word >> 31) & 1,
    }
