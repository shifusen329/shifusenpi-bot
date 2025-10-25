"""Audio System - Voice input/output for Shifusenpi-Bot.

Handles speech recognition, text-to-speech, and audio I/O via WM8960.
"""

import os
import time
import queue
import threading
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum
import wave
import json

import numpy as np


class AudioMode(Enum):
    """Audio processing modes."""
    LISTENING = "listening"  # Actively listening for commands
    SPEAKING = "speaking"    # Currently outputting speech
    IDLE = "idle"           # Standby
    MUTED = "muted"         # Microphone disabled


@dataclass
class VoiceCommand:
    """Recognized voice command."""
    text: str
    confidence: float
    timestamp: float
    intent: Optional[str] = None


class AudioSystem:
    """Manages voice input/output for robot."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        use_wake_word: bool = True,
        wake_word: str = "robot"
    ):
        """
        Initialize audio system.

        Args:
            sample_rate: Audio sample rate (Hz)
            channels: Number of audio channels
            chunk_size: Audio buffer size
            use_wake_word: Enable wake word detection
            wake_word: Wake word to listen for
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.use_wake_word = use_wake_word
        self.wake_word = wake_word

        # State
        self.mode = AudioMode.IDLE
        self.running = False

        # Audio devices
        self.input_device = None
        self.output_device = None

        # Processing
        self.audio_queue = queue.Queue(maxsize=100)
        self.command_queue = queue.Queue(maxsize=10)

        # Callbacks
        self.command_callback: Optional[Callable] = None

        # Threading
        self.listen_thread: Optional[threading.Thread] = None
        self.process_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        # Stats
        self.commands_processed = 0
        self.total_speech_time = 0.0

        # Initialize
        self._init_audio()

    def _init_audio(self):
        """Initialize audio devices and engines."""
        try:
            # Import audio libraries
            import pyaudio

            self.pyaudio = pyaudio.PyAudio()

            # Find WM8960 device
            self._find_audio_device()

            print("[Audio] Audio devices initialized")

        except ImportError as e:
            print(f"[Audio] WARNING: PyAudio not available: {e}")
            print("[Audio] Running in simulation mode")
            self.pyaudio = None

    def _find_audio_device(self):
        """Find WM8960 audio device."""
        if not self.pyaudio:
            return

        # Search for WM8960 or default device
        for i in range(self.pyaudio.get_device_count()):
            info = self.pyaudio.get_device_info_by_index(i)
            if 'wm8960' in info['name'].lower() or 'usb' in info['name'].lower():
                print(f"[Audio] Found audio device: {info['name']}")
                if info['maxInputChannels'] > 0:
                    self.input_device = i
                if info['maxOutputChannels'] > 0:
                    self.output_device = i
                return

        # Use default devices
        print("[Audio] Using default audio devices")

    def start(self):
        """Start audio processing."""
        if self.running:
            print("[Audio] Already running")
            return

        self.running = True
        self.mode = AudioMode.LISTENING if not self.use_wake_word else AudioMode.IDLE

        # Start listening thread
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()

        # Start processing thread
        self.process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.process_thread.start()

        print(f"[Audio] Started in {self.mode.value} mode")

    def stop(self):
        """Stop audio processing."""
        if not self.running:
            return

        self.running = False

        if self.listen_thread:
            self.listen_thread.join(timeout=2.0)

        if self.process_thread:
            self.process_thread.join(timeout=2.0)

        if self.pyaudio:
            self.pyaudio.terminate()

        print("[Audio] Stopped")

    def _listen_loop(self):
        """Main audio capture loop."""
        print("[Audio] Listening loop started")

        if not self.pyaudio:
            # Simulation mode
            while self.running:
                time.sleep(1.0)
            return

        try:
            stream = self.pyaudio.open(
                format=self.pyaudio.get_format_from_width(2),
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.input_device,
                frames_per_buffer=self.chunk_size
            )

            while self.running:
                if self.mode in (AudioMode.LISTENING, AudioMode.IDLE):
                    data = stream.read(self.chunk_size, exception_on_overflow=False)

                    # Convert to numpy array
                    audio_data = np.frombuffer(data, dtype=np.int16)

                    # Check for voice activity
                    if self._detect_voice_activity(audio_data):
                        try:
                            self.audio_queue.put_nowait(audio_data)
                        except queue.Full:
                            pass  # Drop frame if queue full

                time.sleep(0.01)

            stream.stop_stream()
            stream.close()

        except Exception as e:
            print(f"[Audio] Listen loop error: {e}")

        print("[Audio] Listening loop ended")

    def _process_loop(self):
        """Audio processing and speech recognition loop."""
        print("[Audio] Processing loop started")

        buffer = []
        silence_frames = 0
        max_silence_frames = 30  # ~0.5s of silence

        while self.running:
            try:
                # Get audio data with timeout
                audio_data = self.audio_queue.get(timeout=1.0)

                buffer.append(audio_data)

                # Check if still speaking
                if self._detect_voice_activity(audio_data):
                    silence_frames = 0
                else:
                    silence_frames += 1

                # Process complete utterance
                if silence_frames >= max_silence_frames and len(buffer) > 10:
                    self._process_speech(np.concatenate(buffer))
                    buffer = []
                    silence_frames = 0

            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Audio] Processing error: {e}")

        print("[Audio] Processing loop ended")

    def _detect_voice_activity(self, audio_data: np.ndarray) -> bool:
        """
        Simple voice activity detection.

        Args:
            audio_data: Audio samples

        Returns:
            True if voice detected
        """
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_data.astype(float) ** 2))

        # Simple threshold-based VAD
        threshold = 500  # Adjust based on environment
        return rms > threshold

    def _process_speech(self, audio_data: np.ndarray):
        """
        Process speech audio and recognize text.

        Args:
            audio_data: Complete audio utterance
        """
        try:
            # TODO: Implement actual speech recognition
            # Options:
            # 1. Whisper (OpenAI) - local or API
            # 2. Vosk - offline, lightweight
            # 3. Google Speech API
            # 4. Azure Speech Services

            # Placeholder - simulate recognition
            text = self._simulate_recognition(audio_data)

            if text:
                command = VoiceCommand(
                    text=text,
                    confidence=0.85,
                    timestamp=time.time()
                )

                # Parse intent
                command.intent = self._parse_intent(text)

                # Queue command
                self.command_queue.put(command)
                self.commands_processed += 1

                print(f"[Audio] Recognized: '{text}' (intent: {command.intent})")

                # Callback
                if self.command_callback:
                    self.command_callback(command)

        except Exception as e:
            print(f"[Audio] Speech processing error: {e}")

    def _simulate_recognition(self, audio_data: np.ndarray) -> Optional[str]:
        """Simulate speech recognition (placeholder)."""
        # In real implementation, call STT engine here
        return None

    def _parse_intent(self, text: str) -> str:
        """
        Parse user intent from text.

        Args:
            text: Recognized text

        Returns:
            Intent classification
        """
        text_lower = text.lower()

        # Movement intents
        if any(word in text_lower for word in ['forward', 'ahead', 'go']):
            return 'move_forward'
        elif any(word in text_lower for word in ['back', 'backward', 'reverse']):
            return 'move_backward'
        elif 'left' in text_lower:
            return 'turn_left'
        elif 'right' in text_lower:
            return 'turn_right'
        elif any(word in text_lower for word in ['stop', 'halt', 'freeze']):
            return 'stop'

        # Vision intents
        elif any(word in text_lower for word in ['what do you see', 'describe', 'look']):
            return 'describe_scene'
        elif 'find' in text_lower or 'where is' in text_lower:
            return 'find_object'

        # Navigation intents
        elif 'follow' in text_lower:
            return 'follow_person'
        elif 'navigate' in text_lower or 'go to' in text_lower:
            return 'navigate_to'

        # Status intents
        elif 'battery' in text_lower or 'power' in text_lower:
            return 'check_battery'
        elif 'status' in text_lower:
            return 'report_status'

        else:
            return 'unknown'

    def speak(self, text: str, wait: bool = False):
        """
        Convert text to speech and play.

        Args:
            text: Text to speak
            wait: Wait for speech to complete
        """
        with self.lock:
            previous_mode = self.mode
            self.mode = AudioMode.SPEAKING

        try:
            print(f"[Audio] Speaking: '{text}'")

            # TODO: Implement actual TTS
            # Options:
            # 1. pyttsx3 - offline, fast
            # 2. gTTS (Google) - requires internet
            # 3. Azure TTS - high quality
            # 4. Coqui TTS - local, neural

            # Placeholder - simulate speaking
            duration = len(text) * 0.05  # ~50ms per character
            self.total_speech_time += duration

            if wait:
                time.sleep(duration)

        except Exception as e:
            print(f"[Audio] TTS error: {e}")

        finally:
            with self.lock:
                self.mode = previous_mode

    def set_command_callback(self, callback: Callable):
        """Set callback for voice commands."""
        self.command_callback = callback

    def set_mode(self, mode: AudioMode):
        """Set audio processing mode."""
        with self.lock:
            self.mode = mode
            print(f"[Audio] Mode changed to: {mode.value}")

    def mute(self):
        """Mute microphone."""
        self.set_mode(AudioMode.MUTED)

    def unmute(self):
        """Unmute microphone."""
        self.set_mode(AudioMode.LISTENING)

    def get_stats(self) -> Dict[str, Any]:
        """Get audio system statistics."""
        return {
            "mode": self.mode.value,
            "running": self.running,
            "commands_processed": self.commands_processed,
            "total_speech_time": round(self.total_speech_time, 1),
            "queue_size": self.audio_queue.qsize()
        }

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


# Simulation mode for testing
class AudioSystemSimulator(AudioSystem):
    """Simulator for testing without audio hardware."""

    def _init_audio(self):
        """Skip audio initialization."""
        print("[Audio Simulator] Running in simulation mode")
        self.pyaudio = None

    def speak(self, text: str, wait: bool = False):
        """Simulate speech."""
        print(f"[Audio Simulator] 🗣️  Speaking: '{text}'")
        if wait:
            time.sleep(len(text) * 0.03)

    def simulate_voice_command(self, text: str):
        """Manually inject voice command for testing."""
        command = VoiceCommand(
            text=text,
            confidence=1.0,
            timestamp=time.time(),
            intent=self._parse_intent(text)
        )

        self.command_queue.put(command)
        self.commands_processed += 1

        print(f"[Audio Simulator] 👂 Heard: '{text}' (intent: {command.intent})")

        if self.command_callback:
            self.command_callback(command)
