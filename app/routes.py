import math
from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
import serial
from sqlalchemy.exc import IntegrityError

from app import audio_output
from app.encoding import describe_word, encode_bnr, validate_range
from app.extensions import db
from app.models import Envio, Instrumento, ReproduccionAudio, Transmision
from app.serial_transmission import (
    BAUD_RATES,
    BYTE_ORDERS,
    available_ports,
    transmit_word,
    word_to_bytes,
)

main = Blueprint("main", __name__)


@main.get("/")
def index():
    return _render_instrumentos()


@main.route("/instrumentos/nuevo", methods=["GET", "POST"])
def crear_instrumento():
    if request.method == "GET":
        return _render_instrumentos(mostrar_formulario=True)

    instrumento, error = _instrumento_desde_formulario()
    if error:
        flash(error, "error")
        return _render_instrumentos(mostrar_formulario=True, datos_form=request.form), 400

    db.session.add(instrumento)
    if not _guardar_instrumento():
        flash("Ya existe un instrumento con ese nombre.", "error")
        return _render_instrumentos(mostrar_formulario=True, datos_form=request.form), 400

    flash("Instrumento agregado correctamente.", "exito")
    return redirect(url_for("main.index"))


@main.route("/instrumentos/<int:instrumento_id>/editar", methods=["GET", "POST"])
def editar_instrumento(instrumento_id):
    instrumento = db.get_or_404(Instrumento, instrumento_id)
    if request.method == "GET":
        return _render_instrumentos(
            mostrar_formulario=True, instrumento_editar=instrumento
        )

    cambios, error = _instrumento_desde_formulario()
    if error:
        flash(error, "error")
        return _render_instrumentos(
            mostrar_formulario=True,
            instrumento_editar=instrumento,
            datos_form=request.form,
        ), 400

    instrumento.nombre = cambios.nombre
    instrumento.unidad = cambios.unidad
    instrumento.valor_minimo = cambios.valor_minimo
    instrumento.valor_maximo = cambios.valor_maximo
    instrumento.label = cambios.label
    instrumento.escala = cambios.escala
    instrumento.sdi = cambios.sdi

    if not _guardar_instrumento():
        flash("Ya existe otro instrumento con ese nombre.", "error")
        return _render_instrumentos(
            mostrar_formulario=True,
            instrumento_editar=instrumento,
            datos_form=request.form,
        ), 400

    flash("Instrumento actualizado correctamente.", "exito")
    return redirect(url_for("main.index"))


@main.post("/instrumentos/<int:instrumento_id>/eliminar")
def eliminar_instrumento(instrumento_id):
    instrumento = db.get_or_404(Instrumento, instrumento_id)
    db.session.delete(instrumento)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("No se puede eliminar: el instrumento tiene envíos asociados.", "error")
    else:
        flash("Instrumento eliminado correctamente.", "exito")
    return redirect(url_for("main.index"))


@main.route("/envios/nuevo", methods=["GET", "POST"])
def crear_envio():
    if request.method == "GET":
        return _render_instrumentos(mostrar_formulario_envio=True)

    envio, error = _envio_desde_formulario()
    if error:
        flash(error, "error")
        return _render_instrumentos(
            mostrar_formulario_envio=True, datos_envio=request.form
        ), 400

    db.session.add(envio)
    if not _guardar_envio():
        flash("No se pudo guardar el envío. Revisá el instrumento seleccionado.", "error")
        return _render_instrumentos(
            mostrar_formulario_envio=True, datos_envio=request.form
        ), 400

    flash("Envío registrado y codificado correctamente.", "exito")
    return redirect(url_for("main.index", aviso="envios", _anchor="envios"))


@main.route("/envios/<int:envio_id>/editar", methods=["GET", "POST"])
def editar_envio(envio_id):
    envio = db.get_or_404(Envio, envio_id)
    if request.method == "GET":
        return _render_instrumentos(
            mostrar_formulario_envio=True, envio_editar=envio
        )

    cambios, error = _envio_desde_formulario()
    if error:
        flash(error, "error")
        return _render_instrumentos(
            mostrar_formulario_envio=True,
            envio_editar=envio,
            datos_envio=request.form,
        ), 400

    envio.instrumento_id = cambios.instrumento_id
    envio.valor = cambios.valor
    envio.palabra_binaria = cambios.palabra_binaria
    envio.palabra_hexadecimal = cambios.palabra_hexadecimal

    if not _guardar_envio():
        flash("No se pudo actualizar el envío. Revisá el instrumento seleccionado.", "error")
        return _render_instrumentos(
            mostrar_formulario_envio=True,
            envio_editar=envio,
            datos_envio=request.form,
        ), 400

    flash("Envío actualizado y recodificado correctamente.", "exito")
    return redirect(url_for("main.index", aviso="envios", _anchor="envios"))


@main.post("/envios/<int:envio_id>/eliminar")
def eliminar_envio(envio_id):
    envio = db.get_or_404(Envio, envio_id)
    db.session.delete(envio)
    db.session.commit()
    flash("Envío eliminado correctamente.", "exito")
    return redirect(url_for("main.index", aviso="envios", _anchor="envios"))


@main.post("/envios/<int:envio_id>/transmitir")
def transmitir_envio(envio_id):
    envio = db.get_or_404(Envio, envio_id)
    modo_formulario = request.form.get("modo", "")
    simulacion = modo_formulario == "simulacion"
    modo = "simulacion" if simulacion else "uart"
    puerto = "SIMULACIÓN" if simulacion else request.form.get("puerto", "").strip()
    orden_bytes = request.form.get("orden_bytes", "big")
    palabra = int(envio.palabra_binaria, 2)
    bytes_salida = b""

    try:
        velocidad = int(request.form.get("velocidad", ""))
        if modo_formulario not in ("simulacion", "uart"):
            raise ValueError("Seleccioná simulación o transmisión por puerto COM.")
        if orden_bytes not in BYTE_ORDERS:
            raise ValueError("Seleccioná un orden de bytes válido.")
        bytes_salida = word_to_bytes(palabra, orden_bytes)
        if not simulacion:
            puertos_disponibles = {item["device"] for item in available_ports()}
            if puerto not in puertos_disponibles:
                raise ValueError("El puerto COM seleccionado ya no está disponible.")
        resultado = transmit_word(
            palabra,
            puerto,
            velocidad,
            orden_bytes,
            simulate=simulacion,
        )
        estado = resultado.status
        mensaje = resultado.message
    except (ValueError, serial.SerialException, OSError) as error:
        velocidad = _velocidad_para_registro(request.form.get("velocidad", ""))
        estado = "error"
        mensaje = str(error)

    intento = Transmision(
        envio_id=envio.id,
        instrumento_nombre=envio.instrumento.nombre,
        valor=envio.valor,
        puerto=puerto or "(sin seleccionar)",
        modo=modo,
        velocidad=velocidad,
        orden_bytes=orden_bytes if orden_bytes in BYTE_ORDERS else "big",
        palabra_binaria=envio.palabra_binaria,
        palabra_hexadecimal=envio.palabra_hexadecimal,
        bytes_hexadecimales=" ".join(f"{byte:02X}" for byte in bytes_salida),
        resultado=estado,
        mensaje=mensaje,
    )
    db.session.add(intento)
    db.session.commit()

    categoria = {"exitosa": "exito", "simulado": "simulacion"}.get(estado, "error")
    flash(mensaje, categoria)
    return redirect(url_for("main.index", aviso="envios", _anchor="envios"))


@main.get("/api/envios/<int:envio_id>/audio-preview")
def previsualizar_audio(envio_id):
    envio = db.get_or_404(Envio, envio_id)
    try:
        amplitud = float(request.args.get("amplitud", audio_output.DEFAULT_AMPLITUDE))
        dispositivo_texto = request.args.get("dispositivo", "")
        dispositivo_id = int(dispositivo_texto) if dispositivo_texto else None
        sample_rate = audio_output.sample_rate_for_device(dispositivo_id)
        muestras = audio_output.generate_rz_waveform(envio.palabra_binaria, amplitud)
    except (TypeError, ValueError) as error:
        return jsonify(error=str(error)), 400

    return jsonify(
        bits=envio.palabra_binaria,
        muestras=muestras.tolist(),
        amplitud=amplitud,
        frecuencia_muestreo=sample_rate,
        muestras_por_bit=audio_output.SAMPLES_PER_BIT,
        ritmo_demostracion=sample_rate / audio_output.SAMPLES_PER_BIT,
        duracion_segundos=len(muestras) / sample_rate,
    )


@main.post("/envios/<int:envio_id>/reproducir-audio")
def reproducir_audio(envio_id):
    envio = db.get_or_404(Envio, envio_id)
    modo_formulario = request.form.get("modo_audio", "")
    modo = "reproduccion" if modo_formulario == "reproducir" else "simulacion"
    dispositivo_texto = request.form.get("dispositivo_audio", "")
    dispositivo_id = None
    amplitud = audio_output.DEFAULT_AMPLITUDE
    sample_rate = audio_output.DEFAULT_SAMPLE_RATE
    mensaje = ""
    estado = "error"
    dispositivo = None
    nombre_dispositivo = (
        "Simulación sin dispositivo"
        if modo_formulario == "simulacion"
        else "Sin dispositivo seleccionado"
    )

    try:
        dispositivos = audio_output.available_output_devices()
        amplitud = float(request.form.get("amplitud", audio_output.DEFAULT_AMPLITUDE))
        if not math.isfinite(amplitud) or not 0 <= amplitud <= audio_output.MAX_AMPLITUDE:
            raise ValueError(
                f"La amplitud debe estar entre 0 y {audio_output.MAX_AMPLITUDE:.2f}."
            )
        if modo_formulario not in ("simulacion", "reproducir"):
            raise ValueError("Seleccioná simulación o reproducción por audio.")
        if modo_formulario == "reproducir" and request.form.get("previsualizada") != "1":
            raise ValueError("Previsualizá la señal antes de reproducirla.")

        if dispositivo_texto:
            dispositivo_id = int(dispositivo_texto)
            dispositivo = next(
                (item for item in dispositivos if item["index"] == dispositivo_id),
                None,
            )
            if dispositivo is None:
                raise ValueError("El dispositivo de audio seleccionado no está disponible.")
            sample_rate = dispositivo["sample_rate"]
            nombre_dispositivo = dispositivo["name"]
        elif modo_formulario == "reproducir":
            raise ValueError("Seleccioná un dispositivo de salida de audio.")

        waveform = audio_output.generate_rz_waveform(envio.palabra_binaria, amplitud)
        if modo_formulario == "reproducir":
            audio_output.play_waveform(waveform, sample_rate, dispositivo_id)
            estado = "reproducido"
            mensaje = (
                f"Reproducción terminada: 32 bits RZ de demostración a "
                f"{sample_rate} Hz, amplitud digital {amplitud:.3f}."
            )
        else:
            estado = "simulado"
            mensaje = "Simulación completada: se generaron las muestras sin emitir sonido."
    except (TypeError, ValueError, OSError, audio_output.sd.PortAudioError) as error:
        if not math.isfinite(amplitud) or not 0 <= amplitud <= audio_output.MAX_AMPLITUDE:
            amplitud = audio_output.DEFAULT_AMPLITUDE
        mensaje = str(error)

    intento = ReproduccionAudio(
        envio_id=envio.id,
        instrumento_nombre=envio.instrumento.nombre,
        valor=envio.valor,
        dispositivo=nombre_dispositivo,
        modo=modo,
        amplitud=amplitud,
        frecuencia_muestreo=sample_rate,
        muestras_por_bit=audio_output.SAMPLES_PER_BIT,
        ritmo_demostracion=sample_rate / audio_output.SAMPLES_PER_BIT,
        palabra_binaria=envio.palabra_binaria,
        resultado=estado,
        mensaje=mensaje,
    )
    db.session.add(intento)
    db.session.commit()
    categoria = {"reproducido": "exito", "simulado": "simulacion"}.get(estado, "error")
    flash(mensaje, categoria)
    return redirect(url_for("main.index", aviso="envios", _anchor="envios"))


@main.get("/api/salud")
def salud():
    return jsonify(estado="ok", aplicacion="ARINC-429-completo")


def _render_instrumentos(
    mostrar_formulario=False,
    instrumento_editar=None,
    datos_form=None,
    mostrar_formulario_envio=False,
    envio_editar=None,
    datos_envio=None,
):
    instrumentos = Instrumento.query.order_by(Instrumento.nombre).all()
    envios = Envio.query.order_by(Envio.creado_en.desc(), Envio.id.desc()).all()
    envios_con_campos = [
        (envio, describe_word(int(envio.palabra_binaria, 2))) for envio in envios
    ]
    transmisiones = Transmision.query.order_by(
        Transmision.creado_en.desc(), Transmision.id.desc()
    ).all()
    reproducciones_audio = ReproduccionAudio.query.order_by(
        ReproduccionAudio.creado_en.desc(), ReproduccionAudio.id.desc()
    ).all()
    return render_template(
        "index.html",
        instrumentos=instrumentos,
        mostrar_formulario=mostrar_formulario,
        instrumento_editar=instrumento_editar,
        datos_form=datos_form or {},
        mostrar_formulario_envio=mostrar_formulario_envio,
        envio_editar=envio_editar,
        datos_envio=datos_envio or {},
        envios=envios_con_campos,
        puertos_seriales=available_ports(),
        velocidades_uart=BAUD_RATES,
        transmisiones=transmisiones,
        dispositivos_audio=audio_output.available_output_devices(),
        reproducciones_audio=reproducciones_audio,
    )


def _instrumento_desde_formulario():
    formulario = request.form
    nombre = formulario.get("nombre", "").strip()
    unidad = formulario.get("unidad", "").strip()
    if not nombre or not unidad:
        return None, "Completá el nombre y la unidad de medida."
    if len(nombre) > 120 or len(unidad) > 24:
        return None, "El nombre o la unidad superan la longitud permitida."

    try:
        minimo = Decimal(formulario.get("valor_minimo", ""))
        maximo = Decimal(formulario.get("valor_maximo", ""))
        escala = Decimal(formulario.get("escala", ""))
        label = int(formulario.get("label", ""))
        sdi = int(formulario.get("sdi", ""))
    except (InvalidOperation, ValueError):
        return None, "Revisá los valores numéricos ingresados."

    if not all(valor.is_finite() for valor in (minimo, maximo, escala)):
        return None, "Los valores numéricos deben ser finitos."
    if minimo >= maximo:
        return None, "El valor mínimo debe ser menor que el valor máximo."
    if not 0 <= label <= 255:
        return None, "Label ARINC 429 debe estar entre 0 y 255."
    if not 0 <= sdi <= 3:
        return None, "SDI debe estar entre 0 y 3."
    if escala <= 0:
        return None, "La resolución BNR debe ser mayor que cero."

    return Instrumento(
        nombre=nombre,
        unidad=unidad,
        valor_minimo=minimo,
        valor_maximo=maximo,
        label=label,
        escala=escala,
        sdi=sdi,
    ), None


def _guardar_instrumento():
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return False
    return True


def _envio_desde_formulario():
    try:
        instrumento_id = int(request.form.get("instrumento_id", ""))
        valor = Decimal(request.form.get("valor", ""))
    except (InvalidOperation, ValueError):
        return None, "Seleccioná un instrumento e ingresá un valor numérico válido."

    if not valor.is_finite():
        return None, "El valor debe ser un número finito."

    instrumento = db.session.get(Instrumento, instrumento_id)
    if instrumento is None:
        return None, "El instrumento seleccionado no existe."

    try:
        validate_range(valor, instrumento.valor_minimo, instrumento.valor_maximo)
        palabra = encode_bnr(
            valor,
            instrumento.label,
            sdi=instrumento.sdi,
            ssm=instrumento.ssm,
            scale=instrumento.escala,
            offset=instrumento.offset,
        )
    except ValueError as error:
        return None, str(error)

    campos = describe_word(palabra)
    return Envio(
        instrumento_id=instrumento.id,
        valor=valor,
        palabra_binaria=campos["binario"],
        palabra_hexadecimal=campos["hexadecimal"],
    ), None


def _guardar_envio():
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return False
    return True


def _velocidad_para_registro(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return 0
