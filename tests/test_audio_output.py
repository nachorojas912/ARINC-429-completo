import numpy as np
import pytest

from app import audio_output


def test_waveform_duration_and_samples_per_bit():
    bits = "1010" * 8

    waveform = audio_output.generate_rz_waveform(bits, amplitude=0.02)

    assert waveform.dtype == np.float32
    assert waveform.shape == (32 * audio_output.SAMPLES_PER_BIT,)
    assert len(waveform) == 1536


def test_each_bit_maps_to_correct_bipolar_pulse():
    bits = "10" * 16
    amplitude = 0.02
    waveform = audio_output.generate_rz_waveform(bits, amplitude)
    pulse_samples = audio_output.SAMPLES_PER_BIT // 2

    for bit_index, bit in enumerate(bits):
        start = bit_index * audio_output.SAMPLES_PER_BIT
        expected_level = amplitude if bit == "1" else -amplitude
        assert np.allclose(waveform[start : start + pulse_samples], expected_level)


def test_every_pulse_returns_to_zero_before_next_bit():
    waveform = audio_output.generate_rz_waveform("101100" * 5 + "10")
    pulse_samples = audio_output.SAMPLES_PER_BIT // 2

    for bit_index in range(32):
        start = bit_index * audio_output.SAMPLES_PER_BIT
        assert np.all(waveform[start + pulse_samples : start + audio_output.SAMPLES_PER_BIT] == 0)


def test_amplitude_is_limited_and_finite():
    waveform = audio_output.generate_rz_waveform("1" * 32)

    assert np.isclose(float(np.max(np.abs(waveform))), audio_output.DEFAULT_AMPLITUDE)
    with pytest.raises(ValueError, match="amplitud"):
        audio_output.generate_rz_waveform("1" * 32, amplitude=0.051)
    with pytest.raises(ValueError, match="amplitud"):
        audio_output.generate_rz_waveform("1" * 32, amplitude=float("nan"))


def test_invalid_bit_words_are_rejected():
    with pytest.raises(ValueError, match="32 bits"):
        audio_output.generate_rz_waveform("101")
    with pytest.raises(ValueError, match="32 bits"):
        audio_output.generate_rz_waveform("2" * 32)


def test_audio_device_listing_filters_input_only_devices(monkeypatch):
    devices = [
        {"name": "Entrada", "max_output_channels": 0, "default_samplerate": 48000},
        {"name": "Salida", "max_output_channels": 2, "default_samplerate": 44100},
    ]
    monkeypatch.setattr(audio_output.sd, "query_devices", lambda: devices)
    monkeypatch.setattr(audio_output.sd, "check_output_settings", lambda **kwargs: None)

    assert audio_output.available_output_devices() == [
        {"index": 1, "name": "Salida", "sample_rate": 44100, "demo_bit_rate": 918.75}
    ]


def test_playback_uses_selected_device_and_sample_rate(monkeypatch):
    played = {}
    waveform = audio_output.generate_rz_waveform("0" * 32)
    devices = [{"index": 4, "sample_rate": 48000}]
    monkeypatch.setattr(audio_output, "available_output_devices", lambda: devices)
    monkeypatch.setattr(
        audio_output.sd,
        "play",
        lambda samples, **kwargs: played.update(samples=samples, **kwargs),
    )

    audio_output.play_waveform(waveform, 48000, 4)

    assert played["samples"] is waveform
    assert played["samplerate"] == 48000
    assert played["device"] == 4
    assert played["blocking"] is True
