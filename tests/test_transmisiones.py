from decimal import Decimal

import pytest
import serial

from app import create_app, routes
from app.encoding import encode_bnr, format_word
from app.extensions import db
from app.models import Envio, Instrumento, Transmision
from app.serial_transmission import TransmissionResult


class ConfiguracionTransmisionesPrueba:
    TESTING = True
    SECRET_KEY = "prueba-local"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


@pytest.fixture

def cliente_transmisiones():
    app = create_app(ConfiguracionTransmisionesPrueba)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def agregar_envio():
    instrumento = Instrumento(
        nombre="Altitud de prueba",
        unidad="ft",
        valor_minimo=Decimal("0"),
        valor_maximo=Decimal("10000"),
        label=0xA5,
        sdi=1,
        ssm=0,
        escala=Decimal("0.5"),
        offset=Decimal("0"),
    )
    valor = Decimal("125")
    palabra = encode_bnr(
        valor, instrumento.label, instrumento.sdi, instrumento.ssm,
        instrumento.escala, instrumento.offset,
    )
    binario, hexadecimal = format_word(palabra)
    db.session.add(instrumento)
    db.session.flush()
    envio = Envio(
        instrumento_id=instrumento.id,
        valor=valor,
        palabra_binaria=binario,
        palabra_hexadecimal=hexadecimal,
    )
    db.session.add(envio)
    db.session.commit()
    return envio


def datos_transmision(**cambios):
    datos = {
        "modo": "simulacion",
        "puerto": "",
        "velocidad": "9600",
        "orden_bytes": "big",
    }
    datos.update(cambios)
    return datos


def test_simulacion_registra_el_intento_y_sus_cuatro_bytes(cliente_transmisiones):
    envio = agregar_envio()
    palabra = int(envio.palabra_binaria, 2)
    expected_bytes = palabra.to_bytes(4, "big")

    respuesta = cliente_transmisiones.post(
        f"/envios/{envio.id}/transmitir",
        data=datos_transmision(),
        follow_redirects=True,
    )

    intento = db.session.scalar(db.select(Transmision))
    assert respuesta.status_code == 200
    assert "Simulación correcta" in respuesta.get_data(as_text=True)
    assert intento.resultado == "simulado"
    assert intento.instrumento_nombre == "Altitud de prueba"
    assert intento.valor == Decimal("125.0000")
    assert intento.puerto == "SIMULACIÓN"
    assert intento.bytes_hexadecimales == " ".join(f"{byte:02X}" for byte in expected_bytes)
    assert intento.palabra_binaria == envio.palabra_binaria
    assert intento.palabra_hexadecimal == envio.palabra_hexadecimal


def test_uart_exitoso_registra_configuracion_y_orden(monkeypatch, cliente_transmisiones):
    envio = agregar_envio()
    recibido = {}

    def transmitir_falso(word, port, baud_rate, byte_order, simulate=False):
        recibido.update(
            word=word, port=port, baud_rate=baud_rate,
            byte_order=byte_order, simulate=simulate,
        )
        return TransmissionResult(
            "exitosa", "Se transmitieron 4 bytes por COM4 a 19200 baudios.",
            word.to_bytes(4, "little"),
        )

    monkeypatch.setattr(
        routes, "available_ports",
        lambda: [{"device": "COM4", "description": "Puerto de prueba"}],
    )
    monkeypatch.setattr(routes, "transmit_word", transmitir_falso)

    respuesta = cliente_transmisiones.post(
        f"/envios/{envio.id}/transmitir",
        data=datos_transmision(
            modo="uart", puerto="COM4", velocidad="19200", orden_bytes="little"
        ),
        follow_redirects=True,
    )

    intento = db.session.scalar(db.select(Transmision))
    assert respuesta.status_code == 200
    assert intento.resultado == "exitosa"
    assert intento.puerto == "COM4"
    assert intento.velocidad == 19200
    assert intento.orden_bytes == "little"
    assert recibido["port"] == "COM4"
    assert recibido["byte_order"] == "little"
    assert recibido["simulate"] is False


def test_error_serial_se_guarda_en_historial(monkeypatch, cliente_transmisiones):
    envio = agregar_envio()

    def fallo_serial(*args, **kwargs):
        raise serial.SerialException("Puerto ocupado")

    monkeypatch.setattr(
        routes, "available_ports",
        lambda: [{"device": "COM4", "description": "Puerto de prueba"}],
    )
    monkeypatch.setattr(routes, "transmit_word", fallo_serial)

    respuesta = cliente_transmisiones.post(
        f"/envios/{envio.id}/transmitir",
        data=datos_transmision(modo="uart", puerto="COM4"),
        follow_redirects=True,
    )

    intento = db.session.scalar(db.select(Transmision))
    assert respuesta.status_code == 200
    assert "Puerto ocupado" in respuesta.get_data(as_text=True)
    assert intento.resultado == "error"
    assert intento.mensaje == "Puerto ocupado"
    assert intento.bytes_hexadecimales


def test_consultar_y_editar_no_transmiten_automaticamente(cliente_transmisiones):
    envio = agregar_envio()

    assert cliente_transmisiones.get("/").status_code == 200
    assert cliente_transmisiones.get(f"/envios/{envio.id}/editar").status_code == 200
    respuesta = cliente_transmisiones.post(
        f"/envios/{envio.id}/editar",
        data={"instrumento_id": str(envio.instrumento_id), "valor": "126"},
        follow_redirects=True,
    )

    assert respuesta.status_code == 200
    assert db.session.scalar(db.select(db.func.count()).select_from(Transmision)) == 0
