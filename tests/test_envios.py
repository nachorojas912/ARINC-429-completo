from decimal import Decimal

import pytest

from app import create_app
from app.encoding import describe_word, encode_bnr
from app.extensions import db
from app.models import Envio, Instrumento


class ConfiguracionEnviosPrueba:
    TESTING = True
    SECRET_KEY = "prueba-local"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


@pytest.fixture

def cliente_envios():
    app = create_app(ConfiguracionEnviosPrueba)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def agregar_instrumento():
    instrumento = Instrumento(
        nombre="Velocidad indicada",
        unidad="kt",
        valor_minimo=Decimal("0"),
        valor_maximo=Decimal("10"),
        label=0xA5,
        sdi=2,
        ssm=1,
        escala=Decimal("0.5"),
        offset=Decimal("0"),
    )
    db.session.add(instrumento)
    db.session.commit()
    return instrumento


def datos_envio(instrumento_id, valor):
    return {"instrumento_id": str(instrumento_id), "valor": str(valor)}


def test_crear_envio_en_ambos_limites_inclusivos(cliente_envios):
    instrumento = agregar_instrumento()

    for valor in ("0", "10"):
        respuesta = cliente_envios.post(
            "/envios/nuevo",
            data=datos_envio(instrumento.id, valor),
            follow_redirects=True,
        )
        assert respuesta.status_code == 200
        assert "Envío registrado y codificado correctamente." in respuesta.get_data(as_text=True)

    assert db.session.scalar(db.select(db.func.count()).select_from(Envio)) == 2


def test_rechazar_valor_fuera_de_rango(cliente_envios):
    instrumento = agregar_instrumento()

    respuesta = cliente_envios.post(
        "/envios/nuevo", data=datos_envio(instrumento.id, "10.5")
    )

    assert respuesta.status_code == 400
    assert "fuera del rango" in respuesta.get_data(as_text=True)
    assert db.session.scalar(db.select(db.func.count()).select_from(Envio)) == 0


def test_rechazar_valor_no_representable_por_resolucion(cliente_envios):
    instrumento = agregar_instrumento()

    respuesta = cliente_envios.post(
        "/envios/nuevo", data=datos_envio(instrumento.id, "1.1")
    )

    assert respuesta.status_code == 400
    assert "resolución configurada" in respuesta.get_data(as_text=True)
    assert db.session.scalar(db.select(db.func.count()).select_from(Envio)) == 0


def test_rechazar_valor_que_no_cabe_en_datos_bnr(cliente_envios):
    instrumento = agregar_instrumento()
    instrumento.valor_maximo = Decimal("300000")
    db.session.commit()

    respuesta = cliente_envios.post(
        "/envios/nuevo", data=datos_envio(instrumento.id, "262144")
    )

    assert respuesta.status_code == 400
    assert "19 bits BNR" in respuesta.get_data(as_text=True)
    assert db.session.scalar(db.select(db.func.count()).select_from(Envio)) == 0


def test_codificacion_y_campos_de_palabra(cliente_envios):
    instrumento = agregar_instrumento()
    palabra = encode_bnr(
        Decimal("1"), instrumento.label, instrumento.sdi,
        instrumento.ssm, instrumento.escala, instrumento.offset,
    )
    campos = describe_word(palabra)
    respuesta = cliente_envios.post(
        "/envios/nuevo",
        data=datos_envio(instrumento.id, "1"),
        follow_redirects=True,
    )

    assert respuesta.status_code == 200
    assert campos["binario"] in respuesta.get_data(as_text=True)
    assert campos["hexadecimal"] in respuesta.get_data(as_text=True)
    assert campos["label"] == 0xA5
    assert campos["sdi"] == 2
    assert campos["data_value"] == 2
    assert campos["data_bits"] == f"{2:019b}"
    assert campos["ssm"] == 1
    assert campos["paridad"] == int(campos["binario"][0])
    assert int(campos["binario"], 2).bit_count() % 2 == 1


def test_consultar_historial_de_envios(cliente_envios):
    instrumento = agregar_instrumento()
    cliente_envios.post(
        "/envios/nuevo",
        data=datos_envio(instrumento.id, "2"),
        follow_redirects=True,
    )

    respuesta = cliente_envios.get("/#envios")

    assert respuesta.status_code == 200
    assert "2.0000" in respuesta.get_data(as_text=True)
    assert "Velocidad indicada" in respuesta.get_data(as_text=True)
    assert "Ver palabra de 32 bits" in respuesta.get_data(as_text=True)


def test_editar_envio_recalcula_la_palabra(cliente_envios):
    instrumento = agregar_instrumento()
    cliente_envios.post(
        "/envios/nuevo",
        data=datos_envio(instrumento.id, "1"),
        follow_redirects=True,
    )
    envio = db.session.scalar(db.select(Envio))
    palabra_original = envio.palabra_binaria

    respuesta = cliente_envios.post(
        f"/envios/{envio.id}/editar",
        data=datos_envio(instrumento.id, "2"),
        follow_redirects=True,
    )

    actualizado = db.session.get(Envio, envio.id)
    assert respuesta.status_code == 200
    assert b"actualizado y recodificado" in respuesta.data
    assert actualizado.valor == Decimal("2.0000")
    assert actualizado.palabra_binaria != palabra_original
    assert actualizado.palabra_hexadecimal == describe_word(
        int(actualizado.palabra_binaria, 2)
    )["hexadecimal"]


def test_eliminar_envio(cliente_envios):
    instrumento = agregar_instrumento()
    cliente_envios.post(
        "/envios/nuevo",
        data=datos_envio(instrumento.id, "1"),
        follow_redirects=True,
    )
    envio = db.session.scalar(db.select(Envio))
    envio_id = envio.id

    respuesta = cliente_envios.post(
        f"/envios/{envio_id}/eliminar", follow_redirects=True
    )

    assert respuesta.status_code == 200
    assert b"Env\xc3\xado eliminado correctamente" in respuesta.data
    assert db.session.get(Envio, envio_id) is None


def test_rechazar_envio_sin_instrumento_existente(cliente_envios):
    respuesta = cliente_envios.post(
        "/envios/nuevo", data=datos_envio(999, "1")
    )

    assert respuesta.status_code == 400
    assert "no existe" in respuesta.get_data(as_text=True)
    assert db.session.scalar(db.select(db.func.count()).select_from(Envio)) == 0
