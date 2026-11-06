from decimal import Decimal

import numpy as np
import pytest
import sounddevice as sd

from app import audio_output, create_app
from app.encoding import encode_bnr, format_word
from app.extensions import db
from app.models import Envio, Instrumento, ReproduccionAudio


class ConfiguracionAudioPrueba:
    TESTING = True
    SECRET_KEY = "prueba-local"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


@pytest.fixture

def cliente_audio():
    app = create_app(ConfiguracionAudioPrueba)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def agregar_envio():
    instrumento = Instrumento(
        nombre="Presión de prueba",
        unidad="psi",
        valor_minimo=Decimal("0"),
        valor_maximo=Decimal("100"),
        label=0x65,
        sdi=1,
        ssm=0,
        escala=Decimal("0.5"),
        offset=Decimal("0"),
    )
    valor = Decimal("10")
    binario, hexadecimal = format_word(
        encode_bnr(valor, instrumento.label, instrumento.sdi, instrumento.ssm, instrumento.escala)
    )
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


def datos_audio(**cambios):
    datos = {
        "modo_audio": "simulacion",
        "dispositivo_audio": "",
        "amplitud": "0.02",
        "previsualizada": "0",
    }
    datos.update(cambios)
    return datos


def test_preview_returns_samples_without_playing(monkeypatch, cliente_audio):
    envio = agregar_envio()
    monkeypatch.setattr(audio_output, "sample_rate_for_device", lambda device_id: 44100)
    monkeypatch.setattr(
        audio_output.sd,
        "play",
        lambda *args, **kwargs: pytest.fail("La vista previa no debe emitir sonido."),
    )

    respuesta = cliente_audio.get(
        f"/api/envios/{envio.id}/audio-preview?amplitud=0.02"
    )

    datos = respuesta.get_json()
    assert respuesta.status_code == 200
    assert datos["bits"] == envio.palabra_binaria
    assert len(datos["muestras"]) == 32 * audio_output.SAMPLES_PER_BIT
    assert datos["frecuencia_muestreo"] == 44100
    assert datos["ritmo_demostracion"] == 44100 / audio_output.SAMPLES_PER_BIT
    assert db.session.scalar(db.select(db.func.count()).select_from(ReproduccionAudio)) == 0


def test_preview_rejects_amplitude_above_limit(cliente_audio):
    envio = agregar_envio()

    respuesta = cliente_audio.get(
        f"/api/envios/{envio.id}/audio-preview?amplitud=0.08"
    )

    assert respuesta.status_code == 400
    assert "amplitud" in respuesta.get_json()["error"]


def test_simulation_logs_without_calling_play(monkeypatch, cliente_audio):
    envio = agregar_envio()
    monkeypatch.setattr(audio_output, "available_output_devices", lambda: [])
    monkeypatch.setattr(
        audio_output.sd,
        "play",
        lambda *args, **kwargs: pytest.fail("La simulación no debe reproducir audio."),
    )

    respuesta = cliente_audio.post(
        f"/envios/{envio.id}/reproducir-audio",
        data=datos_audio(),
        follow_redirects=True,
    )

    intento = db.session.scalar(db.select(ReproduccionAudio))
    assert respuesta.status_code == 200
    assert "sin emitir sonido" in respuesta.get_data(as_text=True)
    assert intento.resultado == "simulado"
    assert intento.dispositivo == "Simulación sin dispositivo"
    assert intento.amplitud == Decimal("0.0200")
    assert intento.palabra_binaria == envio.palabra_binaria


def test_playback_requires_preview_and_logs_error(monkeypatch, cliente_audio):
    envio = agregar_envio()
    monkeypatch.setattr(audio_output, "available_output_devices", lambda: [
        {"index": 2, "name": "Auriculares de prueba", "sample_rate": 48000}
    ])
    monkeypatch.setattr(
        audio_output,
        "play_waveform",
        lambda *args: pytest.fail("No debe reproducir sin previsualización."),
    )

    respuesta = cliente_audio.post(
        f"/envios/{envio.id}/reproducir-audio",
        data=datos_audio(modo_audio="reproducir", dispositivo_audio="2"),
        follow_redirects=True,
    )

    intento = db.session.scalar(db.select(ReproduccionAudio))
    assert respuesta.status_code == 200
    assert "Previsualizá la señal" in respuesta.get_data(as_text=True)
    assert intento.resultado == "error"
    assert intento.mensaje == "Previsualizá la señal antes de reproducirla."


def test_invalid_amplitude_is_logged_safely(monkeypatch, cliente_audio):
    envio = agregar_envio()
    monkeypatch.setattr(audio_output, "available_output_devices", lambda: [])

    respuesta = cliente_audio.post(
        f"/envios/{envio.id}/reproducir-audio",
        data=datos_audio(amplitud="nan"),
        follow_redirects=True,
    )

    intento = db.session.scalar(db.select(ReproduccionAudio))
    assert respuesta.status_code == 200
    assert intento.resultado == "error"
    assert intento.amplitud == Decimal("0.0200")
    assert "amplitud" in intento.mensaje


def test_opening_creating_and_editing_never_reproduces_automatically(
    monkeypatch, cliente_audio
):
    envio = agregar_envio()
    monkeypatch.setattr(audio_output, "available_output_devices", lambda: [])
    monkeypatch.setattr(
        audio_output.sd,
        "play",
        lambda *args, **kwargs: pytest.fail("No se debe reproducir automáticamente."),
    )

    assert cliente_audio.get("/").status_code == 200
    respuesta_crear = cliente_audio.post(
        "/envios/nuevo",
        data={"instrumento_id": str(envio.instrumento_id), "valor": "12"},
        follow_redirects=True,
    )
    assert respuesta_crear.status_code == 200
    assert cliente_audio.get(f"/envios/{envio.id}/editar").status_code == 200
    respuesta_editar = cliente_audio.post(
        f"/envios/{envio.id}/editar",
        data={"instrumento_id": str(envio.instrumento_id), "valor": "11"},
        follow_redirects=True,
    )

    assert respuesta_editar.status_code == 200
    assert db.session.scalar(
        db.select(db.func.count()).select_from(ReproduccionAudio)
    ) == 0


def test_playback_calls_sounddevice_only_after_explicit_post(monkeypatch, cliente_audio):
    envio = agregar_envio()
    played = {}
    devices = [{"index": 2, "name": "Auriculares de prueba", "sample_rate": 48000}]
    monkeypatch.setattr(audio_output, "available_output_devices", lambda: devices)
    monkeypatch.setattr(
        audio_output,
        "play_waveform",
        lambda waveform, sample_rate, device: played.update(
            waveform=waveform, sample_rate=sample_rate, device=device
        ),
    )

    respuesta = cliente_audio.post(
        f"/envios/{envio.id}/reproducir-audio",
        data=datos_audio(
            modo_audio="reproducir",
            dispositivo_audio="2",
            amplitud="0.015",
            previsualizada="1",
        ),
        follow_redirects=True,
    )

    intento = db.session.scalar(db.select(ReproduccionAudio))
    assert respuesta.status_code == 200
    assert intento.resultado == "reproducido"
    assert intento.dispositivo == "Auriculares de prueba"
    assert intento.amplitud == Decimal("0.0150")
    assert played["sample_rate"] == 48000
    assert played["device"] == 2
    assert isinstance(played["waveform"], np.ndarray)
    assert np.max(np.abs(played["waveform"])) <= audio_output.MAX_AMPLITUDE


def test_playback_failure_is_logged(monkeypatch, cliente_audio):
    envio = agregar_envio()
    monkeypatch.setattr(audio_output, "available_output_devices", lambda: [
        {"index": 2, "name": "Auriculares de prueba", "sample_rate": 48000}
    ])

    def fail_playback(*args):
        raise OSError("Dispositivo ocupado")

    monkeypatch.setattr(audio_output, "play_waveform", fail_playback)
    respuesta = cliente_audio.post(
        f"/envios/{envio.id}/reproducir-audio",
        data=datos_audio(
            modo_audio="reproducir", dispositivo_audio="2", previsualizada="1"
        ),
        follow_redirects=True,
    )

    intento = db.session.scalar(db.select(ReproduccionAudio))
    assert respuesta.status_code == 200
    assert "Dispositivo ocupado" in respuesta.get_data(as_text=True)
    assert intento.resultado == "error"
    assert intento.mensaje == "Dispositivo ocupado"
