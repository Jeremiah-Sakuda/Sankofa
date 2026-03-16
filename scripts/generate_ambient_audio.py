"""
Generate 30-second, mono, 22050Hz loopable ambient WAV files for Sankofa.

Each track uses layered noise synthesis with fade-in/out for seamless looping.
Mono at 22kHz keeps files ~1.3MB (vs 5MB for stereo 44.1kHz) — indistinguishable
for ambient background loops played at 15% volume.

Output: frontend/public/audio/{wind,fire,nature,market,drums,rain,ocean,river,crickets,village}.wav
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
    """Warm campfire with prominent crackle pops and soft low rumble."""
    t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

    # Subtle low rumble (replaces the old broad brown noise that sounded like static)
    rumble = brown_noise(NUM_SAMPLES)
    rumble = lowpass_filter(rumble, 120)  # much lower cutoff — just the warm low hum
    breath = 0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t)
    rumble *= breath * 0.25  # very quiet — just warmth

    # Crackle layer — many more pops, louder, more varied
    crackle = np.zeros(NUM_SAMPLES)
    np.random.seed(42)

    # Dense small crackles (the continuous texture)
    small_positions = np.random.randint(0, NUM_SAMPLES - 600, 600)
    for pos in small_positions:
        length = np.random.randint(30, 200)
        amplitude = np.random.uniform(0.2, 0.7)
        c = np.random.randn(length) * amplitude
        env = np.exp(-np.linspace(0, 10, length))
        c *= env
        end = min(pos + length, NUM_SAMPLES)
        actual = end - pos
        crackle[pos:end] += c[:actual]

    # Medium pops
    med_positions = np.random.randint(0, NUM_SAMPLES - 800, 150)
    for pos in med_positions:
        length = np.random.randint(150, 500)
        amplitude = np.random.uniform(0.5, 1.0)
        c = np.random.randn(length) * amplitude
        env = np.exp(-np.linspace(0, 6, length))
        c *= env
        end = min(pos + length, NUM_SAMPLES)
        actual = end - pos
        crackle[pos:end] += c[:actual]

    # Large occasional snaps
    snap_positions = np.random.randint(0, NUM_SAMPLES - 1000, 30)
    for pos in snap_positions:
        length = np.random.randint(400, 900)
        amplitude = np.random.uniform(0.8, 1.5)
        c = np.random.randn(length) * amplitude
        env = np.exp(-np.linspace(0, 4, length))
        c *= env
        end = min(pos + length, NUM_SAMPLES)
        actual = end - pos
        crackle[pos:end] += c[:actual]

    crackle = bandpass_filter(crackle, 300, 8000) * 0.7

    # Warm mid-range hiss (very gentle fire roar)
    hiss = pink_noise(NUM_SAMPLES)
    hiss = bandpass_filter(hiss, 150, 600) * 0.1
    hiss_mod = 0.4 + 0.6 * np.sin(2 * np.pi * 0.05 * t)
    hiss *= hiss_mod

    signal = rumble + crackle + hiss
    signal = apply_loop_crossfade(signal)
    return normalize_and_convert(signal, volume=0.3)


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


def generate_rain():
    """Steady rain with occasional heavier drops — monsoon/tropical atmosphere."""
    t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

    # Base rain: filtered pink noise
    rain = pink_noise(NUM_SAMPLES)
    rain = bandpass_filter(rain, 200, 6000) * 0.5

    # Slow intensity modulation (rain gusts)
    mod = 0.6 + 0.4 * np.sin(2 * np.pi * 0.03 * t)
    rain *= mod

    # Individual heavy drops
    drops = np.zeros(NUM_SAMPLES)
    np.random.seed(55)
    drop_positions = np.random.randint(0, NUM_SAMPLES - 500, 200)
    for pos in drop_positions:
        length = np.random.randint(60, 200)
        freq = np.random.uniform(800, 3000)
        drop_t = np.linspace(0, length / SAMPLE_RATE, length, endpoint=False)
        drop = np.sin(2 * np.pi * freq * drop_t) * np.exp(-drop_t * 50) * np.random.uniform(0.1, 0.4)
        end = min(pos + length, NUM_SAMPLES)
        actual = end - pos
        drops[pos:end] += drop[:actual]

    # Low rumble (distant thunder feel)
    rumble = brown_noise(NUM_SAMPLES)
    rumble = lowpass_filter(rumble, 100) * 0.15
    rumble_mod = 0.3 + 0.7 * np.sin(2 * np.pi * 0.02 * t)
    rumble *= rumble_mod

    signal = rain + drops + rumble
    signal = apply_loop_crossfade(signal)
    return normalize_and_convert(signal, volume=0.25)


def generate_ocean():
    """Rolling ocean waves with surf and gentle wash — coastal/island atmosphere."""
    t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

    # Wave cycles — low frequency amplitude modulation on broadband noise
    wave_noise = pink_noise(NUM_SAMPLES)
    wave_noise = bandpass_filter(wave_noise, 60, 4000)

    # Main wave cycle (about 8 seconds per wave)
    wave_env = 0.3 + 0.7 * (np.sin(2 * np.pi * 0.125 * t) ** 2)
    waves = wave_noise * wave_env * 0.5

    # Surf hiss on wave crests
    surf = pink_noise(NUM_SAMPLES)
    surf = bandpass_filter(surf, 1500, 8000) * 0.25
    surf_env = np.clip(np.sin(2 * np.pi * 0.125 * t + 0.5), 0, 1) ** 3
    surf *= surf_env

    # Deep low rumble (ocean body)
    deep = brown_noise(NUM_SAMPLES)
    deep = lowpass_filter(deep, 80) * 0.2

    signal = waves + surf + deep
    signal = apply_loop_crossfade(signal)
    return normalize_and_convert(signal, volume=0.25)


def generate_river():
    """Flowing water with gentle babbling — riverside, stream atmosphere."""
    t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

    # Continuous flow — filtered noise
    flow = pink_noise(NUM_SAMPLES)
    flow = bandpass_filter(flow, 200, 3000) * 0.4

    # Gentle modulation (water tumbling over rocks)
    flow_mod = 0.6 + 0.4 * np.sin(2 * np.pi * 0.2 * t) * np.sin(2 * np.pi * 0.07 * t)
    flow *= flow_mod

    # Babbling — higher frequency splashes
    babble = pink_noise(NUM_SAMPLES)
    babble = bandpass_filter(babble, 1500, 6000) * 0.15
    babble_mod = 0.3 + 0.7 * (np.sin(2 * np.pi * 0.35 * t) ** 2)
    babble *= babble_mod

    # Low water body
    body = brown_noise(NUM_SAMPLES)
    body = lowpass_filter(body, 150) * 0.15

    signal = flow + babble + body
    signal = apply_loop_crossfade(signal)
    return normalize_and_convert(signal, volume=0.25)


def generate_crickets():
    """Night insects — crickets chirping, cicadas humming — evening/night atmosphere."""
    t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

    # Background night hum — very soft filtered noise
    night = pink_noise(NUM_SAMPLES)
    night = bandpass_filter(night, 100, 500) * 0.1

    # Cricket chirps — rapid amplitude-modulated sine tones
    crickets = np.zeros(NUM_SAMPLES)
    np.random.seed(66)

    # Several cricket "voices" at different pitches and rhythms
    for voice in range(6):
        freq = np.random.uniform(3500, 5500)
        chirp_rate = np.random.uniform(4, 8)  # chirps per second
        chirp_duty = np.random.uniform(0.3, 0.6)
        phase_offset = np.random.uniform(0, 2 * np.pi)
        amplitude = np.random.uniform(0.08, 0.2)

        # On/off modulation
        mod = (np.sin(2 * np.pi * chirp_rate * t + phase_offset) > (1 - chirp_duty * 2)).astype(float)
        # Smooth the edges
        from scipy.signal import butter, sosfilt
        sos = butter(2, 50, btype='low', fs=SAMPLE_RATE, output='sos')
        mod = sosfilt(sos, mod)
        mod = np.clip(mod, 0, 1)

        tone = np.sin(2 * np.pi * freq * t) * mod * amplitude
        # Occasional silence (cricket pauses)
        pause_mod = (np.sin(2 * np.pi * np.random.uniform(0.05, 0.15) * t + np.random.uniform(0, 6)) > -0.3).astype(float)
        tone *= pause_mod

        crickets += tone

    # Cicada drone (higher continuous tone)
    cicada_freq = 2800
    cicada = np.sin(2 * np.pi * cicada_freq * t) * 0.03
    cicada_mod = 0.4 + 0.6 * np.sin(2 * np.pi * 0.08 * t)
    cicada *= cicada_mod

    signal = night + crickets + cicada
    signal = apply_loop_crossfade(signal)
    return normalize_and_convert(signal, volume=0.2)


def generate_village():
    """Distant village life — soft voices murmur, children, chickens, gentle activity."""
    t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

    # Distant conversation murmur
    murmur = pink_noise(NUM_SAMPLES)
    formant1 = bandpass_filter(murmur, 250, 700) * 0.3
    formant2 = bandpass_filter(murmur, 800, 1800) * 0.2
    voices = formant1 + formant2

    # Swell and ebb of conversation
    voice_mod = 0.3 + 0.7 * (np.sin(2 * np.pi * 0.06 * t) * 0.5 + np.sin(2 * np.pi * 0.03 * t) * 0.5)
    voices *= voice_mod

    # Occasional higher-pitched sounds (children's voices)
    children = bandpass_filter(pink_noise(NUM_SAMPLES), 1500, 3500) * 0.08
    child_mod = np.clip(np.sin(2 * np.pi * 0.1 * t + 1.0), 0, 1) ** 4
    children *= child_mod

    # Rooster/chicken-like sounds (short chirps)
    chickens = np.zeros(NUM_SAMPLES)
    np.random.seed(88)
    chicken_positions = np.random.randint(SAMPLE_RATE * 2, NUM_SAMPLES - SAMPLE_RATE, 15)
    for pos in chicken_positions:
        # Quick descending chirp
        chirp_len = np.random.randint(300, 600)
        freq_start = np.random.uniform(1800, 2500)
        freq_end = np.random.uniform(1200, 1600)
        freqs = np.linspace(freq_start, freq_end, chirp_len)
        phase = 2 * np.pi * np.cumsum(freqs) / SAMPLE_RATE
        chirp_t = np.linspace(0, chirp_len / SAMPLE_RATE, chirp_len, endpoint=False)
        chirp = np.sin(phase) * np.exp(-chirp_t * 12) * np.random.uniform(0.05, 0.12)
        end = min(pos + chirp_len, NUM_SAMPLES)
        actual = end - pos
        chickens[pos:end] += chirp[:actual]

    # Soft wind/outdoor ambience
    outdoor = bandpass_filter(pink_noise(NUM_SAMPLES), 100, 500) * 0.1

    signal = voices + children + chickens + outdoor
    signal = apply_loop_crossfade(signal)
    return normalize_and_convert(signal, volume=0.2)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tracks = {
        "wind.wav": generate_wind,
        "fire.wav": generate_fire,
        "nature.wav": generate_nature,
        "market.wav": generate_market,
        "drums.wav": generate_drums,
        "rain.wav": generate_rain,
        "ocean.wav": generate_ocean,
        "river.wav": generate_river,
        "crickets.wav": generate_crickets,
        "village.wav": generate_village,
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
