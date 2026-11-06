from types import SimpleNamespace

import pytest
import serial

from app import serial_transmission


def test_word_to_bytes_respects_both_byte_orders():
    word = 0x12345678

    assert serial_transmission.word_to_bytes(word, "big") == bytes.fromhex("12 34 56 78")
    assert serial_transmission.word_to_bytes(word, "little") == bytes.fromhex("78 56 34 12")


def test_port_discovery_returns_sorted_com_ports(monkeypatch):
    monkeypatch.setattr(
        serial_transmission.list_ports,
        "comports",
        lambda: [
            SimpleNamespace(device="COM7", description="Puerto siete"),
            SimpleNamespace(device="COM3", description="Puerto tres"),
        ],
    )

    assert serial_transmission.available_ports() == [
        {"device": "COM3", "description": "Puerto tres"},
        {"device": "COM7", "description": "Puerto siete"},
    ]


def test_simulation_does_not_open_a_serial_port(monkeypatch):
    def no_serial_port(**kwargs):
        pytest.fail("La simulación no debe abrir un puerto físico.")

    monkeypatch.setattr(serial_transmission.serial, "Serial", no_serial_port)

    result = serial_transmission.transmit_word(
        0x12345678, "", 9600, "big", simulate=True
    )

    assert result.status == "simulado"
    assert result.data == bytes.fromhex("12 34 56 78")
    assert "no se abrió ningún puerto" in result.message


def test_uart_transmits_exactly_four_bytes_with_selected_settings(monkeypatch):
    opened = {}

    class PuertoFalso:
        def __init__(self, **settings):
            opened.update(settings)
            self.data = None
            self.flushed = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def write(self, data):
            self.data = data
            opened["data"] = data
            return len(data)

        def flush(self):
            self.flushed = True
            opened["flushed"] = True

    monkeypatch.setattr(serial_transmission.serial, "Serial", PuertoFalso)

    result = serial_transmission.transmit_word(
        0x12345678, "COM9", 19200, "little"
    )

    assert result.status == "exitosa"
    assert result.data == bytes.fromhex("78 56 34 12")
    assert len(result.data) == 4
    assert opened["port"] == "COM9"
    assert opened["baudrate"] == 19200
    assert opened["bytesize"] == serial.EIGHTBITS
    assert opened["parity"] == serial.PARITY_NONE
    assert opened["stopbits"] == serial.STOPBITS_ONE
    assert opened["data"] == result.data
    assert opened["flushed"] is True


def test_transmission_rejects_unsupported_baud_and_byte_order():
    with pytest.raises(ValueError, match="Velocidad UART"):
        serial_transmission.transmit_word(0, "COM1", 4800, "big")
    with pytest.raises(ValueError, match="orden de bytes"):
        serial_transmission.transmit_word(0, "COM1", 9600, "native")
