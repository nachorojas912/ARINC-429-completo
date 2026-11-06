import math

import numpy as np
import sounddevice as sd


DEFAULT_SAMPLE_RATE = 48000
SAMPLES_PER_BIT = 48
DEFAULT_AMPLITUDE = 0.02
MAX_AMPLITUDE = 0.05


def generate_rz_waveform(bits, amplitude=DEFAULT_AMPLITUDE):
    if len(bits) != 32 or any(bit not in "01" for bit in bits):
        raise ValueError("La palabra de audio debe contener exactamente 32 bits.")
    try:
        amplitude = float(amplitude)
    except (TypeError, ValueError) as error:
        raise ValueError("La amplitud debe ser un número válido.") from error
    if not math.isfinite(amplitude) or not 0 <= amplitude <= MAX_AMPLITUDE:
        raise ValueError(f"La amplitud debe estar entre 0 y {MAX_AMPLITUDE:.2f}.")

    waveform = np.zeros(len(bits) * SAMPLES_PER_BIT, dtype=np.float32)
    pulse_samples = SAMPLES_PER_BIT // 2
    for bit_index, bit in enumerate(bits):
        start = bit_index * SAMPLES_PER_BIT
        pulse_level = amplitude if bit == "1" else -amplitude
        waveform[start : start + pulse_samples] = pulse_level
    return waveform


def available_output_devices():
    try:
        devices = sd.query_devices()
    except (OSError, sd.PortAudioError):
        return []

    available = []
    for index, device in enumerate(devices):
        if int(device.get("max_output_channels", 0)) < 1:
            continue
        default_rate = int(round(device.get("default_samplerate") or 0))
        candidate_rates = list(dict.fromkeys((default_rate, 48000, 44100, 22050)))
        sample_rate = None
        for candidate in candidate_rates:
            if candidate <= 0:
                continue
            try:
                sd.check_output_settings(
                    device=index,
                    channels=1,
                    dtype="float32",
                    samplerate=candidate,
                )
            except (OSError, ValueError, sd.PortAudioError):
                continue
            sample_rate = candidate
            break
        if sample_rate is not None:
            available.append(
                {
                    "index": index,
                    "name": device.get("name", f"Dispositivo {index}"),
                    "sample_rate": sample_rate,
                    "demo_bit_rate": sample_rate / SAMPLES_PER_BIT,
                }
            )
    return available


def sample_rate_for_device(device_index=None):
    if device_index is None:
        return DEFAULT_SAMPLE_RATE
    for device in available_output_devices():
        if device["index"] == device_index:
            return device["sample_rate"]
    raise ValueError("El dispositivo de audio seleccionado no está disponible.")


def play_waveform(waveform, sample_rate, device_index):
    devices = available_output_devices()
    selected = next(
        (device for device in devices if device["index"] == device_index), None
    )
    if selected is None:
        raise ValueError("El dispositivo de audio seleccionado no está disponible.")
    if selected["sample_rate"] != sample_rate:
        raise ValueError("La frecuencia ya no es compatible con el dispositivo.")

    sd.play(
        waveform,
        samplerate=sample_rate,
        device=device_index,
        blocking=True,
    )