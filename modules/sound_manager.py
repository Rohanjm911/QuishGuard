"""
Sound Manager - Tactical Cybersecurity Audio Feedback Engine for QuishGuard.
Synthesizes studio-grade in-memory WAV audio inspired by Apple & Google acoustic design.
Uses native Windows multimedia PlaySound API with zero external dependencies.
"""
import io
import math
import random
import struct
import sys
import threading
import wave
from typing import Dict, Any, List, Optional

try:
    import winsound
    WINSOUND_AVAILABLE = True
except Exception:
    WINSOUND_AVAILABLE = False


def _build_pcm_wav(samples: List[float], sample_rate: int = 44100) -> bytes:
    """Encodes normalized float PCM samples into an in-memory 16-bit mono RIFF WAV byte buffer."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for s in samples:
            val = int(max(-32767, min(32767, s * 27000)))
            frames.extend(struct.pack("<h", val))
        wav.writeframes(frames)
    return buf.getvalue()


class SoundManager:
    """
    Manages studio-quality acoustic feedback for QR quarantine, camera tracking,
    threat alerts, and tactile haptic taps.
    """

    def __init__(self):
        self.muted = False
        self._wav_cache: Dict[str, bytes] = {}
        self._playback_lock = threading.Lock()
        self._initialize_sound_library()

    def _initialize_sound_library(self):
        """Synthesizes all audio waveforms once on startup for instantaneous, zero-latency playback."""
        sr = 44100

        # 1. Clean QR Chime (Apple Pay / Google Pay Triad Chime: C6 -> E6 -> G6)
        n = int(sr * 0.40)
        samples_clean = []
        for i in range(n):
            t = i / sr
            ramp = min(1.0, t / 0.004)
            if t < 0.10:
                f = 1046.50  # C6
                env = math.exp(-t * 22)
            elif t < 0.22:
                f = 1318.51  # E6
                env = math.exp(-(t - 0.10) * 18)
            else:
                f = 1567.98  # G6
                env = math.exp(-(t - 0.22) * 12)
            s = (
                math.sin(2 * math.pi * f * t)
                + 0.25 * math.sin(4 * math.pi * f * t)
                + 0.08 * math.sin(6 * math.pi * f * t)
            ) * env * ramp
            samples_clean.append(s)
        self._wav_cache["clean"] = _build_pcm_wav(samples_clean, sr)

        # 2. Camera Shutter / Aperture Snap (Tactile Optical Capture)
        n = int(sr * 0.075)
        samples_shutter = []
        for i in range(n):
            t = i / sr
            env = math.exp(-t * 75)
            noise = (random.random() * 2 - 1) * 0.65
            click = math.sin(2 * math.pi * 3200 * t) * 0.5
            samples_shutter.append((noise + click) * env)
        self._wav_cache["shutter"] = _build_pcm_wav(samples_shutter, sr)

        # 3. Biometric Matrix Lock Chirp (FaceID / Optical Acquisition Sweep)
        dur_lock = 0.13
        n = int(sr * dur_lock)
        samples_lock = []
        for i in range(n):
            t = i / sr
            f = 1850.0 + (t / dur_lock) * 950.0  # 1850Hz -> 2800Hz
            env = math.sin(math.pi * t / dur_lock)
            s = (math.sin(2 * math.pi * f * t) + 0.2 * math.sin(4 * math.pi * f * t)) * env
            samples_lock.append(s)
        self._wav_cache["lock"] = _build_pcm_wav(samples_lock, sr)

        # 4. Warning Alert (Apple Amber Double Bell: A5 -> F5)
        n = int(sr * 0.36)
        samples_warn = []
        for i in range(n):
            t = i / sr
            ramp = min(1.0, t / 0.004)
            if t < 0.16:
                f = 880.00  # A5
                env = math.exp(-t * 20)
            else:
                f = 698.46  # F5
                env = math.exp(-(t - 0.16) * 16)
            s = (math.sin(2 * math.pi * f * t) + 0.35 * math.sin(4 * math.pi * f * t)) * env * ramp
            samples_warn.append(s)
        self._wav_cache["warning"] = _build_pcm_wav(samples_warn, sr)

        # 5. Critical Quarantine Alarm (Futuristic Security Dissonance Warble)
        n = int(sr * 0.52)
        samples_crit = []
        for i in range(n):
            t = i / sr
            warble = 0.5 + 0.5 * math.sin(2 * math.pi * 9 * t)
            f1, f2 = 440.0, 466.16  # Minor 2nd dissonance
            sub = 0.35 * math.sin(2 * math.pi * 180 * t)
            env = math.exp(-t * 3.8)
            s = (0.55 * math.sin(2 * math.pi * f1 * t) + 0.50 * math.sin(2 * math.pi * f2 * t) + sub) * warble * env
            samples_crit.append(s)
        self._wav_cache["critical"] = _build_pcm_wav(samples_crit, sr)

        # 6. Subtle Glass Tap / Tactile Haptic Pop (Apple iOS micro-tap)
        n = int(sr * 0.024)
        samples_tap = []
        for i in range(n):
            t = i / sr
            f = 2200 - (t / 0.024) * 1200
            env = math.exp(-t * 160)
            s = math.sin(2 * math.pi * f * t) * env
            samples_tap.append(s)
        self._wav_cache["tap"] = _build_pcm_wav(samples_tap, sr)

        # 7. Export & AirDrop Chime (Ascending Major Triad: E5 -> B5 -> E6)
        n = int(sr * 0.42)
        samples_export = []
        for i in range(n):
            t = i / sr
            ramp = min(1.0, t / 0.004)
            if t < 0.12:
                f = 659.25  # E5
                env = math.exp(-t * 20)
            elif t < 0.24:
                f = 987.77  # B5
                env = math.exp(-(t - 0.12) * 18)
            else:
                f = 1318.51  # E6
                env = math.exp(-(t - 0.24) * 12)
            s = (math.sin(2 * math.pi * f * t) + 0.28 * math.sin(4 * math.pi * f * t)) * env * ramp
            samples_export.append(s)
        self._wav_cache["export"] = _build_pcm_wav(samples_export, sr)

    def is_muted(self) -> bool:
        """Returns True if audio feedback is currently muted."""
        return self.muted

    def toggle_mute(self) -> bool:
        """Toggles audio mute state and plays confirmation cue when unmuted."""
        self.muted = not self.muted
        if not self.muted:
            self.play_scan_clean()
        return self.muted

    def _play_wav_async(self, sound_key: str, fallback_freq: int = 1500, fallback_dur: int = 60):
        """Asynchronously plays in-memory synthesized WAV audio via Windows PlaySound."""
        if self.muted or not WINSOUND_AVAILABLE or sys.platform != "win32":
            return

        wav_data = self._wav_cache.get(sound_key)

        def _worker():
            try:
                if wav_data:
                    # winsound.SND_MEMORY plays the byte array directly through Windows audio mixer
                    winsound.PlaySound(wav_data, winsound.SND_MEMORY)
                else:
                    winsound.Beep(fallback_freq, fallback_dur)
            except Exception:
                try:
                    winsound.Beep(fallback_freq, fallback_dur)
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

    # --- PUBLIC AUDIO CUES (Backward-Compatible API) ---

    def play_scan_start(self):
        """High-resolution camera shutter / aperture snap when scan begins or camera activates."""
        self._play_wav_async("shutter", fallback_freq=2200, fallback_dur=30)

    def play_shutter(self):
        """Alias for play_scan_start."""
        self.play_scan_start()

    def play_matrix_lock(self):
        """High-tech biometric optical acquisition chirp when QR matrix is locked in view."""
        self._play_wav_async("lock", fallback_freq=2400, fallback_dur=70)

    def play_scan_clean(self):
        """Pleasant Apple Pay / Google Pay major triad chime for low-risk verified QR code."""
        self._play_wav_async("clean", fallback_freq=1800, fallback_dur=100)

    def play_warning_alert(self):
        """Warm amber double-bell alert for suspicious/medium-risk scan."""
        self._play_wav_async("warning", fallback_freq=880, fallback_dur=120)

    def play_critical_alert(self):
        """Deep futuristic cyber quarantine alarm for malicious phishing / exploit payload."""
        self._play_wav_async("critical", fallback_freq=420, fallback_dur=220)

    def play_tap(self):
        """Subtle tactile glass tap / haptic feedback for buttons, switches, and copy actions."""
        self._play_wav_async("tap", fallback_freq=2000, fallback_dur=15)

    def play_export_success(self):
        """Pleasant ascending AirDrop chime when forensic report or audit log is saved."""
        self._play_wav_async("export", fallback_freq=1400, fallback_dur=110)

    def play_test_sound(self, sound_key: str):
        """Preview play a specific sound by key for testing or settings panel."""
        if sound_key == "clean":
            self.play_scan_clean()
        elif sound_key == "warning":
            self.play_warning_alert()
        elif sound_key == "critical":
            self.play_critical_alert()
        elif sound_key == "lock":
            self.play_matrix_lock()
        elif sound_key == "shutter":
            self.play_scan_start()
        elif sound_key == "export":
            self.play_export_success()
        elif sound_key == "tap":
            self.play_tap()

    def get_sound_catalog(self) -> List[Dict[str, str]]:
        """Returns catalog of all synthesized acoustic profiles with titles and descriptions."""
        return [
            {
                "key": "clean",
                "title": "🛡️ Verified Clean QR",
                "desc": "Apple Pay & Google Pay major triad chord (C6-E6-G6) for secure scans.",
                "badge": "SUCCESS",
                "badge_col": "#22c55e",
            },
            {
                "key": "warning",
                "title": "⚠️ Suspicious Caution",
                "desc": "Apple macOS amber double-bell chime (A5-F5) for redirection / warnings.",
                "badge": "CAUTION",
                "badge_col": "#f59e0b",
            },
            {
                "key": "critical",
                "title": "🚨 Critical Quarantine Alarm",
                "desc": "Futuristic minor dissonance warble alerting to phishing or exploits.",
                "badge": "ALERT",
                "badge_col": "#ef4444",
            },
            {
                "key": "lock",
                "title": "🎯 Biometric Matrix Lock",
                "desc": "High-tech FaceID / optical chirp when QR code is locked in frame.",
                "badge": "TRACKING",
                "badge_col": "#38bdf8",
            },
            {
                "key": "shutter",
                "title": "📷 Optical Shutter Snap",
                "desc": "Tactile camera aperture snapshot when scanning or loading an image.",
                "badge": "TRIGGER",
                "badge_col": "#94a3b8",
            },
            {
                "key": "export",
                "title": "📄 AirDrop Export Chime",
                "desc": "Gentle ascending chime when PDF report or CSV audit is generated.",
                "badge": "EXPORT",
                "badge_col": "#388bfd",
            },
            {
                "key": "tap",
                "title": "🔘 Tactile Glass Tap",
                "desc": "Subtle Apple iOS glass micro-tap for buttons, copies, and switches.",
                "badge": "HAPTIC",
                "badge_col": "#a855f7",
            },
        ]


sound_manager = SoundManager()
