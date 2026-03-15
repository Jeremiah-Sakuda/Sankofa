"""
Generate 30-second, stereo, 44.1kHz loopable ambient WAV files for Sankofa.

Each track uses layered noise synthesis with fade-in/out for seamless looping.
Output: frontend/public/audio/{wind,fire,nature,market,drums}.wav
"""

import os
import numpy as np
from scipy.io import wavfile

SAMPLE_RATE = 44100
DURATION = 30  # seconds
NUM_SAMPLES = SAMPLE_RATE * DURATION
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "audio")

# Crossfade duration for seamless looping (in samples)
FADE_SAMPLES = SAMPLE_RATE * 2  # 2-second crossfade


def apply_loop_crossfade(signal: np.ndarray) -> np.ndarray:
    """Apply a crossfade between the end and beginning for seamless looping."""
    fade_in = np.linspace(0, 1, FADE_SAMPLES)
    fade_out = np.linspace(1, 0, FADE_SAMPLES)

    # Crossfade: blend end into beginning
    result = signal.copy()
    result[:FADE_SAMPLES] = signal[:FADE_SAMPLES] * fade_in + signal[-FADE_SAMPLES:] * fade_out
    result[-FADE_SAMPLES:] = signal[-FADE_SAMPLES:] * fade_out + signal[:FADE_SAMPLES] * fade_in
    return result


def pink_noise(n: int) -> np.ndarray:
    """Generate pink noise (1/f) using the Voss-McCartney algorithm approximation."""
    # Use spectral method: generate white noise, then apply 1/f filter
    white = np.random.randn(n)
    fft = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n, d=1.0 / SAMPLE_RATE)
    freqs[0] = 1  # avoid division by zero
    fft /= np.sqrt(freqs)
    return np.fft.irfft(fft, n=n)


def brown_noise(n: int) -> np.ndarray:
    """Generate brownian noise by cumulative sum of white noise."""
    white = np.random.randn(n) * 0.02
    brown = np.cumsum(white)
    # High-pass filter to remove DC drift
    from scipy.signal import butter, sosfilt
    sos = butter(2, 20, btype='high', fs=SAMPLE_RATE, output='sos')
    brown = sosfilt(sos, brown)
    brown /= np.max(np.abs(brown)) + 1e-10
    return brown


def bandpass_filter(signal: np.ndarray, low: float, high: float) -> np.ndarray:
    """Apply a bandpass filter."""
    from scipy.signal import butter, sosfilt
    sos = butter(4, [low, high], btype='band', fs=SAMPLE_RATE, output='sos')
    return sosfilt(sos, signal)


def lowpass_filter(signal: np.ndarray, cutoff: float) -> np.ndarray:
    """Apply a lowpass filter."""
    from scipy.signal import butter, sosfilt
    sos = butter(4, cutoff, btype='low', fs=SAMPLE_RATE, output='sos')
    return sosfilt(sos, signal)


def to_stereo(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Combine two mono signals into stereo."""
    return np.column_stack([left, right])


def normalize_and_convert(signal: np.ndarray, volume: float = 0.3) -> np.ndarray:
    """Normalize signal and convert to int16."""
    peak = np.max(np.abs(signal)) + 1e-10
    signal = signal / peak * volume
    return np.clip(signal * 32767, -32768, 32767).astype(np.int16)


def generate_wind():
    """Filtered pink noise with slow amplitude modulation (Harmattan/savanna breeze)."""
    t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

    # Base: pink noise filtered to wind range
    noise_l = pink_noise(NUM_SAMPLES)
    noise_r = pink_noise(NUM_SAMPLES)

    wind_l = bandpass_filter(noise_l, 80, 800)
    wind_r = bandpass_filter(noise_r, 80, 800)

    # Slow amplitude modulation (wind gusts)
    mod1 = 0.5 + 0.5 * np.sin(2 * np.pi * 0.08 * t)  # ~12s cycle
    mod2 = 0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * t + 1.2)  # ~8s cycle
    mod = 0.4 + 0.6 * (mod1 * 0.6 + mod2 * 0.4)

    wind_l *= mod
    wind_r *= mod

    # Higher whistle layer
    whistle_l = bandpass_filter(pink_noise(NUM_SAMPLES), 1000, 3000) * 0.15
    whistle_r = bandpass_filter(pink_noise(NUM_SAMPLES), 1000, 3000) * 0.15
    mod_whistle = 0.3 + 0.7 * np.sin(2 * np.pi * 0.05 * t + 0.5) ** 2
    whistle_l *= mod_whistle
    whistle_r *= mod_whistle

    left = wind_l + whistle_l
    right = wind_r + whistle_r

    left = apply_loop_crossfade(left)
    right = apply_loop_crossfade(right)

    stereo = to_stereo(left, right)
    return normalize_and_convert(stereo, volume=0.25)


def generate_fire():
    """Brownian noise base + random crackle pops (campfire/hearth)."""
    t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

    # Base: brownian noise (low rumble)
    base_l = brown_noise(NUM_SAMPLES)
    base_r = brown_noise(NUM_SAMPLES)
    base_l = lowpass_filter(base_l, 400)
    base_r = lowpass_filter(base_r, 400)

    # Slow breathing modulation
    breath = 0.6 + 0.4 * np.sin(2 * np.pi * 0.1 * t)
    base_l *= breath
    base_r *= breath

    # Crackle layer: random short impulses
    crackle_l = np.zeros(NUM_SAMPLES)
    crackle_r = np.zeros(NUM_SAMPLES)

    np.random.seed(42)
    num_crackles = 200
    crackle_positions = np.random.randint(0, NUM_SAMPLES - 500, num_crackles)
    for pos in crackle_positions:
        length = np.random.randint(50, 400)
        amplitude = np.random.uniform(0.3, 1.0)
        crackle = np.random.randn(length) * amplitude
        # Rapid decay envelope
        env = np.exp(-np.linspace(0, 8, length))
        crackle *= env
        end = min(pos + length, NUM_SAMPLES)
        actual_len = end - pos
        # Randomly pan each crackle
        pan = np.random.uniform(0.2, 0.8)
        crackle_l[pos:end] += crackle[:actual_len] * (1 - pan)
        crackle_r[pos:end] += crackle[:actual_len] * pan

    crackle_l = bandpass_filter(crackle_l, 500, 6000) * 0.5
    crackle_r = bandpass_filter(crackle_r, 500, 6000) * 0.5

    left = base_l * 0.7 + crackle_l
    right = base_r * 0.7 + crackle_r

    left = apply_loop_crossfade(left)
    right = apply_loop_crossfade(right)

    stereo = to_stereo(left, right)
    return normalize_and_convert(stereo, volume=0.25)


def generate_nature():
    """Wind layer + bird-like chirps (sine sweeps) + gentle water (filtered noise)."""
    t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

    # Wind base layer (gentle)
    wind_l = bandpass_filter(pink_noise(NUM_SAMPLES), 100, 600) * 0.4
    wind_r = bandpass_filter(pink_noise(NUM_SAMPLES), 100, 600) * 0.4
    wind_mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.06 * t)
    wind_l *= wind_mod
    wind_r *= wind_mod

    # Water/stream layer
    water_l = bandpass_filter(pink_noise(NUM_SAMPLES), 300, 3000) * 0.2
    water_r = bandpass_filter(pink_noise(NUM_SAMPLES), 300, 3000) * 0.2
    water_mod = 0.6 + 0.4 * np.sin(2 * np.pi * 0.15 * t)
    water_l *= water_mod
    water_r *= water_mod

    # Bird chirps: sine sweeps at random intervals
    birds_l = np.zeros(NUM_SAMPLES)
    birds_r = np.zeros(NUM_SAMPLES)
    np.random.seed(123)
    num_birds = 40
    bird_positions = np.random.randint(SAMPLE_RATE, NUM_SAMPLES - SAMPLE_RATE, num_birds)
    for pos in bird_positions:
        # Each chirp is a short frequency sweep
        chirp_dur = np.random.uniform(0.05, 0.2)
        chirp_samples = int(chirp_dur * SAMPLE_RATE)
        freq_start = np.random.uniform(2000, 4000)
        freq_end = np.random.uniform(3000, 6000)
        chirp_t = np.linspace(0, chirp_dur, chirp_samples, endpoint=False)
        freqs = np.linspace(freq_start, freq_end, chirp_samples)
        phase = 2 * np.pi * np.cumsum(freqs) / SAMPLE_RATE
        chirp = np.sin(phase) * np.exp(-chirp_t * 15) * np.random.uniform(0.1, 0.3)

        end = min(pos + chirp_samples, NUM_SAMPLES)
        actual = end - pos
        pan = np.random.uniform(0.1, 0.9)
        birds_l[pos:end] += chirp[:actual] * (1 - pan)
        birds_r[pos:end] += chirp[:actual] * pan

    left = wind_l + water_l + birds_l
    right = wind_r + water_r + birds_r

    left = apply_loop_crossfade(left)
    right = apply_loop_crossfade(right)

    stereo = to_stereo(left, right)
    return normalize_and_convert(stereo, volume=0.25)


def generate_market():
    """Broadband hum + resonant peaks (crowd murmur) + rhythmic tapping."""
    t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

    # Crowd murmur: filtered noise with vocal resonances
    murmur_l = pink_noise(NUM_SAMPLES)
    murmur_r = pink_noise(NUM_SAMPLES)

    # Apply formant-like bandpass filters to simulate crowd voices
    formant1_l = bandpass_filter(murmur_l, 200, 800) * 0.5
    formant2_l = bandpass_filter(murmur_l, 800, 2000) * 0.3
    formant1_r = bandpass_filter(murmur_r, 200, 800) * 0.5
    formant2_r = bandpass_filter(murmur_r, 800, 2000) * 0.3

    crowd_l = formant1_l + formant2_l
    crowd_r = formant1_r + formant2_r

    # Slow swell modulation
    swell = 0.5 + 0.5 * np.sin(2 * np.pi * 0.04 * t)
    crowd_l *= swell
    crowd_r *= swell

    # Rhythmic tapping/clanking sounds
    taps_l = np.zeros(NUM_SAMPLES)
    taps_r = np.zeros(NUM_SAMPLES)
    np.random.seed(77)

    # Semi-regular tapping pattern
    tap_interval = int(SAMPLE_RATE * 0.4)  # ~2.5 taps per second
    for i in range(0, NUM_SAMPLES - 1000, tap_interval):
        offset = np.random.randint(-int(tap_interval * 0.3), int(tap_interval * 0.3))
        pos = max(0, min(i + offset, NUM_SAMPLES - 500))
        tap_len = np.random.randint(100, 300)
        freq = np.random.uniform(800, 2500)
        tap_t = np.linspace(0, tap_len / SAMPLE_RATE, tap_len, endpoint=False)
        tap = np.sin(2 * np.pi * freq * tap_t) * np.exp(-tap_t * 40) * np.random.uniform(0.05, 0.15)

        end = min(pos + tap_len, NUM_SAMPLES)
        actual = end - pos
        pan = np.random.uniform(0.2, 0.8)
        taps_l[pos:end] += tap[:actual] * (1 - pan)
        taps_r[pos:end] += tap[:actual] * pan

    left = crowd_l + taps_l
    right = crowd_r + taps_r

    left = apply_loop_crossfade(left)
    right = apply_loop_crossfade(right)

    stereo = to_stereo(left, right)
    return normalize_and_convert(stereo, volume=0.25)


def generate_drums():
    """Soft djembe-like pulse pattern with reverb tail."""
    t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

    drums_l = np.zeros(NUM_SAMPLES)
    drums_r = np.zeros(NUM_SAMPLES)

    # BPM ~72, grouped in patterns of 4 beats with accents
    bpm = 72
    beat_samples = int(SAMPLE_RATE * 60 / bpm)

    # West African 12/8 feel: subdivide into triplets
    sub_samples = beat_samples // 3

    np.random.seed(99)

    # Pattern: 1-and-a 2-and-a 3-and-a 4-and-a (12 subdivisions per bar)
    # Djembe pattern: bass on 1, tone on others
    pattern = [
        (1.0, 80),   # 1 - bass hit
        (0.0, 0),    # -
        (0.4, 200),  # a - light tone
        (0.6, 150),  # 2 - tone
        (0.0, 0),    # -
        (0.3, 250),  # a - light slap
        (0.8, 90),   # 3 - bass
        (0.0, 0),    # -
        (0.4, 200),  # a - tone
        (0.5, 160),  # 4 - tone
        (0.3, 250),  # -  - light
        (0.4, 200),  # a - tone
    ]

    pos = 0
    while pos < NUM_SAMPLES - SAMPLE_RATE:
        for amp, freq in pattern:
            if pos >= NUM_SAMPLES - SAMPLE_RATE:
                break
            if amp > 0:
                # Generate a drum hit
                hit_dur = 0.15 if freq < 120 else 0.08
                hit_samples = int(hit_dur * SAMPLE_RATE)
                hit_t = np.linspace(0, hit_dur, hit_samples, endpoint=False)

                # Drum body: sine with fast decay
                body = np.sin(2 * np.pi * freq * hit_t) * np.exp(-hit_t * 20) * amp

                # Attack transient
                noise_hit = np.random.randn(min(hit_samples, 200)) * 0.3 * amp
                noise_env = np.exp(-np.linspace(0, 15, len(noise_hit)))
                noise_component = np.zeros(hit_samples)
                noise_component[:len(noise_hit)] = noise_hit * noise_env

                hit = body + noise_component * 0.3

                # Slight random variation
                hit *= np.random.uniform(0.8, 1.0)

                end = min(pos + hit_samples, NUM_SAMPLES)
                actual = end - pos
                # Slight stereo variation
                pan = 0.4 + np.random.uniform(-0.15, 0.15)
                drums_l[pos:end] += hit[:actual] * (1 - pan)
                drums_r[pos:end] += hit[:actual] * pan

            pos += sub_samples

    # Add subtle reverb tail using convolution with exponential decay
    reverb_len = int(0.5 * SAMPLE_RATE)
    reverb_ir = np.random.randn(reverb_len) * np.exp(-np.linspace(0, 8, reverb_len)) * 0.15
    from scipy.signal import fftconvolve
    drums_l_rev = fftconvolve(drums_l, reverb_ir, mode='full')[:NUM_SAMPLES]
    drums_r_rev = fftconvolve(drums_r, reverb_ir, mode='full')[:NUM_SAMPLES]

    left = drums_l + drums_l_rev
    right = drums_r + drums_r_rev

    # Add a very subtle low drone for warmth
    drone = np.sin(2 * np.pi * 55 * t) * 0.05  # A1 note
    drone_mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.03 * t)
    drone *= drone_mod
    left += drone
    right += drone

    left = apply_loop_crossfade(left)
    right = apply_loop_crossfade(right)

    stereo = to_stereo(left, right)
    return normalize_and_convert(stereo, volume=0.3)


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
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"  -> {path} ({size_mb:.1f} MB, {audio.shape[0] / SAMPLE_RATE:.1f}s, {audio.shape[1]}ch)")

    # Remove unused .ogg files
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith(".ogg"):
            ogg_path = os.path.join(OUTPUT_DIR, f)
            os.remove(ogg_path)
            print(f"  Removed unused: {ogg_path}")

    print("Done!")


if __name__ == "__main__":
    main()
