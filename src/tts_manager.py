"""Text-to-Speech manager with Piper integration."""

import subprocess
import os
from pathlib import Path
from typing import Optional
import threading
import queue
import time


class PiperTTS:
    """Piper TTS integration for robot voice."""

    def __init__(
        self,
        piper_path: str = "/home/administrator/piper/piper",
        model_path: str = "/home/administrator/piper/en_US-lessac-medium.onnx",
        sample_rate: int = 22050
    ):
        """
        Initialize Piper TTS.

        Args:
            piper_path: Path to piper executable
            model_path: Path to voice model (.onnx file)
            sample_rate: Audio sample rate (Hz)
        """
        self.piper_path = Path(piper_path)
        self.model_path = Path(model_path)
        self.sample_rate = sample_rate

        # Check if Piper is installed
        if not self.piper_path.exists():
            print(f"[TTS] WARNING: Piper not found at {self.piper_path}")
            print("[TTS] Running in simulation mode (no audio output)")
            self.simulation = True
        else:
            self.simulation = False

        # Speech queue for async processing
        self.speech_queue = queue.Queue()
        self.speaking = False
        self.enabled = True
        self.running = True

        # Background thread
        self.tts_thread = threading.Thread(target=self._speech_loop, daemon=True)
        self.tts_thread.start()

    def speak(self, text: str, blocking: bool = False):
        """
        Speak text using Piper TTS.

        Args:
            text: Text to speak
            blocking: Wait for speech to complete
        """
        if not self.enabled or not text.strip():
            return

        if blocking:
            self._speak_blocking(text)
        else:
            # Add to queue
            if self.speech_queue.qsize() < 10:  # Limit queue size
                self.speech_queue.put(text)

    def _speak_blocking(self, text: str):
        """Speak text synchronously."""
        if self.simulation:
            print(f"[TTS Simulation] 🔊 '{text}'")
            time.sleep(len(text) * 0.05)  # Simulate speech duration
            return

        try:
            # Generate speech with Piper
            cmd = [
                str(self.piper_path),
                "--model", str(self.model_path),
                "--output-raw"
            ]

            piper_proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Pipe to aplay
            aplay_cmd = [
                "aplay",
                "-r", str(self.sample_rate),
                "-f", "S16_LE",
                "-t", "raw",
                "-"
            ]

            aplay_proc = subprocess.Popen(
                aplay_cmd,
                stdin=piper_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Send text
            piper_proc.stdin.write(text.encode('utf-8'))
            piper_proc.stdin.close()

            # Wait for completion
            piper_proc.wait()
            aplay_proc.wait()

            print(f"[TTS] Spoke: '{text}'")

        except Exception as e:
            print(f"[TTS] Error: {e}")

    def _speech_loop(self):
        """Background thread for async speech."""
        while self.running:
            try:
                text = self.speech_queue.get(timeout=1.0)
                self.speaking = True
                self._speak_blocking(text)
                self.speaking = False
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[TTS] Speech loop error: {e}")
                self.speaking = False

    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self.speaking

    def clear_queue(self):
        """Clear pending speech."""
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
            except queue.Empty:
                break

    def enable(self):
        """Enable TTS."""
        self.enabled = True
        print("[TTS] Enabled")

    def disable(self):
        """Disable TTS."""
        self.enabled = False
        self.clear_queue()
        print("[TTS] Disabled")

    def stop(self):
        """Stop TTS system."""
        self.running = False
        self.clear_queue()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


class VoiceNarrator:
    """Narrates robot vision and actions with intelligent speech."""

    def __init__(
        self,
        tts: PiperTTS,
        verbose: bool = True
    ):
        """
        Initialize voice narrator.

        Args:
            tts: PiperTTS instance
            verbose: Print narration to console
        """
        self.tts = tts
        self.verbose = verbose

        # Narration settings (can be toggled)
        self.narrate_detections = True
        self.narrate_navigation = True
        self.narrate_actions = False  # Too verbose by default
        self.narrate_obstacles = True

        # Rate limiting
        self.last_narration_time = 0.0
        self.min_narration_interval = 3.0  # Minimum seconds between narrations

        # Context tracking
        self.last_scene = None
        self.last_action = None

    def narrate_scene(self, scene_description: str):
        """
        Narrate what the robot sees.

        Args:
            scene_description: VLM scene description
        """
        if not self._should_narrate() or not self.narrate_detections:
            return

        # Avoid repeating same scene
        if scene_description == self.last_scene:
            return

        # Simplify for speech
        summary = self._summarize_scene(scene_description)

        if summary:
            self.tts.speak(f"I see {summary}")
            self.last_scene = scene_description
            self.last_narration_time = time.time()

    def narrate_obstacle(self, obstacle_type: str, direction: str = "ahead", distance: str = ""):
        """
        Narrate obstacle detection.

        Args:
            obstacle_type: Type of obstacle (person, chair, etc.)
            direction: Direction (left, right, center, ahead)
            distance: Optional distance description
        """
        if not self._should_narrate() or not self.narrate_obstacles:
            return

        distance_str = f"{distance} " if distance else ""
        self.tts.speak(f"Warning: {obstacle_type} detected {distance_str}{direction}")
        self.last_narration_time = time.time()

    def narrate_action(self, action: str):
        """
        Narrate movement action.

        Args:
            action: Action keyword (FORWARD, LEFT, RIGHT, STOP, etc.)
        """
        if not self.narrate_actions:
            return

        # Avoid repeating same action
        if action == self.last_action:
            return

        action_map = {
            "FORWARD": "moving forward",
            "BACKWARD": "moving backward",
            "LEFT": "turning left",
            "RIGHT": "turning right",
            "STOP": "stopping",
            "ASSESS": "analyzing situation"
        }

        speech = action_map.get(action, action.lower())
        self.tts.speak(speech)
        self.last_action = action

    def narrate_navigation_guidance(self, guidance: str):
        """
        Narrate VLM navigation guidance.

        Args:
            guidance: Navigation text from VLM
        """
        if not self._should_narrate() or not self.narrate_navigation:
            return

        # Extract actionable advice
        summary = self._extract_key_guidance(guidance)

        if summary:
            self.tts.speak(summary)
            self.last_narration_time = time.time()

    def greet(self):
        """Robot startup greeting."""
        greetings = [
            "Hello! I am your hexapod robot. My vision system is online.",
            "Systems initialized. Ready for autonomous operation.",
            "Good to see you! Vision and navigation systems are active."
        ]

        import random
        self.tts.speak(random.choice(greetings))

    def acknowledge_command(self, command: str):
        """
        Acknowledge user command.

        Args:
            command: Command description
        """
        self.tts.speak(f"Executing: {command}")

    def report_status(self, status_dict: dict):
        """
        Report system status.

        Args:
            status_dict: Status information
        """
        mode = status_dict.get('mode', 'unknown')
        self.tts.speak(f"Currently in {mode} mode")

    def say(self, text: str):
        """
        Say arbitrary text.

        Args:
            text: Text to speak
        """
        self.tts.speak(text)

    def _should_narrate(self) -> bool:
        """Check if enough time has passed since last narration."""
        elapsed = time.time() - self.last_narration_time
        return elapsed >= self.min_narration_interval

    def _summarize_scene(self, description: str) -> str:
        """
        Simplify VLM description for speech.

        Args:
            description: Full VLM scene description

        Returns:
            Simplified summary
        """
        # Simple summarization - extract first sentence or key objects
        if not description:
            return ""

        # Take first sentence
        sentences = description.split('.')
        first_sentence = sentences[0].strip()

        # Limit length
        if len(first_sentence) > 80:
            return first_sentence[:77] + "..."

        return first_sentence

    def _extract_key_guidance(self, guidance: str) -> str:
        """
        Extract actionable guidance from VLM text.

        Args:
            guidance: Full VLM navigation guidance

        Returns:
            Key actionable advice
        """
        # Simple extraction - look for action verbs
        action_phrases = [
            "move forward", "turn left", "turn right", "stop",
            "go straight", "back up", "safe to proceed", "avoid"
        ]

        guidance_lower = guidance.lower()

        for phrase in action_phrases:
            if phrase in guidance_lower:
                # Extract sentence containing this phrase
                sentences = guidance.split('.')
                for sentence in sentences:
                    if phrase in sentence.lower():
                        return sentence.strip()

        # Default: return first sentence
        sentences = guidance.split('.')
        if sentences:
            return sentences[0].strip()

        return ""

    def set_verbosity(self, detections: bool = None, navigation: bool = None,
                     actions: bool = None, obstacles: bool = None):
        """
        Configure what gets narrated.

        Args:
            detections: Narrate object detections
            navigation: Narrate navigation guidance
            actions: Narrate movement actions
            obstacles: Narrate obstacle warnings
        """
        if detections is not None:
            self.narrate_detections = detections
        if navigation is not None:
            self.narrate_navigation = navigation
        if actions is not None:
            self.narrate_actions = actions
        if obstacles is not None:
            self.narrate_obstacles = obstacles

        print(f"[Narrator] Settings: detections={self.narrate_detections}, "
              f"navigation={self.narrate_navigation}, "
              f"actions={self.narrate_actions}, "
              f"obstacles={self.narrate_obstacles}")
