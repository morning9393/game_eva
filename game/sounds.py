"""Procedural sound system.

Every sound effect and the background music loop are synthesised at startup
using numpy; no external audio files are shipped. Sounds are stereo 16-bit
at 22050 Hz and are played via pygame.mixer.Sound.

Usage:
    SoundSystem.init()          # call once after pygame.init()
    SoundSystem.play("attack")  # fire a sound by name
    SoundSystem.play_music()    # loop the Echo Lord BGM
    SoundSystem.stop_music()

Silently degrades to no-ops if the mixer can't initialise (headless tests).
"""
import math

import pygame

try:
    import numpy as np
    _NUMPY = True
except Exception:
    _NUMPY = False


SAMPLE_RATE = 22050
STEREO = 2
_INT16_MAX = 32767


# ---------- waveform primitives ----------

def _silence(duration):
    n = int(SAMPLE_RATE * duration)
    return np.zeros(n, dtype=np.float32)


def _sine(freq, duration, phase=0.0):
    n = int(SAMPLE_RATE * duration)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    return np.sin(2 * np.pi * freq * t + phase)


def _triangle(freq, duration):
    n = int(SAMPLE_RATE * duration)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    period = 1.0 / freq
    phase = (t % period) / period
    return 2 * np.abs(2 * phase - 1) - 1


def _saw(freq, duration):
    n = int(SAMPLE_RATE * duration)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    period = 1.0 / freq
    phase = (t % period) / period
    return 2 * phase - 1


def _noise(duration, seed=0):
    n = int(SAMPLE_RATE * duration)
    rng = np.random.default_rng(seed)
    return rng.standard_normal(n).astype(np.float32)


def _env_adsr(n, attack=0.01, decay=0.05, sustain=0.7, release=0.1):
    """Attack-decay-sustain-release envelope over n samples."""
    a = int(n * attack)
    d = int(n * decay)
    r = int(n * release)
    s = max(0, n - a - d - r)
    env = np.zeros(n, dtype=np.float32)
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if d > 0:
        env[a:a + d] = np.linspace(1, sustain, d)
    if s > 0:
        env[a + d:a + d + s] = sustain
    if r > 0:
        env[a + d + s:a + d + s + r] = np.linspace(sustain, 0, r)
    return env


def _env_decay(n, shape=3.0):
    """Exponential decay envelope from 1 to 0."""
    t = np.linspace(0, 1, n, dtype=np.float32)
    return np.exp(-shape * t)


def _lowpass(signal, cutoff_hz):
    """Simple 1-pole IIR lowpass for warming up signals."""
    alpha = math.exp(-2 * math.pi * cutoff_hz / SAMPLE_RATE)
    out = np.zeros_like(signal)
    prev = 0.0
    for i, s in enumerate(signal):
        prev = (1 - alpha) * s + alpha * prev
        out[i] = prev
    return out


def _mix(*signals):
    """Sum several signals of (potentially different) length, padding with 0."""
    max_len = max(len(s) for s in signals)
    out = np.zeros(max_len, dtype=np.float32)
    for s in signals:
        out[:len(s)] += s
    return out


def _normalize(signal, target=0.85):
    peak = float(np.max(np.abs(signal))) if len(signal) else 1.0
    if peak < 1e-6:
        return signal
    return signal * (target / peak)


def _to_sound(signal, volume=0.8, right=None):
    """Convert a float32 [-1, 1] signal into a pygame.mixer.Sound.
    `signal` may be mono (duplicated to stereo) or - with `right` supplied -
    the left channel of a stereo pair.
    """
    if not _NUMPY:
        return None
    if right is not None:
        left = np.clip(signal * volume, -1.0, 1.0)
        right_ = np.clip(right * volume, -1.0, 1.0)
        n = min(len(left), len(right_))
        left = left[:n]; right_ = right_[:n]
        lp = (left * _INT16_MAX).astype(np.int16)
        rp = (right_ * _INT16_MAX).astype(np.int16)
        stereo = np.stack([lp, rp], axis=1)
    else:
        s = np.clip(signal * volume, -1.0, 1.0)
        pcm = (s * _INT16_MAX).astype(np.int16)
        stereo = np.repeat(pcm[:, None], STEREO, axis=1)
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def _delay_echo(signal, delay_s=0.28, feedback=0.35, mix=0.3):
    """Simple feedback delay for reverb-like tail. Keeps output bounded."""
    n = len(signal)
    delay_n = max(1, int(SAMPLE_RATE * delay_s))
    out = signal.copy()
    buf = np.zeros(delay_n, dtype=np.float32)
    bi = 0
    for i in range(n):
        tap = buf[bi]
        new = signal[i] + tap * feedback
        buf[bi] = new
        bi = (bi + 1) % delay_n
        out[i] = signal[i] * (1 - mix) + tap * mix
    return out


# ---------- concrete sound designs ----------

def _fx_sword_swing():
    """Airy swoosh - noise filtered down with a quick attack-decay envelope."""
    dur = 0.22
    n = int(SAMPLE_RATE * dur)
    noise = _noise(dur, seed=1)
    # pitch down over time by modulating lowpass
    lp = _lowpass(noise, 3000)
    env = _env_adsr(n, attack=0.04, decay=0.20, sustain=0.45, release=0.55)
    body = lp * env
    # small whistle harmonic for "singing blade"
    whistle = _sine(680, dur) * _env_adsr(n, attack=0.1, decay=0.2, sustain=0.3, release=0.6) * 0.15
    return _normalize(_mix(body * 0.9, whistle), 0.75)


def _fx_boss_hit():
    """Sharp metallic impact with a brief ring."""
    dur = 0.35
    n = int(SAMPLE_RATE * dur)
    # crack = filtered noise burst
    crack = _noise(0.05, seed=2) * _env_decay(int(SAMPLE_RATE * 0.05), shape=30)
    # bell tone - detuned two sines
    bell = (_sine(420, dur) * 0.6 + _sine(630, dur) * 0.35 + _sine(210, dur) * 0.25)
    bell *= _env_decay(n, shape=5.0)
    # pad crack to match bell length
    crack_padded = np.zeros(n, dtype=np.float32)
    crack_padded[:len(crack)] = crack
    return _normalize(crack_padded * 0.8 + bell * 0.6, 0.8)


def _fx_player_hit():
    """Heavy low thud + brief noise slap."""
    dur = 0.32
    n = int(SAMPLE_RATE * dur)
    thud = _sine(85, dur) * _env_decay(n, shape=8.0)
    slap = _noise(0.04, seed=3) * _env_decay(int(SAMPLE_RATE * 0.04), shape=40)
    slap_padded = np.zeros(n, dtype=np.float32)
    slap_padded[:len(slap)] = slap
    return _normalize(thud * 1.0 + slap_padded * 0.7, 0.9)


def _fx_dash():
    """Short airy whoosh - filtered noise with fast attack/decay."""
    dur = 0.25
    n = int(SAMPLE_RATE * dur)
    noise = _noise(dur, seed=4)
    lp = _lowpass(noise, 2000)
    env = _env_adsr(n, attack=0.05, decay=0.15, sustain=0.5, release=0.5)
    body = lp * env
    hi = _sine(1200, dur) * _env_adsr(n, attack=0.02, decay=0.08, sustain=0.3, release=0.7) * 0.12
    return _normalize(body * 0.8 + hi, 0.65)


def _fx_echo_warn():
    """Rising low chime - two detuned sines ramping in pitch."""
    dur = 0.8
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    # frequency sweep 220 -> 440
    f = 220 + (440 - 220) * (t / dur) ** 2
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    tone = np.sin(phase) * 0.5 + np.sin(phase * 1.498) * 0.3
    env = _env_adsr(n, attack=0.12, decay=0.25, sustain=0.55, release=0.45)
    return _normalize(tone * env, 0.55)


def _fx_echo_slash():
    """Red-slash fire: rapid noise whoosh + cut tone."""
    dur = 0.28
    n = int(SAMPLE_RATE * dur)
    noise = _noise(dur, seed=5)
    lp = _lowpass(noise, 3500)
    env = _env_adsr(n, attack=0.03, decay=0.12, sustain=0.25, release=0.55)
    body = lp * env
    # downward sweep tone
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    f = 1500 - (1500 - 600) * (t / dur)
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    sweep = np.sin(phase) * _env_decay(n, shape=7.0)
    return _normalize(body * 0.9 + sweep * 0.35, 0.8)


def _fx_cascade():
    """4-note descending cluster, sibilant - a rippling ghost chorus."""
    dur = 0.9
    n = int(SAMPLE_RATE * dur)
    total = np.zeros(n, dtype=np.float32)
    notes = [523, 440, 392, 330]  # descending
    for i, f in enumerate(notes):
        start = int(i * (n / len(notes) * 0.55))
        sub_dur = 0.5
        sub_n = int(SAMPLE_RATE * sub_dur)
        if start + sub_n > n:
            sub_n = n - start
        t = np.arange(sub_n, dtype=np.float32) / SAMPLE_RATE
        tone = np.sin(2 * np.pi * f * t) * 0.5 + np.sin(2 * np.pi * f * 1.505 * t) * 0.3
        env = _env_adsr(sub_n, attack=0.05, decay=0.25, sustain=0.4, release=0.5)
        total[start:start + sub_n] += tone * env
    return _normalize(total, 0.6)


def _fx_memory_surge():
    """Low rumble building into a shrieking chord."""
    dur = 0.8
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    rumble = _sine(55, dur) * _env_adsr(n, attack=0.05, decay=0.25, sustain=0.8, release=0.25) * 0.9
    # ascending detuned chord
    f = 180 + 220 * (t / dur) ** 1.5
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    chord = (np.sin(phase) + np.sin(phase * 1.501) + np.sin(phase * 2.005)) / 3.0
    env_chord = _env_adsr(n, attack=0.3, decay=0.25, sustain=0.7, release=0.25)
    # crash at the peak
    crash = _noise(0.15, seed=6) * _env_decay(int(SAMPLE_RATE * 0.15), shape=8.0)
    crash_full = np.zeros(n, dtype=np.float32)
    start = int(n * 0.6)
    end = min(n, start + len(crash))
    crash_full[start:end] = crash[:end - start]
    return _normalize(rumble + chord * env_chord * 0.75 + crash_full * 0.6, 0.85)


def _fx_echo_spawn():
    """Brief pitch-up chime - a phantom appears."""
    dur = 0.3
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    f = 600 + 1000 * (t / dur)
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    tone = np.sin(phase) * _env_adsr(n, attack=0.05, decay=0.2, sustain=0.5, release=0.6)
    return _normalize(tone, 0.5)


def _fx_boss_death():
    """Long collapsing tone + whoosh - the echo lord unravels."""
    dur = 1.8
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    f = 440 * (1 - (t / dur) ** 0.5) + 60
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    tone = (np.sin(phase) + np.sin(phase * 1.498)) * 0.5
    env = _env_adsr(n, attack=0.05, decay=0.3, sustain=0.6, release=0.4)
    noise_tail = _noise(dur, seed=7) * _env_decay(n, shape=2.5) * 0.35
    return _normalize(tone * env + noise_tail, 0.85)


def _fx_player_death():
    """Descending low tone with distortion fizz."""
    dur = 1.6
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    f = 220 * (1 - (t / dur) ** 0.7) + 40
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    tone = np.sin(phase) * 0.8
    env = _env_decay(n, shape=1.5)
    fizz = _noise(dur, seed=8) * _env_decay(n, shape=3.0) * 0.3
    return _normalize(tone * env + fizz, 0.85)


# ---------- background music: echo lord theme ----------

# Note frequencies (Hz) - expanded to cover all four new boss themes
_NOTE = {
    "C2":  65.41, "D2":  73.42, "E2":  82.41, "F2":  87.31, "F#2": 92.50,
    "G2":  98.00, "A2": 110.00, "Bb2": 116.54, "B2": 123.47,
    "C3": 130.81, "C#3": 138.59, "D3": 146.83, "D#3": 155.56, "E3": 164.81,
    "F3": 174.61, "F#3": 185.00, "G3": 196.00, "G#3": 207.65, "A3": 220.00,
    "Bb3": 233.08, "B3": 246.94,
    "C4": 261.63, "C#4": 277.18, "D4": 293.66, "Eb4": 311.13, "E4": 329.63,
    "F4": 349.23, "F#4": 369.99, "G4": 392.00, "G#4": 415.30, "A4": 440.00,
    "Bb4": 466.16, "B4": 493.88,
    "C5": 523.25, "D5": 587.33, "E5": 659.25, "F5": 698.46, "F#5": 739.99,
    "G5": 783.99, "A5": 880.00,
}


def _layer_drone(out_left, out_right, root_hz, start_s, dur_s, pan=0.0):
    """Low detuned triangle drone with slow LFO swell, panned L<->R."""
    n_start = int(start_s * SAMPLE_RATE)
    n_dur = int(dur_s * SAMPLE_RATE)
    n_end = min(len(out_left), n_start + n_dur)
    if n_start >= n_end:
        return
    seg = n_end - n_start
    tri = _triangle(root_hz, seg / SAMPLE_RATE) * 0.45
    tri += _triangle(root_hz * 1.506, seg / SAMPLE_RATE) * 0.25
    tri += _sine(root_hz * 0.5, seg / SAMPLE_RATE) * 0.30        # sub-octave
    tri = _lowpass(tri, 420)
    t = np.arange(seg, dtype=np.float32) / SAMPLE_RATE
    lfo = 0.60 + 0.40 * np.sin(2 * np.pi * 0.07 * t)
    tri *= lfo
    # smooth bar-level ADSR so chord changes don't click
    env = _env_adsr(seg, attack=0.12, decay=0.2, sustain=0.85, release=0.12)
    tri *= env
    left_gain = math.cos((pan + 1) * math.pi / 4)
    right_gain = math.sin((pan + 1) * math.pi / 4)
    out_left[n_start:n_end] += tri * left_gain * 0.55
    out_right[n_start:n_end] += tri * right_gain * 0.55


def _layer_arpeggio(out_left, out_right, chord_notes, start_s, dur_s,
                    notes_per_bar=8, pan=0.0):
    """A soft sine-bell arpeggio stepping through chord_notes[].
    chord_notes: list of Hz values.
    """
    beat_dur = dur_s / notes_per_bar
    beat_n = int(beat_dur * SAMPLE_RATE)
    for i in range(notes_per_bar):
        note_hz = chord_notes[i % len(chord_notes)]
        note_start = start_s + i * beat_dur
        ns = int(note_start * SAMPLE_RATE)
        ne = min(len(out_left), ns + int(beat_dur * 1.1 * SAMPLE_RATE))
        if ns >= ne:
            continue
        seg = ne - ns
        tone = _sine(note_hz, seg / SAMPLE_RATE) * 0.55
        tone += _sine(note_hz * 2.004, seg / SAMPLE_RATE) * 0.18
        env = _env_adsr(seg, attack=0.04, decay=0.25, sustain=0.3, release=0.5)
        tone *= env * 0.3
        # subtle pan sway per note
        local_pan = pan + 0.3 * math.sin(i * 0.9)
        local_pan = max(-1.0, min(1.0, local_pan))
        left_gain = math.cos((local_pan + 1) * math.pi / 4)
        right_gain = math.sin((local_pan + 1) * math.pi / 4)
        out_left[ns:ne] += tone * left_gain
        out_right[ns:ne] += tone * right_gain


def _layer_melody(out_left, out_right, note_schedule):
    """note_schedule: list of (start_s, dur_s, note_hz, amp). Sustained lead
    notes that carry the theme over the arpeggio."""
    for (ts, td, f, amp) in note_schedule:
        ns = int(ts * SAMPLE_RATE)
        ne = min(len(out_left), ns + int(td * SAMPLE_RATE))
        if ns >= ne:
            continue
        seg = ne - ns
        tone = _sine(f, seg / SAMPLE_RATE) * 0.6
        tone += _sine(f * 1.004, seg / SAMPLE_RATE) * 0.3       # chorus
        tone += _triangle(f * 0.501, seg / SAMPLE_RATE) * 0.15  # sub
        env = _env_adsr(seg, attack=0.18, decay=0.2, sustain=0.6, release=0.35)
        tone *= env * amp
        # gentle wobble
        t = np.arange(seg, dtype=np.float32) / SAMPLE_RATE
        vib = 1.0 + 0.015 * np.sin(2 * np.pi * 5.0 * t)
        tone *= vib
        # add a stereo delay shimmer
        tone_echo = _delay_echo(tone, delay_s=0.27, feedback=0.25, mix=0.3)
        # slight pan offset between wet/dry for width
        out_left[ns:ne] += tone * 0.45 + tone_echo * 0.35
        out_right[ns:ne] += tone * 0.35 + tone_echo * 0.5


def _layer_percussion(out_left, out_right, beat_times, variant=0):
    """Soft filtered noise hits on beat_times (seconds)."""
    for i, ts in enumerate(beat_times):
        ns = int(ts * SAMPLE_RATE)
        hit_dur = 0.12
        hit_n = int(hit_dur * SAMPLE_RATE)
        ne = min(len(out_left), ns + hit_n)
        if ns >= ne:
            continue
        seg = ne - ns
        # alternate between low thump and high hat
        if (i + variant) % 2 == 0:
            hit = _noise(seg / SAMPLE_RATE, seed=10 + i)
            hit = _lowpass(hit, 120)  # deep thud
            hit *= _env_decay(seg, shape=18.0) * 0.45
        else:
            hit = _noise(seg / SAMPLE_RATE, seed=20 + i)
            hit = hit - _lowpass(hit, 2500)  # highpass (shimmer)
            hit *= _env_decay(seg, shape=30.0) * 0.20
        out_left[ns:ne] += hit
        out_right[ns:ne] += hit


def _music_echo_lord(duration=48.0):
    """Atmospheric composition in D minor for the Echo Lord fight.

    - 8 bars of 6 seconds each.
    - Chord progression:   i  iv  VI  v   i  iv  III v   (Dm Gm Bb Am Dm Gm F Am)
    - Layered drones, arpeggios, sparse lead, and very soft percussion.
    - Stereo panning for spatial width.
    """
    n = int(SAMPLE_RATE * duration)
    left = np.zeros(n, dtype=np.float32)
    right = np.zeros(n, dtype=np.float32)

    # 8 bars, 6 seconds each = 48s loop
    bars = 8
    bar_dur = duration / bars
    # chord roots (low octave for drone) and their arpeggio note sets
    progression = [
        ("D2", ["D3", "F3", "A3", "D4"]),   # Dm
        ("G2", ["G3", "Bb3", "D4", "G4"]),  # Gm
        ("Bb2", ["Bb3", "D4", "F4", "Bb3"]),  # Bb major
        ("A2", ["A3", "C4", "E4", "A3"]),   # Am
        ("D2", ["D3", "F3", "A3", "D4"]),   # Dm
        ("G2", ["G3", "Bb3", "D4", "F4"]),  # Gm (with dim7 flavor)
        ("F2", ["F3", "A3", "C4", "F4"]),   # F major (relief)
        ("A2", ["A3", "C4", "E4", "G3"]),   # Am7 (dominant-ish)
    ]
    # build drones + arpeggios
    for bar_idx, (root_key, arp_keys) in enumerate(progression):
        start_s = bar_idx * bar_dur
        root_hz = _NOTE[root_key]
        arp_hz = [_NOTE[k] for k in arp_keys]
        # pan alternates subtly per bar for motion
        drone_pan = 0.15 * ((-1) ** bar_idx)
        arp_pan = -drone_pan * 1.5
        _layer_drone(left, right, root_hz, start_s, bar_dur, pan=drone_pan)
        _layer_arpeggio(
            left, right, arp_hz, start_s, bar_dur,
            notes_per_bar=8, pan=arp_pan,
        )

    # sparse lead melody (A, D, E, D  F, D, C, A) with long sustained notes
    # roughly one note every 2 bars, drifting in and out
    lead_hz_schedule = [
        (bar_dur * 0 + 1.5, bar_dur * 2 - 1.5, _NOTE["A3"], 0.35),
        (bar_dur * 2 + 1.0, bar_dur * 2 - 1.0, _NOTE["D4"], 0.38),
        (bar_dur * 4 + 1.0, bar_dur * 2 - 0.5, _NOTE["F4"], 0.42),
        (bar_dur * 6 + 0.5, bar_dur * 2 - 2.0, _NOTE["E4"], 0.38),
        (bar_dur * 7 + 2.5, bar_dur - 0.5, _NOTE["D4"], 0.30),
    ]
    _layer_melody(left, right, lead_hz_schedule)

    # soft percussion on beats 1 of each bar + pick-up on beat 3 of some bars
    beats = []
    for bar_idx in range(bars):
        beats.append(bar_idx * bar_dur + 0.02)
        # accent on bar 3 of progression (Bb / relief)
        if bar_idx in (2, 4, 6):
            beats.append(bar_idx * bar_dur + bar_dur * 0.5)
    _layer_percussion(left, right, beats)

    # faint background pad: filtered noise modulated by LFO
    bed = _noise(duration, seed=42)
    bed = _lowpass(bed, 380)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    bed_lfo = 0.25 + 0.15 * np.sin(2 * np.pi * 0.05 * t)
    bed *= bed_lfo
    left += bed * 0.12
    right += bed * 0.10       # slight stereo imbalance for atmosphere

    # ensure clean loop: crossfade first and last 200ms
    xfade_n = int(0.2 * SAMPLE_RATE)
    if n > 2 * xfade_n:
        fade = np.linspace(0, 1, xfade_n, dtype=np.float32)
        left[:xfade_n] = left[:xfade_n] * fade + left[-xfade_n:] * (1 - fade) * 0.35
        right[:xfade_n] = right[:xfade_n] * fade + right[-xfade_n:] * (1 - fade) * 0.35

    # normalize per-channel then return paired arrays
    peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))), 1e-6)
    target = 0.6
    left *= target / peak
    right *= target / peak
    return left, right


def _finalize_stereo(left, right, target=0.6):
    """Crossfade the loop edge and normalize both channels."""
    n = len(left)
    xfade_n = int(0.2 * SAMPLE_RATE)
    if n > 2 * xfade_n:
        fade = np.linspace(0, 1, xfade_n, dtype=np.float32)
        left[:xfade_n] = left[:xfade_n] * fade + left[-xfade_n:] * (1 - fade) * 0.35
        right[:xfade_n] = right[:xfade_n] * fade + right[-xfade_n:] * (1 - fade) * 0.35
    peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))), 1e-6)
    left *= target / peak
    right *= target / peak
    return left, right


def _music_twin_sovereigns(duration=40.0):
    """Bright cosmic theme with day/night alternation: G major bars alternate
    with parallel G minor bars for a solar/lunar duality."""
    n = int(SAMPLE_RATE * duration)
    left = np.zeros(n, dtype=np.float32)
    right = np.zeros(n, dtype=np.float32)
    bars = 8
    bar_dur = duration / bars
    # alternate G major <-> G minor chord roots; day / night feel
    # major bars: G, D (V), C (IV), G    minor bars: Gm, Eb, Cm, Gm
    progression = [
        ("G2", ["G3", "B3", "D4", "G4"], True),       # G major (DAY)
        ("D3", ["D4", "F#4", "A4", "D5"], True),      # D major (DAY)
        ("F#2", ["F#3", "A3", "C#4", "F#4"], False),  # F#m (NIGHT)
        ("E3", ["E4", "G4", "B4", "E5"], False),      # Em (NIGHT)
        ("C3", ["C4", "E4", "G4", "C5"], True),       # C major (DAY, IV)
        ("A2", ["A3", "C#4", "E4", "A4"], True),      # A major (DAY)
        ("C3", ["C4", "Eb4", "G4", "C5"], False),     # Cm (NIGHT)
        ("G2", ["G3", "Bb3", "D4", "G4"], False),     # Gm (NIGHT resolution)
    ]
    for bar_idx, (root_key, arp_keys, is_bright) in enumerate(progression):
        start_s = bar_idx * bar_dur
        root_hz = _NOTE[root_key]
        arp_hz = [_NOTE[k] for k in arp_keys]
        # brighter bars = more pan motion + faster arp; dark bars slower
        drone_pan = 0.2 * ((-1) ** bar_idx)
        notes_per = 8 if is_bright else 6
        _layer_drone(left, right, root_hz, start_s, bar_dur, pan=drone_pan)
        _layer_arpeggio(left, right, arp_hz, start_s, bar_dur,
                        notes_per_bar=notes_per, pan=-drone_pan)
    # lead: bright pealing bell on major bars, soft croon on minor
    lead = [
        (0 * bar_dur + 1.0, bar_dur * 1.5, _NOTE["D5"], 0.40),
        (2 * bar_dur + 0.8, bar_dur * 1.8, _NOTE["A4"], 0.30),
        (4 * bar_dur + 0.6, bar_dur * 1.4, _NOTE["E5"], 0.36),
        (6 * bar_dur + 1.0, bar_dur * 1.7, _NOTE["G4"], 0.28),
    ]
    _layer_melody(left, right, lead)
    # percussion: brighter pulses on day bars, deeper thuds on night bars
    beats = []
    for i, (_, _, bright) in enumerate(progression):
        beats.append(i * bar_dur + 0.02)
        if bright:
            beats.append(i * bar_dur + bar_dur * 0.5)
    _layer_percussion(left, right, beats, variant=0)
    return _finalize_stereo(left, right)


def _music_fate_weaver(duration=44.0):
    """Tense mystical A-minor piece - harp-like arpeggios + violin sustains."""
    n = int(SAMPLE_RATE * duration)
    left = np.zeros(n, dtype=np.float32)
    right = np.zeros(n, dtype=np.float32)
    bars = 8
    bar_dur = duration / bars
    # A minor progression with tritone tension: Am, Dm, F, E7, Am, Gm, Dm, E
    progression = [
        ("A2", ["A3", "C4", "E4", "A4"]),     # Am
        ("D3", ["D4", "F4", "A4", "D5"]),     # Dm
        ("F2", ["F3", "A3", "C4", "F4"]),     # F major (VI)
        ("E3", ["E4", "G#3", "B3", "E4"]),    # E (V of A) - tension
        ("A2", ["A3", "C4", "E4", "A4"]),     # Am
        ("G2", ["G3", "Bb3", "D4", "G4"]),    # Gm (passing)
        ("D3", ["D4", "F4", "A4", "D5"]),     # Dm
        ("E3", ["E4", "G#3", "B3", "D4"]),    # E dominant 7 (back to Am)
    ]
    for bar_idx, (root_key, arp_keys) in enumerate(progression):
        start_s = bar_idx * bar_dur
        root_hz = _NOTE[root_key]
        arp_hz = [_NOTE[k] for k in arp_keys]
        # faster arp pattern - 12 notes per bar for harp feel
        _layer_drone(left, right, root_hz, start_s, bar_dur,
                     pan=0.1 * ((-1) ** bar_idx))
        _layer_arpeggio(left, right, arp_hz, start_s, bar_dur,
                        notes_per_bar=12, pan=-0.15 * ((-1) ** bar_idx))
    # sustained violin-style lead (long pianissimo notes)
    lead = [
        (0 * bar_dur + 1.0, bar_dur * 1.8, _NOTE["E4"], 0.32),
        (2 * bar_dur + 0.8, bar_dur * 1.6, _NOTE["A4"], 0.38),
        (4 * bar_dur + 0.6, bar_dur * 1.8, _NOTE["C5"], 0.40),
        (6 * bar_dur + 1.2, bar_dur * 1.5, _NOTE["E5"], 0.30),
    ]
    _layer_melody(left, right, lead)
    # tense low percussion on beats 1 and 3 of each bar
    beats = []
    for i in range(bars):
        beats.append(i * bar_dur + 0.02)
        beats.append(i * bar_dur + bar_dur * 0.5)
    _layer_percussion(left, right, beats, variant=1)
    return _finalize_stereo(left, right)


def _music_mirrorwright(duration=44.0):
    """Glassy ethereal F# minor with a mirror-drone bass."""
    n = int(SAMPLE_RATE * duration)
    left = np.zeros(n, dtype=np.float32)
    right = np.zeros(n, dtype=np.float32)
    bars = 8
    bar_dur = duration / bars
    # F#m progression with modal flavour: F#m, C#m, B, A, F#m, D, C#7, F#m
    progression = [
        ("F#2", ["F#3", "A3", "C#4", "F#4"]),  # F#m
        ("C#3", ["C#4", "E4", "G#3", "C#4"]),  # C#m
        ("B2", ["B3", "D4", "F#4", "B4"]),     # B major
        ("A2", ["A3", "C#4", "E4", "A4"]),     # A major
        ("F#2", ["F#3", "A3", "C#4", "F#4"]),  # F#m
        ("D3", ["D4", "F#4", "A4", "D5"]),     # D major
        ("C#3", ["C#4", "F4", "G#3", "C#4"]),  # C#7 (approach)
        ("F#2", ["F#3", "A3", "C#4", "F#4"]),  # F#m resolution
    ]
    for bar_idx, (root_key, arp_keys) in enumerate(progression):
        start_s = bar_idx * bar_dur
        root_hz = _NOTE[root_key]
        arp_hz = [_NOTE[k] for k in arp_keys]
        _layer_drone(left, right, root_hz, start_s, bar_dur,
                     pan=0.12 * ((-1) ** bar_idx))
        # 16-note arpeggio for glassy twinkle, panning more extreme
        _layer_arpeggio(left, right, arp_hz, start_s, bar_dur,
                        notes_per_bar=16, pan=-0.35 * ((-1) ** bar_idx))
    lead = [
        (0 * bar_dur + 1.5, bar_dur * 1.2, _NOTE["C#4"], 0.30),
        (2 * bar_dur + 0.5, bar_dur * 1.6, _NOTE["F#4"], 0.38),
        (4 * bar_dur + 1.0, bar_dur * 1.4, _NOTE["A4"], 0.34),
        (6 * bar_dur + 0.5, bar_dur * 1.5, _NOTE["C#4"], 0.32),
    ]
    _layer_melody(left, right, lead)
    # sparse shimmering hats (hi-noise)
    beats = [i * bar_dur + bar_dur * 0.75 for i in range(bars)]
    beats += [i * bar_dur + bar_dur * 0.25 for i in range(0, bars, 2)]
    _layer_percussion(left, right, beats, variant=1)
    return _finalize_stereo(left, right)


def _music_hollow_king(duration=44.0):
    """Dark royal C minor - slow heavy brass-pad feel."""
    n = int(SAMPLE_RATE * duration)
    left = np.zeros(n, dtype=np.float32)
    right = np.zeros(n, dtype=np.float32)
    bars = 8
    bar_dur = duration / bars
    # Cm with dark passing chords: Cm, Ab, Eb, Bb, Cm, Fm, Ab, G (dominant)
    progression = [
        ("C2",  ["C3", "Eb4", "G4", "C4"]),    # Cm
        ("C#3", ["C4", "F3", "Eb4", "C4"]),    # Ab (VI) approximation
        ("Eb4", ["Eb4", "G4", "Bb4", "Eb4"]),  # Eb (III)
        ("Bb2", ["Bb3", "D4", "F4", "Bb3"]),   # Bb (VII)
        ("C2",  ["C3", "Eb4", "G4", "C4"]),    # Cm
        ("F2",  ["F3", "Ab3", "C4", "F4"]),    # Fm (iv)
        ("C#3", ["C4", "F3", "Eb4", "C4"]),    # Ab (VI)
        ("G2",  ["G3", "B3", "D4", "G4"]),     # G major (V) - tension
    ]
    # We reference Ab via "C#3" key which is actually C# - that's a little
    # off key. Let's substitute G#3 for Ab references (G# and Ab share pitch).
    def _sub_ab(notes):
        return [("G#3" if n == "Ab3" else "G#4" if n == "Ab4" else n) for n in notes]
    for bar_idx, (root_key, arp_keys) in enumerate(progression):
        start_s = bar_idx * bar_dur
        root_hz = _NOTE[root_key]
        arp_hz = [_NOTE[k] for k in _sub_ab(arp_keys)]
        _layer_drone(left, right, root_hz, start_s, bar_dur,
                     pan=0.08 * ((-1) ** bar_idx))
        # slow brass pad - 4 notes per bar, long sustain
        _layer_arpeggio(left, right, arp_hz, start_s, bar_dur,
                        notes_per_bar=4, pan=-0.1 * ((-1) ** bar_idx))
    lead = [
        (0 * bar_dur + 2.0, bar_dur * 2.0, _NOTE["G3"], 0.38),
        (2 * bar_dur + 1.5, bar_dur * 1.8, _NOTE["Eb4"], 0.42),
        (4 * bar_dur + 1.8, bar_dur * 1.8, _NOTE["C4"], 0.40),
        (6 * bar_dur + 2.0, bar_dur * 1.6, _NOTE["G3"], 0.36),
    ]
    _layer_melody(left, right, lead)
    # slow heavy drum - beat 1 every bar
    beats = [i * bar_dur + 0.05 for i in range(bars)]
    _layer_percussion(left, right, beats, variant=0)
    return _finalize_stereo(left, right)


# ---------- level-specific SFX ----------

# --- Level 2 (Twin Sovereigns) ---

def _fx_sunlance_charge():
    dur = 0.5
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    # rising bright tone, sun gathering
    f = 200 + 600 * (t / dur) ** 1.4
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    tone = np.sin(phase) * 0.5 + np.sin(phase * 1.498) * 0.3 + np.sin(phase * 2.0) * 0.18
    env = _env_adsr(n, attack=0.10, decay=0.30, sustain=0.55, release=0.40)
    return _normalize(tone * env, 0.65)


def _fx_sunlance_fire():
    dur = 0.45
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    # bright noise burst with downward sweep
    noise = _noise(dur, seed=11)
    body = noise * _env_decay(n, shape=4.0)
    f = 1500 - 1000 * (t / dur)
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    sweep = np.sin(phase) * _env_decay(n, shape=3.0) * 0.6
    return _normalize(body * 0.7 + sweep, 0.85)


def _fx_solar_flare():
    dur = 0.7
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    # whoosh of expanding fire
    noise = _noise(dur, seed=12)
    lp_cutoff_traj = 1500 + 800 * np.sin(2 * np.pi * 2.0 * t)
    body = _lowpass(noise, 1500) * _env_adsr(n, 0.05, 0.2, 0.5, 0.6)
    crackle = _noise(dur, seed=13) * 0.3 * _env_decay(n, shape=2.5)
    return _normalize(body * 0.8 + crackle, 0.7)


def _fx_lunar_orbit():
    dur = 0.6
    n = int(SAMPLE_RATE * dur)
    # ethereal chime - moon appearing
    bell = _sine(659, dur) * 0.5 + _sine(880, dur) * 0.3 + _sine(440, dur) * 0.25
    bell *= _env_decay(n, shape=4.0)
    shimmer = _noise(0.15, seed=14) * _env_decay(int(SAMPLE_RATE * 0.15), shape=12.0) * 0.3
    pad = np.zeros(n, dtype=np.float32)
    pad[:len(shimmer)] = shimmer
    return _normalize(bell + pad, 0.6)


def _fx_star_fall_warn():
    dur = 0.4
    n = int(SAMPLE_RATE * dur)
    # eerie low tone
    tone = _sine(220, dur) * 0.4 + _sine(330, dur) * 0.2
    tone *= _env_adsr(n, 0.10, 0.20, 0.5, 0.5)
    return _normalize(tone, 0.45)


def _fx_star_fall_impact():
    dur = 0.45
    n = int(SAMPLE_RATE * dur)
    # bass thud + dark shimmer
    thud = _sine(70, dur) * _env_decay(n, shape=8.0)
    crack = _noise(0.06, seed=15) * _env_decay(int(SAMPLE_RATE * 0.06), shape=30.0)
    full = np.zeros(n, dtype=np.float32)
    full[:len(crack)] = crack
    dark = _sine(180, dur) * _env_decay(n, shape=4.0) * 0.4
    return _normalize(thud * 0.9 + full * 0.7 + dark, 0.85)


def _fx_cycle_flip():
    dur = 0.9
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    # bell-like swept tone, day/night shift
    f = 440 + 220 * np.sin(2 * np.pi * 1.5 * t)
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    bell = np.sin(phase) * 0.6 + np.sin(phase * 1.498) * 0.3
    bell *= _env_decay(n, shape=2.5)
    return _normalize(bell, 0.65)


# --- Level 3 (Fate-Weaver) ---

def _fx_thread_weave():
    dur = 0.4
    n = int(SAMPLE_RATE * dur)
    # plucked harp string
    pluck = _sine(440, dur) * 0.5 + _sine(660, dur) * 0.3 + _sine(880, dur) * 0.18
    env = _env_decay(n, shape=5.5)
    # initial click for pluck attack
    click = _noise(0.012, seed=16) * 0.5
    out = pluck * env
    out[:len(click)] += click
    return _normalize(out, 0.55)


def _fx_thread_snap():
    dur = 0.35
    n = int(SAMPLE_RATE * dur)
    # high snap + downward whip
    snap = _noise(0.04, seed=17) * _env_decay(int(SAMPLE_RATE * 0.04), shape=40.0)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    f = 1000 - 700 * (t / dur)
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    whip = np.sin(phase) * _env_decay(n, shape=8.0) * 0.5
    out = whip
    out[:len(snap)] += snap * 0.9
    return _normalize(out, 0.85)


def _fx_fated_strike_warn():
    dur = 0.6
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    # ominous low pulse rising
    f = 130 + 80 * (t / dur)
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    tone = np.sin(phase) * 0.6
    pulse = 0.5 + 0.5 * np.sin(2 * np.pi * 8.0 * t)
    tone *= pulse
    env = _env_adsr(n, 0.08, 0.20, 0.7, 0.30)
    return _normalize(tone * env, 0.55)


def _fx_fated_strike_impact():
    dur = 0.6
    n = int(SAMPLE_RATE * dur)
    # heavy violet thunder - sub bass + crack + bell ring
    sub = _sine(55, dur) * _env_decay(n, shape=5.0)
    crack = _noise(0.08, seed=18) * _env_decay(int(SAMPLE_RATE * 0.08), shape=22.0)
    crack_full = np.zeros(n, dtype=np.float32)
    crack_full[:len(crack)] = crack
    bell = _sine(330, dur) * 0.4 + _sine(495, dur) * 0.3
    bell *= _env_decay(n, shape=4.0)
    return _normalize(sub * 1.0 + crack_full * 0.8 + bell * 0.5, 0.95)


def _fx_weft_pulse():
    dur = 0.7
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    # tense string resonance
    f = 196.0
    tone = (_sine(f, dur) * 0.4 + _sine(f * 2.0, dur) * 0.3 +
            _sine(f * 3.0, dur) * 0.2 + _sine(f * 4.0, dur) * 0.1)
    # tremolo
    tremolo = 0.5 + 0.5 * np.sin(2 * np.pi * 12.0 * t)
    tone *= tremolo
    env = _env_adsr(n, 0.05, 0.30, 0.65, 0.45)
    return _normalize(tone * env, 0.65)


def _fx_pull_dash():
    dur = 0.45
    n = int(SAMPLE_RATE * dur)
    # whoosh of fast travel
    noise = _noise(dur, seed=19)
    lp = _lowpass(noise, 800)
    env = _env_adsr(n, 0.05, 0.15, 0.6, 0.5)
    body = lp * env
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    f = 800 - 500 * (t / dur)
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    sweep = np.sin(phase) * _env_decay(n, shape=4.0) * 0.3
    return _normalize(body * 0.85 + sweep, 0.75)


# --- Level 4 (Mirrorwright) ---

def _fx_mirror_sweep():
    dur = 0.35
    n = int(SAMPLE_RATE * dur)
    # glass-like swoosh
    noise = _noise(dur, seed=20)
    hp = noise - _lowpass(noise, 2500)
    env = _env_adsr(n, 0.03, 0.12, 0.4, 0.6)
    body = hp * env
    bell = _sine(1200, dur) * _env_decay(n, shape=8.0) * 0.4
    return _normalize(body * 0.7 + bell, 0.7)


def _fx_phantom_spawn():
    dur = 0.5
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    # eerie rising whisper
    f = 400 + 600 * (t / dur)
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    whisper = np.sin(phase) * _env_adsr(n, 0.20, 0.30, 0.6, 0.5) * 0.3
    noise = _noise(dur, seed=21) * 0.15 * _env_adsr(n, 0.30, 0.30, 0.5, 0.40)
    return _normalize(whisper + noise, 0.5)


def _fx_dash_shatter():
    dur = 0.7
    n = int(SAMPLE_RATE * dur)
    # huge glass crack with bright explosion
    crack = _noise(0.08, seed=22) * _env_decay(int(SAMPLE_RATE * 0.08), shape=20.0)
    crack_full = np.zeros(n, dtype=np.float32)
    crack_full[:len(crack)] = crack
    # cluster of bell tones
    bells = (_sine(523, dur) * 0.5 + _sine(659, dur) * 0.4 + _sine(880, dur) * 0.3 +
             _sine(1047, dur) * 0.25)
    bells *= _env_decay(n, shape=4.0)
    sub = _sine(80, dur) * _env_decay(n, shape=6.0) * 0.4
    return _normalize(crack_full * 1.0 + bells * 0.7 + sub, 1.0)


def _fx_auto_shatter():
    dur = 0.6
    n = int(SAMPLE_RATE * dur)
    # menacing red detonation
    sub = _sine(60, dur) * _env_decay(n, shape=5.0)
    distort = _noise(0.15, seed=23) * _env_decay(int(SAMPLE_RATE * 0.15), shape=8.0)
    distort_full = np.zeros(n, dtype=np.float32)
    distort_full[:len(distort)] = distort
    high = _sine(330, dur) * 0.4 + _sine(440, dur) * 0.3
    high *= _env_decay(n, shape=4.0)
    return _normalize(sub * 1.2 + distort_full * 0.7 + high * 0.5, 0.95)


def _fx_silver_rain_warn():
    dur = 0.4
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    # tinkling chime
    f = 880 + 200 * np.sin(2 * np.pi * 5.0 * t)
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    chime = np.sin(phase) * _env_adsr(n, 0.05, 0.2, 0.5, 0.6) * 0.4
    return _normalize(chime, 0.5)


def _fx_silver_rain_hit():
    dur = 0.3
    n = int(SAMPLE_RATE * dur)
    # multiple quick high pings
    out = np.zeros(n, dtype=np.float32)
    for i, f in enumerate((880, 1320, 1100, 990)):
        offset = int(i * SAMPLE_RATE * 0.02)
        sub_dur = 0.1
        sub_n = int(SAMPLE_RATE * sub_dur)
        if offset + sub_n > n:
            sub_n = n - offset
        ping = _sine(f, sub_n / SAMPLE_RATE) * _env_decay(sub_n, shape=20.0) * 0.3
        out[offset:offset + sub_n] += ping
    return _normalize(out, 0.65)


def _fx_shard_volley():
    dur = 0.4
    n = int(SAMPLE_RATE * dur)
    # whoosh of multiple projectiles
    noise = _noise(dur, seed=24)
    hp = noise - _lowpass(noise, 1800)
    env = _env_adsr(n, 0.03, 0.18, 0.4, 0.6)
    body = hp * env
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    f = 1000 + 200 * np.sin(2 * np.pi * 8 * t)
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    sweep = np.sin(phase) * _env_decay(n, shape=5.0) * 0.3
    return _normalize(body * 0.8 + sweep, 0.75)


def _fx_teleport():
    dur = 0.6
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    # vortex - rapid pitch sweep + reverb-like noise tail
    f = 800 + 600 * np.sin(2 * np.pi * 5 * t)
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    vortex = np.sin(phase) * _env_decay(n, shape=3.5) * 0.5
    noise = _noise(dur, seed=25) * 0.3 * _env_decay(n, shape=2.5)
    return _normalize(vortex + noise, 0.7)


# --- Level 5 (Hollow King) ---

def _fx_royal_sweep():
    dur = 0.4
    n = int(SAMPLE_RATE * dur)
    # heavier sword swing - more noise + low harmonics
    noise = _noise(dur, seed=26)
    lp = _lowpass(noise, 2000)
    env = _env_adsr(n, 0.04, 0.15, 0.5, 0.6)
    body = lp * env
    rumble = _sine(120, dur) * _env_decay(n, shape=5.0) * 0.3
    return _normalize(body * 0.95 + rumble, 0.85)


def _fx_crown_bolt_fire():
    dur = 0.35
    n = int(SAMPLE_RATE * dur)
    # ember projectile launch
    noise = _noise(dur, seed=27)
    body = _lowpass(noise, 1500) * _env_decay(n, shape=4.5)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    f = 600 - 300 * (t / dur)
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    sweep = np.sin(phase) * _env_decay(n, shape=4.0) * 0.4
    return _normalize(body * 0.7 + sweep, 0.75)


def _fx_shard_erupt():
    dur = 0.5
    n = int(SAMPLE_RATE * dur)
    # rocky earth break
    rumble = _sine(50, dur) * _env_decay(n, shape=5.0)
    crunch = _noise(0.12, seed=28) * _env_decay(int(SAMPLE_RATE * 0.12), shape=10.0)
    crunch_full = np.zeros(n, dtype=np.float32)
    crunch_full[:len(crunch)] = crunch
    return _normalize(rumble * 1.0 + crunch_full * 0.6, 0.85)


def _fx_shard_pulse():
    dur = 0.4
    n = int(SAMPLE_RATE * dur)
    # crystalline pulse - high ringing tones
    bell = _sine(1100, dur) * 0.5 + _sine(1650, dur) * 0.35 + _sine(2200, dur) * 0.25
    bell *= _env_decay(n, shape=6.0)
    return _normalize(bell, 0.6)


def _fx_ring_slam():
    dur = 0.7
    n = int(SAMPLE_RATE * dur)
    # heavy boom + expanding rumble
    boom = _sine(60, dur) * _env_decay(n, shape=4.0)
    crack = _noise(0.1, seed=29) * _env_decay(int(SAMPLE_RATE * 0.1), shape=15.0)
    crack_full = np.zeros(n, dtype=np.float32)
    crack_full[:len(crack)] = crack
    rumble_tail = _noise(dur, seed=30) * _env_decay(n, shape=3.0) * 0.25
    return _normalize(boom * 1.0 + crack_full * 0.8 + rumble_tail, 0.95)


def _fx_void_step():
    dur = 0.65
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    # void portal - dark whoosh with descending pitch
    f = 600 - 400 * (t / dur)
    phase = np.cumsum(2 * np.pi * f / SAMPLE_RATE)
    portal = np.sin(phase) * _env_decay(n, shape=2.5) * 0.5
    noise = _noise(dur, seed=31) * 0.3 * _env_decay(n, shape=2.0)
    sub = _sine(80, dur) * _env_decay(n, shape=3.0) * 0.4
    return _normalize(portal + noise + sub, 0.8)


# ---------- public API ----------

class SoundSystem:
    _sounds = {}
    _music_tracks = {}        # key -> pygame.mixer.Sound
    _music_channel = None
    _current_music_key = None
    _initialized = False
    _enabled = False
    _sfx_volume = 0.7
    _music_volume = 0.4

    @classmethod
    def init(cls):
        if cls._initialized:
            return
        cls._initialized = True
        if not _NUMPY:
            cls._enabled = False
            return
        try:
            pygame.mixer.pre_init(frequency=SAMPLE_RATE, size=-16, channels=STEREO, buffer=1024)
            pygame.mixer.init()
        except pygame.error:
            cls._enabled = False
            return
        pygame.mixer.set_num_channels(24)
        cls._enabled = True
        cls._build_sound_bank()

    @classmethod
    def _build_sound_bank(cls):
        """Synthesize every sound effect and BGM once, cache."""
        sfx_builders = {
            # shared
            "sword_swing":   _fx_sword_swing,
            "boss_hit":      _fx_boss_hit,
            "player_hit":    _fx_player_hit,
            "dash":          _fx_dash,
            "boss_death":    _fx_boss_death,
            "player_death":  _fx_player_death,
            # echo lord
            "echo_warn":     _fx_echo_warn,
            "echo_slash":    _fx_echo_slash,
            "echo_spawn":    _fx_echo_spawn,
            "cascade":       _fx_cascade,
            "memory_surge":  _fx_memory_surge,
            # twin sovereigns
            "sunlance_charge":   _fx_sunlance_charge,
            "sunlance_fire":     _fx_sunlance_fire,
            "solar_flare":       _fx_solar_flare,
            "lunar_orbit":       _fx_lunar_orbit,
            "star_fall_warn":    _fx_star_fall_warn,
            "star_fall_impact":  _fx_star_fall_impact,
            "cycle_flip":        _fx_cycle_flip,
            # fate-weaver
            "thread_weave":          _fx_thread_weave,
            "thread_snap":           _fx_thread_snap,
            "fated_strike_warn":     _fx_fated_strike_warn,
            "fated_strike_impact":   _fx_fated_strike_impact,
            "weft_pulse":            _fx_weft_pulse,
            "pull_dash":             _fx_pull_dash,
            # mirrorwright
            "mirror_sweep":      _fx_mirror_sweep,
            "phantom_spawn":     _fx_phantom_spawn,
            "dash_shatter":      _fx_dash_shatter,
            "auto_shatter":      _fx_auto_shatter,
            "silver_rain_warn":  _fx_silver_rain_warn,
            "silver_rain_hit":   _fx_silver_rain_hit,
            "shard_volley":      _fx_shard_volley,
            "teleport":          _fx_teleport,
            # hollow king
            "royal_sweep":      _fx_royal_sweep,
            "crown_bolt_fire":  _fx_crown_bolt_fire,
            "shard_erupt":      _fx_shard_erupt,
            "shard_pulse":      _fx_shard_pulse,
            "ring_slam":        _fx_ring_slam,
            "void_step":        _fx_void_step,
        }
        for name, fn in sfx_builders.items():
            try:
                signal = fn()
                snd = _to_sound(signal, volume=cls._sfx_volume)
                if snd is not None:
                    cls._sounds[name] = snd
            except Exception:
                pass
        # all music tracks (stereo compositions) - keyed by level mnemonic
        music_builders = {
            "echo_lord":        _music_echo_lord,
            "twin_sovereigns":  _music_twin_sovereigns,
            "fate_weaver":      _music_fate_weaver,
            "mirrorwright":     _music_mirrorwright,
            "hollow_king":      _music_hollow_king,
        }
        for key, fn in music_builders.items():
            try:
                left, right = fn()
                snd = _to_sound(left, volume=cls._music_volume, right=right)
                if snd is not None:
                    cls._music_tracks[key] = snd
            except Exception:
                pass

    @classmethod
    def play(cls, name, volume_mod=1.0):
        if not cls._enabled:
            return
        snd = cls._sounds.get(name)
        if snd is None:
            return
        ch = pygame.mixer.find_channel(True)
        if ch is None:
            return
        ch.set_volume(min(1.0, cls._sfx_volume * volume_mod))
        ch.play(snd)

    @classmethod
    def play_music(cls, key="echo_lord"):
        """Switch to the named track, looping. No-op if same key already playing."""
        if not cls._enabled:
            return
        track = cls._music_tracks.get(key)
        if track is None:
            return
        if cls._current_music_key == key and cls._music_channel and cls._music_channel.get_busy():
            return
        if cls._music_channel is None:
            cls._music_channel = pygame.mixer.Channel(0)
        cls._music_channel.set_volume(cls._music_volume)
        cls._music_channel.play(track, loops=-1, fade_ms=800)
        cls._current_music_key = key

    @classmethod
    def stop_music(cls, fade_ms=400):
        if cls._music_channel is None:
            return
        try:
            cls._music_channel.fadeout(fade_ms)
        except pygame.error:
            pass
        cls._current_music_key = None
