from dataclasses import dataclass

import serial
from serial.tools import list_ports


BAUD_RATES = (9600, 19200, 115200)
BYTE_ORDERS = ("big", "little")


@dataclass(frozen=True)
class TransmissionResult:
    status: str
    message: str
    data: bytes


def available_ports():
    try:
        ports = list_ports.comports()
    except (OSError, serial.SerialException):
        return []

    return [
        {"device": port.device, "description": port.description or "Puerto serial"}
        for port in sorted(ports, key=lambda item: item.device)
    ]


def word_to_bytes(word, byte_order):
    if not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("La palabra debe ocupar exactamente 32 bits.")
    if byte_order not in BYTE_ORDERS:
        raise ValueError("Seleccioná un orden de bytes válido.")
    return word.to_bytes(4, byteorder=byte_order, signed=False)


def transmit_word(word, port, baud_rate, byte_order, simulate=False):
    if baud_rate not in BAUD_RATES:
        raise ValueError("Velocidad UART no permitida.")
    if not simulate and not port:
        raise ValueError("Seleccioná un puerto COM disponible.")

    data = word_to_bytes(word, byte_order)
    if simulate:
        return TransmissionResult(
            status="simulado",
            message="Simulación correcta: no se abrió ningún puerto ni se enviaron señales.",
            data=data,
        )

    with serial.Serial(
        port=port,
        baudrate=baud_rate,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1,
        write_timeout=2,
    ) as connection:
        written = connection.write(data)
        connection.flush()
        if written != len(data):
            raise serial.SerialTimeoutException(
                f"Se escribieron {written} de {len(data)} bytes."
            )

    return TransmissionResult(
        status="exitosa",
        message=f"Se transmitieron 4 bytes por {port} a {baud_rate} baudios.",
        data=data,
    )