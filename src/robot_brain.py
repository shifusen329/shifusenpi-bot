"""Robot Brain - Central coordinator for vision, audio, and movement.

The complete sensory AI system integrating:
- Vision (Hailo + VLM)
- Hearing (WM8960 microphone + STT)
- Speech (WM8960 speaker + TTS)
- Movement (hexapod control)
"""

import time
import threading
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

import numpy as np
from PIL import Image

from vision_manager import VisionManager, VisionMode
from audio_system import AudioSystem, AudioSystemSimulator, VoiceCommand
from vlm_client import VLMClient


class RobotState(Enum):
    """Overall robot operational states."""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    MOVING = "moving"
    ANALYZING = "analyzing"
    ERROR = "error"


@dataclass
class RobotResponse:
    """Robot's multimodal response."""
    speech: Optional[str] = None
    movement: Optional[Dict[str, Any]] = None
    vision_analysis: Optional[str] = None
    state_change: Optional[RobotState] = None


class RobotBrain:
    """Central intelligence coordinator - the robot's brain."""

    def __init__(
        self,
        enable_vision: bool = True,
        enable_audio: bool = True,
        enable_vlm: bool = True,
        simulation_mode: bool = False,
        personality: str = "friendly"
    ):
        """
        Initialize robot brain.

        Args:
            enable_vision: Enable Hailo + VLM vision
            enable_audio: Enable voice I/O
            enable_vlm: Enable VLM reasoning
            simulation_mode: Run without hardware
            personality: Robot personality (friendly, professional, sarcastic)
        """
        self.enable_vision = enable_vision
        self.enable_audio = enable_audio
        self.enable_vlm = enable_vlm
        self.simulation_mode = simulation_mode
        self.personality = personality

        # Subsystems
        self.vision: Optional[VisionManager] = None
        self.audio: Optional[AudioSystem] = None
        self.vlm: Optional[VLMClient] = None

        # State
        self.state = RobotState.IDLE
        self.running = False
        self.current_frame = None

        # Movement callback (set by robot control system)
        self.movement_callback = None

        # Stats
        self.commands_executed = 0
        self.start_time = time.time()

        # Threading
        self.lock = threading.Lock()

        # Initialize subsystems
        self._init_subsystems()

    def _init_subsystems(self):
        """Initialize all subsystems."""
        print("[Brain] Initializing robot brain...")

        # Vision system
        if self.enable_vision:
            try:
                self.vision = VisionManager(
                    use_hailo=True,
                    use_vlm=self.enable_vlm,
                    vlm_interval=5.0,
                    simulation_mode=self.simulation_mode
                )
                self.vision.set_command_callback(self._handle_vision_command)
                print("[Brain] ✓ Vision system initialized")
            except Exception as e:
                print(f"[Brain] ✗ Vision init failed: {e}")

        # Audio system
        if self.enable_audio:
            try:
                if self.simulation_mode:
                    self.audio = AudioSystemSimulator()
                else:
                    self.audio = AudioSystem(use_wake_word=True, wake_word="robot")

                self.audio.set_command_callback(self._handle_voice_command)
                print("[Brain] ✓ Audio system initialized")
            except Exception as e:
                print(f"[Brain] ✗ Audio init failed: {e}")

        # VLM client
        if self.enable_vlm and not self.vision:  # If vision didn't init VLM
            try:
                self.vlm = VLMClient()
                print("[Brain] ✓ VLM initialized")
            except Exception as e:
                print(f"[Brain] ✗ VLM init failed: {e}")

        print("[Brain] Robot brain ready! 🤖🧠")

    def start(self):
        """Start all subsystems."""
        if self.running:
            print("[Brain] Already running")
            return

        self.running = True

        if self.vision:
            self.vision.start()

        if self.audio:
            self.audio.start()

        self.state = RobotState.IDLE
        self.speak("Systems online. Ready for commands.")

        print("[Brain] All systems operational")

    def stop(self):
        """Stop all subsystems."""
        if not self.running:
            return

        self.running = False

        self.speak("Shutting down.")

        if self.vision:
            self.vision.stop()

        if self.audio:
            self.audio.stop()

        print("[Brain] Systems offline")

    def update_camera_frame(self, frame: np.ndarray):
        """
        Update current camera frame for vision processing.

        Args:
            frame: Camera frame (numpy array)
        """
        self.current_frame = frame

        if self.vision:
            self.vision.update_frame(frame)

    def _handle_voice_command(self, command: VoiceCommand):
        """
        Process voice command from audio system.

        Args:
            command: Recognized voice command
        """
        print(f"[Brain] 👂 Voice command: '{command.text}' (intent: {command.intent})")

        self.state = RobotState.THINKING

        try:
            response = self._process_command(command)
            self._execute_response(response)

        except Exception as e:
            print(f"[Brain] Command processing error: {e}")
            self.speak("Sorry, I encountered an error processing that command.")
            self.state = RobotState.ERROR

        finally:
            if self.state != RobotState.MOVING:
                self.state = RobotState.IDLE

    def _handle_vision_command(self, command: Dict[str, Any]):
        """
        Process movement command from vision system.

        Args:
            command: Vision-generated command dict
        """
        print(f"[Brain] 👁️  Vision command: {command}")

        # Forward to movement system if not in manual control
        if self.movement_callback and self.vision.mode != VisionMode.MANUAL:
            self.movement_callback(command)

    def _process_command(self, command: VoiceCommand) -> RobotResponse:
        """
        Process command and generate response.

        Args:
            command: Voice command

        Returns:
            Robot response with speech/movement/analysis
        """
        intent = command.intent
        text = command.text.lower()

        # Movement commands
        if intent == 'move_forward':
            return RobotResponse(
                speech=self._get_acknowledgment(),
                movement={'action': 'FORWARD', 'duration': 2.0}
            )

        elif intent == 'move_backward':
            return RobotResponse(
                speech="Moving backward",
                movement={'action': 'BACKWARD', 'duration': 2.0}
            )

        elif intent == 'turn_left':
            return RobotResponse(
                speech="Turning left",
                movement={'action': 'LEFT', 'angle': 45}
            )

        elif intent == 'turn_right':
            return RobotResponse(
                speech="Turning right",
                movement={'action': 'RIGHT', 'angle': 45}
            )

        elif intent == 'stop':
            return RobotResponse(
                speech="Stopping",
                movement={'action': 'STOP'}
            )

        # Vision commands
        elif intent == 'describe_scene':
            if self.vision and self.current_frame is not None:
                analysis = self.vision.manual_vlm_query("Describe what you see in detail.")
                return RobotResponse(
                    speech=f"I see: {analysis}",
                    vision_analysis=analysis
                )
            else:
                return RobotResponse(speech="Vision system not available")

        elif intent == 'find_object':
            # Extract object from text
            obj = self._extract_object(text)
            if self.vision and obj:
                query = f"Can you see a {obj} in this image? Where is it located?"
                result = self.vision.manual_vlm_query(query)
                return RobotResponse(
                    speech=result,
                    vision_analysis=result
                )
            else:
                return RobotResponse(speech=f"Looking for {obj if obj else 'object'}...")

        # Mode changes
        elif intent == 'follow_person':
            if self.vision:
                self.vision.set_mode(VisionMode.AUTONOMOUS)
                return RobotResponse(
                    speech="Following mode activated. I'll track the nearest person.",
                    state_change=RobotState.MOVING
                )
            else:
                return RobotResponse(speech="Vision system required for following mode")

        # Status commands
        elif intent == 'check_battery':
            # TODO: Get actual battery status
            return RobotResponse(speech="Battery at 85 percent")

        elif intent == 'report_status':
            status = self.get_status()
            speech = f"Status report: Vision {status['vision_enabled']}, " \
                     f"Audio {status['audio_enabled']}, " \
                     f"Mode: {status['state']}"
            return RobotResponse(speech=speech)

        # Unknown
        else:
            if self.vlm and self.current_frame is not None:
                # Ask VLM for help with unknown command
                response = self.vision.manual_vlm_query(
                    f"A robot heard this command: '{command.text}'. "
                    f"Based on what you see, what should the robot do?"
                )
                return RobotResponse(speech=response)
            else:
                return RobotResponse(
                    speech="I didn't understand that command. Try: forward, left, right, or describe scene."
                )

    def _execute_response(self, response: RobotResponse):
        """
        Execute robot response.

        Args:
            response: Response to execute
        """
        # Speech
        if response.speech:
            self.speak(response.speech)

        # State change
        if response.state_change:
            self.state = response.state_change

        # Movement
        if response.movement:
            self.state = RobotState.MOVING
            if self.movement_callback:
                self.movement_callback(response.movement)
            self.commands_executed += 1

    def _extract_object(self, text: str) -> Optional[str]:
        """Extract object name from text like 'find the cup'."""
        words = text.split()
        # Simple extraction - look after "find" or "where is"
        if 'find' in words:
            idx = words.index('find') + 1
            if idx < len(words):
                return ' '.join(words[idx:]).replace('the', '').replace('a', '').strip()
        elif 'where' in text:
            # Extract after "where is"
            return text.split('where is')[-1].strip()
        return None

    def _get_acknowledgment(self) -> str:
        """Get personality-appropriate acknowledgment."""
        if self.personality == "friendly":
            import random
            return random.choice([
                "Sure thing!",
                "On it!",
                "Right away!",
                "You got it!",
                "Moving now!"
            ])
        elif self.personality == "professional":
            return "Acknowledged. Executing."
        elif self.personality == "sarcastic":
            import random
            return random.choice([
                "Oh, forward. How exciting.",
                "Sure, because I have nothing better to do.",
                "Your wish is my command... I guess.",
                "Fine, fine. Moving."
            ])
        else:
            return "OK"

    def speak(self, text: str, wait: bool = False):
        """
        Make robot speak.

        Args:
            text: Text to speak
            wait: Wait for speech to complete
        """
        if self.audio:
            self.state = RobotState.SPEAKING
            self.audio.speak(text, wait=wait)
            if not wait:
                time.sleep(0.1)  # Brief pause
            self.state = RobotState.IDLE
        else:
            print(f"[Brain] 🗣️  {text}")

    def set_movement_callback(self, callback):
        """Set callback for movement commands."""
        self.movement_callback = callback

    def get_status(self) -> Dict[str, Any]:
        """Get complete system status."""
        status = {
            "state": self.state.value,
            "running": self.running,
            "vision_enabled": self.vision is not None,
            "audio_enabled": self.audio is not None,
            "vlm_enabled": self.vlm is not None,
            "uptime": round(time.time() - self.start_time, 1),
            "commands_executed": self.commands_executed
        }

        if self.vision:
            status["vision_status"] = self.vision.get_status()

        if self.audio:
            status["audio_stats"] = self.audio.get_stats()

        return status

    def demo_conversation(self):
        """Run a demo conversation (simulation mode)."""
        if not self.simulation_mode or not self.audio:
            print("[Brain] Demo requires simulation mode with audio")
            return

        print("\n" + "="*60)
        print("ROBOT BRAIN DEMO CONVERSATION")
        print("="*60 + "\n")

        # Simulate conversation
        demo_commands = [
            "robot go forward",
            "robot what do you see",
            "robot turn left",
            "robot follow me",
            "robot stop"
        ]

        for cmd in demo_commands:
            print(f"\n👤 User: \"{cmd}\"")
            time.sleep(0.5)

            # Simulate voice command
            if isinstance(self.audio, AudioSystemSimulator):
                self.audio.simulate_voice_command(cmd)

            time.sleep(2.0)

        print("\n" + "="*60)
        print("DEMO COMPLETE")
        print("="*60 + "\n")

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
