from decimal import Decimal

import pytest

from app import create_app
from app.extensions import db
from app.models import Instrumento


class ConfiguracionPruebas:
    TESTING = True
    SECRET_KEY = "prueba-local"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


@pytest.fixture

def cliente():
    app = create_app(ConfiguracionPruebas)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def datos_instrumento(**cambios):
    datos = {
        "nombre": "Altitud",
        "unidad": "ft",
        "valor_minimo": "0",
        "valor_maximo": "50000",
        "label": "203",
        "escala": "1.0",
        "sdi": "0",
    }
    datos.update(cambios)
    return datos


def test_crear_instrumento(cliente):
    respuesta = cliente.post(
        "/instrumentos/nuevo", data=datos_instrumento(), follow_redirects=True
    )

    assert respuesta.status_code == 200
    assert b"Instrumento agregado correctamente" in respuesta.data
    instrumento = db.session.scalar(
        db.select(Instrumento).where(Instrumento.nombre == "Altitud")
    )
    assert instrumento is not None
    assert instrumento.unidad == "ft"
    assert instrumento.label == 203
    assert instrumento.escala == Decimal("1.00000000")


def test_consultar_instrumentos(cliente):
    db.session.add(Instrumento(
        nombre="Velocidad", unidad="kt", valor_minimo=0, valor_maximo=600,
        label=100, escala=Decimal("0.5"), sdi=1,
    ))
    db.session.commit()

    respuesta = cliente.get("/")

    assert respuesta.status_code == 200
    assert b"Velocidad" in respuesta.data
    assert b"0.5" in respuesta.data


def test_modificar_instrumento(cliente):
    instrumento = Instrumento(
        nombre="Altitud", unidad="ft", valor_minimo=0, valor_maximo=50000,
        label=203, escala=Decimal("1"), sdi=0,
    )
    db.session.add(instrumento)
    db.session.commit()

    respuesta = cliente.post(
        f"/instrumentos/{instrumento.id}/editar",
        data=datos_instrumento(nombre="Altitud presión", unidad="m", escala="0.25", sdi="2"),
        follow_redirects=True,
    )

    assert respuesta.status_code == 200
    assert b"Instrumento actualizado correctamente" in respuesta.data
    actualizado = db.session.get(Instrumento, instrumento.id)
    assert actualizado.nombre == "Altitud presión"
    assert actualizado.unidad == "m"
    assert actualizado.escala == Decimal("0.25000000")
    assert actualizado.sdi == 2


def test_eliminar_instrumento(cliente):
    instrumento = Instrumento(
        nombre="Temperatura", unidad="C", valor_minimo=-50, valor_maximo=100,
        label=42, escala=Decimal("0.1"), sdi=0,
    )
    db.session.add(instrumento)
    db.session.commit()
    instrumento_id = instrumento.id

    respuesta = cliente.post(
        f"/instrumentos/{instrumento_id}/eliminar", follow_redirects=True
    )

    assert respuesta.status_code == 200
    assert b"Instrumento eliminado correctamente" in respuesta.data
    assert db.session.get(Instrumento, instrumento_id) is None


def test_rechazar_rango_invalido(cliente):
    respuesta = cliente.post(
        "/instrumentos/nuevo",
        data=datos_instrumento(valor_minimo="500", valor_maximo="500"),
    )

    assert respuesta.status_code == 400
    assert "El valor mínimo debe ser menor" in respuesta.data.decode("utf-8")
    assert db.session.scalar(db.select(db.func.count()).select_from(Instrumento)) == 0
