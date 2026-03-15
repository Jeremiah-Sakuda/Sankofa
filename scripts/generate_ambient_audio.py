"""
Generate 30-second, mono, 22050Hz loopable ambient WAV files for Sankofa.

Each track uses layered noise synthesis with fade-in/out for seamless looping.
Mono at 22kHz keeps files ~1.3MB (vs 5MB for stereo 44.1kHz) — indistinguishable
for ambient background loops played at 15% volume.

Output: frontend/public/audio/{wind,fire,nature,market,drums}.wav
"""

import os
import numpy as np
from scipy.io import wavfile

SAMPLE_RATE = 22050
DURATION = 30  # seconds
NUM_SAMPLES = SAMPLE_RATE * DURATION
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "audio")

# Crossfade duration for seamless looping (in samples)
FADE_SAMPLES = SAMPLE_RATE * 2  # 2-second crossfade


def apply_loop_crossfade(signal: np.ndarray) -> np.ndarray:
    """Apply a crossfade between the end and beginning for seamless looping."""
    fade_in = np.linspace(0, 1, FADE_SAMPLES)
    fade_out = np.linspace(1, 0, FADE_SAMPLES)

    result = signal.copy()
    result[:FADE_SAMPLES] = signal[:FADE_SAMPLES] * fade_in + signal[-FADE_SAMPLES:] * fade_out
    result[-FADE_SAMPLES:] = signal[-FADE_SAMPLES:] * fade_out + signal[:FADE_SAMPLES] * fade_in
    return result


def pink_noise(n: int) -> np.ndarray:
    """Generate pink noise (1/f) using spectral method."""
    white = np.random.randn(n)
    fft = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n, d=1.0 / SAMPLE_RATE)
    freqs[0] = 1  # avoid division by zero
    fft /= np.sqrt(freqs)
    return np.fft.irfft(fft, n=n)


def brown_noise(n: int) -> np.ndarray:
    """Generate brownian noise by cumulative sum of white noise."""
    from scipy.signal import butter, sosfilt
    white = np.random.randn(n) * 0.02
    brown = np.cumsum(white)
    sos = butter(2, 20, btype='high', fs=SAMPLE_RATE, output='sos')
    brown = sosfilt(sos, brown)
    brown /= np.max(np.abs(brown)) + 1e-10
    return brown


def bandpass_filter(signal: np.ndarray, low: float, high: float) -> np.ndarray:
    """Apply a bandpass filter."""
    from scipy.signal import butter, sosfilt
    # Clamp to Nyquist
    nyq = SAMPLE_RATE / 2
    high = min(high, nyq - 1)
    low = min(low, high - 1)
    sos = butter(4, [low, high], btype='band', fs=SAMPLE_RATE, output='sos')
    return sosfilt(sos, signal)


def lowpass_filter(signal: np.ndarray, cutoff: float) -> np.ndarray:
    """Apply a lowpass filter."""
    from scipy.signal import butter, sosfilt
    cutoff = min(cutoff, SAMPLE_RATE / 2 - 1)
    sos = butter(4, cutoff, btype='low', fs=SAMPLE_RATE, output='sos')
    return sosfilt(sos, signal)


def normalize_and_convert(signal: np.ndarray, volume: float = 0.3) -> np.ndarray:
    """Normalize mono signal and convert to int16."""
    peak = np.max(np.abs(signal)) + 1e-10
    signal = signal / peak * volume
    return np.clip(signal * 32767, -32768, 32767).astype(np.int16)


def generate_wind():
    """Filtered pink noise with slow amplitude modulation (Harmattan/savanna breeze)."""
    t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

    wind = bandpass_filter(pink_noise(NUM_SAMPLES), 80, 800)

    # Slow amplitude modulation (wind gusts)
    mod1 = 0.5 + 0.5 * np.sin(2 * np.pi * 0.08 * t)
    mod2 = 0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * t + 1.2)
    mod = 0.4 + 0.6 * (mod1 * 0.6 + mod2 * 0.4)
    wind *= mod

    # Higher whistle layer
    whistle = bandpass_filter(pink_noise(NUM_SAMPLES), 1000, 3000) * 0.15
    mod_whistle = 0.3 + 0.7 * np.sin(2 * np.pi * 0.05 * t + 0.5) ** 2
    whistle *= mod_whistle

    signal = wind + whistle
    signal = apply_loop_crossfade(signal)
    return normalize_and_convert(signal, volume=0.25)


def generate_fire():
    """Brownian noise base + random crackle pops (campfire/hearth)."""
    t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

    base = brown_noise(NUM_SAMPLES)
    base = lowpass_filter(base, 400)

    breath = 0.6 + 0.4 * np.sin(2 * np.pi * 0.1 * t)
    base *= breath

    # Crackle layer
    crackle = np.zeros(NUM_SAMPLES)
    np.random.seed(42)
    crackle_positions = np.random.randint(0, NUM_SAMPLES - 500, 200)
    for pos in crackle_positions:
        length = np.random.randint(50, 400)
        amplitude = np.random.uniform(0.3, 1.0)
        c = np.random.randn(length) * amplitude
        env = np.exp(-np.linspace(0, 8, length))
        c *= env
        end = min(pos + length, NUM_SAMPLES)
        actual = end - pos
        crackle[pos:end] += c[:actual]

    crackle = bandpass_filter(crackle, 500, 6000) * 0.5

    signal = base * 0.7 + crackle
    signal = apply_loop_crossfade(signal)
    return normalize_and_convert(signal, volume=0.25)


def generate_nature():
    """Wind layer + bird-like chirps (sine sweeps) + gentle water."""
    t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

    wind = bandpass_filter(pink_noise(NUM_SAMPLES), 100, 600) * 0.4
    wind_mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.06 * t)
    wind *= wind_mod

    water = bandpass_filter(pink_noise(NUM_SAMPLES), 300, 3000) * 0.2
    water_mod = 0.6 + 0.4 * np.sin(2 * np.pi * 0.15 * t)
    water *= water_mod

    # Bird chirps
    birds = np.zeros(NUM_SAMPLES)
    np.random.seed(123)
    bird_positions = np.random.randint(SAMPLE_RATE, NUM_SAMPLES - SAMPLE_RATE, 40)
    for pos in bird_positions:
        chirp_dur = np.random.uniform(0.05, 0.2)
        chirp_samples = int(chirp_dur * SAMPLE_RATE)
        freq_start = np.random.uniform(2000, 4000)
        freq_end = np.random.uniform(3000, min(6000, SAMPLE_RATE / 2 - 100))
        freqs = np.linspace(freq_start, freq_end, chirp_samples)
        phase = 2 * np.pi * np.cumsum(freqs) / SAMPLE_RATE
        chirp_t = np.linspace(0, chirp_dur, chirp_samples, endpoint=False)
        chirp = np.sin(phase) * np.exp(-chirp_t * 15) * np.random.uniform(0.1, 0.3)

        end = min(pos + chirp_samples, NUM_SAMPLES)
        actual = end - pos
        birds[pos:end] += chirp[:actual]

    signal = wind + water + birds
    signal = apply_loop_crossfade(signal)
    return normalize_and_convert(signal, volume=0.25)


def generate_market():
    """Broadband hum + resonant peaks (crowd murmur) + rhythmic tapping."""
    t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

    murmur = pink_noise(NUM_SAMPLES)
    formant1 = bandpass_filter(murmur, 200, 800) * 0.5
    formant2 = bandpass_filter(murmur, 800, 2000) * 0.3
    crowd = formant1 + formant2

    swell = 0.5 + 0.5 * np.sin(2 * np.pi * 0.04 * t)
    crowd *= swell

    # Rhythmic tapping
    taps = np.zeros(NUM_SAMPLES)
    np.random.seed(77)
    tap_interval = int(SAMPLE_RATE * 0.4)
    for i in range(0, NUM_SAMPLES - 1000, tap_interval):
        offset = np.random.randint(-int(tap_interval * 0.3), int(tap_interval * 0.3))
        pos = max(0, min(i + offset, NUM_SAMPLES - 500))
        tap_len = np.random.randint(100, 300)
        freq = np.random.uniform(800, 2500)
        tap_t = np.linspace(0, tap_len / SAMPLE_RATE, tap_len, endpoint=False)
        tap = np.sin(2 * np.pi * freq * tap_t) * np.exp(-tap_t * 40) * np.random.uniform(0.05, 0.15)

        end = min(pos + tap_len, NUM_SAMPLES)
        actual = end - pos
        taps[pos:end] += tap[:actual]

    signal = crowd + taps
    signal = apply_loop_crossfade(signal)
    return normalize_and_convert(signal, volume=0.25)


def generate_drums():
    """Soft djembe-like pulse pattern with reverb tail."""
    t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

    drums = np.zeros(NUM_SAMPLES)

    bpm = 72
    beat_samples = int(SAMPLE_RATE * 60 / bpm)
    sub_samples = beat_samples // 3

    np.random.seed(99)

    pattern = [
        (1.0, 80), (0.0, 0), (0.4, 200),
        (0.6, 150), (0.0, 0), (0.3, 250),
        (0.8, 90), (0.0, 0), (0.4, 200),
        (0.5, 160), (0.3, 250), (0.4, 200),
    ]

    pos = 0
    while pos < NUM_SAMPLES - SAMPLE_RATE:
        for amp, freq in pattern:
            if pos >= NUM_SAMPLES - SAMPLE_RATE:
                break
            if amp > 0:
                hit_dur = 0.15 if freq < 120 else 0.08
                hit_samples = int(hit_dur * SAMPLE_RATE)
                hit_t = np.linspace(0, hit_dur, hit_samples, endpoint=False)

                body = np.sin(2 * np.pi * freq * hit_t) * np.exp(-hit_t * 20) * amp

                noise_hit = np.random.randn(min(hit_samples, 200)) * 0.3 * amp
                noise_env = np.exp(-np.linspace(0, 15, len(noise_hit)))
                noise_component = np.zeros(hit_samples)
                noise_component[:len(noise_hit)] = noise_hit * noise_env

                hit = body + noise_component * 0.3
                hit *= np.random.uniform(0.8, 1.0)

                end = min(pos + hit_samples, NUM_SAMPLES)
                actual = end - pos
                drums[pos:end] += hit[:actual]

            pos += sub_samples

    # Reverb tail
    from scipy.signal import fftconvolve
    reverb_len = int(0.5 * SAMPLE_RATE)
    reverb_ir = np.random.randn(reverb_len) * np.exp(-np.linspace(0, 8, reverb_len)) * 0.15
    drums_rev = fftconvolve(drums, reverb_ir, mode='full')[:NUM_SAMPLES]

    signal = drums + drums_rev

    # Subtle low drone
    drone = np.sin(2 * np.pi * 55 * t) * 0.05
    drone_mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.03 * t)
    drone *= drone_mod
    signal += drone

    signal = apply_loop_crossfade(signal)
    return normalize_and_convert(signal, volume=0.3)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tracks = {
        "wind.wav": generate_wind,
        "fire.wav": generate_fire,
        "nature.wav": generate_nature,
        "market.wav": generate_market,
        "drums.wav": generate_drums,
    }

    for name, generator in tracks.items():
        print(f"Generating {name}...")
        audio = generator()
        path = os.path.join(OUTPUT_DIR, name)
        wavfile.write(path, SAMPLE_RATE, audio)
        size_kb = os.path.getsize(path) / 1024
        print(f"  -> {path} ({size_kb:.0f} KB, {len(audio) / SAMPLE_RATE:.1f}s, mono)")

    print("Done!")


if __name__ == "__main__":
    main()
