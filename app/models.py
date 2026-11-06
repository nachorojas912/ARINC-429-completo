from datetime import datetime

from app.extensions import db


class Instrumento(db.Model):
    __tablename__ = "instrumentos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False, unique=True)
    valor_minimo = db.Column(db.Numeric(12, 4), nullable=False)
    valor_maximo = db.Column(db.Numeric(12, 4), nullable=False)
    unidad = db.Column(db.String(24), nullable=False)
    label = db.Column(db.SmallInteger, nullable=False)
    sdi = db.Column(db.SmallInteger, nullable=False, default=0)
    ssm = db.Column(db.SmallInteger, nullable=False, default=0)
    escala = db.Column(db.Numeric(16, 8), nullable=False, default=1)
    offset = db.Column(db.Numeric(16, 8), nullable=False, default=0)

    envios = db.relationship("Envio", back_populates="instrumento", lazy=True)


class Envio(db.Model):
    __tablename__ = "envios"

    id = db.Column(db.Integer, primary_key=True)
    instrumento_id = db.Column(
        db.Integer, db.ForeignKey("instrumentos.id"), nullable=False
    )
    valor = db.Column(db.Numeric(12, 4), nullable=False)
    palabra_binaria = db.Column(db.String(32), nullable=False)
    palabra_hexadecimal = db.Column(db.String(10), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    instrumento = db.relationship("Instrumento", back_populates="envios")


class Transmision(db.Model):
    __tablename__ = "transmisiones"

    id = db.Column(db.Integer, primary_key=True)
    envio_id = db.Column(
        db.Integer, db.ForeignKey("envios.id", ondelete="SET NULL"), nullable=True
    )
    instrumento_nombre = db.Column(db.String(120), nullable=False)
    valor = db.Column(db.Numeric(12, 4), nullable=False)
    puerto = db.Column(db.String(32), nullable=False)
    modo = db.Column(db.String(16), nullable=False)
    velocidad = db.Column(db.Integer, nullable=False)
    orden_bytes = db.Column(db.String(8), nullable=False)
    palabra_binaria = db.Column(db.String(32), nullable=False)
    palabra_hexadecimal = db.Column(db.String(10), nullable=False)
    bytes_hexadecimales = db.Column(db.String(11), nullable=False)
    resultado = db.Column(db.String(16), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ReproduccionAudio(db.Model):
    __tablename__ = "reproducciones_audio"

    id = db.Column(db.Integer, primary_key=True)
    envio_id = db.Column(
        db.Integer, db.ForeignKey("envios.id", ondelete="SET NULL"), nullable=True
    )
    instrumento_nombre = db.Column(db.String(120), nullable=False)
    valor = db.Column(db.Numeric(12, 4), nullable=False)
    dispositivo = db.Column(db.String(160), nullable=False)
    modo = db.Column(db.String(16), nullable=False)
    amplitud = db.Column(db.Numeric(5, 4), nullable=False)
    frecuencia_muestreo = db.Column(db.Integer, nullable=False)
    muestras_por_bit = db.Column(db.Integer, nullable=False)
    ritmo_demostracion = db.Column(db.Numeric(12, 4), nullable=False)
    palabra_binaria = db.Column(db.String(32), nullable=False)
    resultado = db.Column(db.String(16), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
