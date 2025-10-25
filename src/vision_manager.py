"""Vision Manager - Coordinates Hailo + VLM hybrid vision system."""

import time
import threading
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

import numpy as np
from PIL import Image

from vlm_client import VLMClient
from hailo_vision import HailoVision, NavigationData, HailoVisionSimulator


class VisionMode(Enum):
    """Vision processing modes."""

    MANUAL = "manual"  # User control only, no AI assistance
    ASSISTED = "assisted"  # Hailo obstacle avoidance while manual
    AUTONOMOUS = "autonomous"  # Full AI control


@dataclass
class VisionStrategy:
    """High-level vision strategy from VLM."""

    scene_description: str
    navigation_guidance: str
    recommended_action: str
    confidence: float
    timestamp: float


class VisionManager:
    """Coordinates Hailo (real-time) + VLM (reasoning) vision systems."""

    def __init__(
        self,
        use_hailo: bool = True,
        use_vlm: bool = True,
        vlm_interval: float = 5.0,
        simulation_mode: bool = False
    ):
        """
        Initialize vision manager.

        Args:
            use_hailo: Enable Hailo real-time processing
            use_vlm: Enable VLM high-level reasoning
            vlm_interval: Seconds between VLM queries
            simulation_mode: Run without hardware (testing)
        """
        self.use_hailo = use_hailo
        self.use_vlm = use_vlm
        self.vlm_interval = vlm_interval
        self.simulation_mode = simulation_mode

        # Vision systems
        self.hailo: Optional[HailoVision] = None
        self.vlm: Optional[VLMClient] = None

        # State
        self.mode = VisionMode.MANUAL
        self.running = False
        self.current_frame = None
        self.strategy: Optional[VisionStrategy] = None
        self.last_vlm_query_time = 0.0

        # Callbacks
        self.command_callback: Optional[Callable] = None

        # Threading
        self.vision_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        # Initialize systems
        self._init_systems()

    def _init_systems(self):
        """Initialize Hailo and VLM systems."""
        if self.use_hailo:
            try:
                if self.simulation_mode:
                    self.hailo = HailoVisionSimulator(enable_depth=True, enable_tracking=True)
                else:
                    self.hailo = HailoVision(enable_depth=True, enable_tracking=True)
                print("[VisionManager] Hailo initialized")
            except Exception as e:
                print(f"[VisionManager] Hailo init failed: {e}, using simulator")
                self.hailo = HailoVisionSimulator(enable_depth=True, enable_tracking=True)

        if self.use_vlm:
            try:
                self.vlm = VLMClient()
                print("[VisionManager] VLM initialized")
            except Exception as e:
                print(f"[VisionManager] VLM init failed: {e}")
                self.use_vlm = False

    def start(self):
        """Start vision processing."""
        if self.running:
            print("[VisionManager] Already running")
            return

        self.running = True

        if self.hailo:
            self.hailo.start()

        # Start vision processing thread
        self.vision_thread = threading.Thread(target=self._vision_loop, daemon=True)
        self.vision_thread.start()

        print(f"[VisionManager] Started in {self.mode.value} mode")

    def stop(self):
        """Stop vision processing."""
        if not self.running:
            return

        self.running = False

        if self.vision_thread:
            self.vision_thread.join(timeout=2.0)

        if self.hailo:
            self.hailo.stop()

        if self.vlm:
            self.vlm.close()

        print("[VisionManager] Stopped")

    def set_mode(self, mode: VisionMode):
        """Set vision processing mode."""
        self.mode = mode
        print(f"[VisionManager] Mode changed to: {mode.value}")

    def update_frame(self, frame: np.ndarray):
        """
        Update current camera frame.

        Args:
            frame: Camera frame (numpy array or PIL Image)
        """
        with self.lock:
            self.current_frame = frame

    def set_command_callback(self, callback: Callable):
        """
        Set callback for sending movement commands.

        Args:
            callback: Function to call with command dict
        """
        self.command_callback = callback

    def _vision_loop(self):
        """Main vision processing loop."""
        print("[VisionManager] Vision loop started")

        while self.running:
            try:
                # Get current frame
                with self.lock:
                    frame = self.current_frame

                if frame is None:
                    time.sleep(0.1)
                    continue

                # Process based on mode
                if self.mode == VisionMode.MANUAL:
                    # Manual mode: No AI processing
                    pass

                elif self.mode == VisionMode.ASSISTED:
                    # Assisted mode: Hailo only for safety
                    self._process_assisted(frame)

                elif self.mode == VisionMode.AUTONOMOUS:
                    # Autonomous mode: Full AI control
                    self._process_autonomous(frame)

                time.sleep(0.03)  # ~30 FPS

            except Exception as e:
                print(f"[VisionManager] Error in vision loop: {e}")
                time.sleep(1.0)

        print("[VisionManager] Vision loop ended")

    def _process_assisted(self, frame):
        """Process frame in assisted mode (obstacle avoidance only)."""
        if not self.hailo:
            return

        # Get navigation data from Hailo
        nav_data = self.hailo.get_navigation_data()

        # Check for critical alerts
        if nav_data.critical_alerts:
            for alert in nav_data.critical_alerts:
                print(f"[VisionManager] {alert}")
                # Send emergency stop
                self._send_command({"action": "STOP", "reason": alert})

        # Check for obstacles in path
        if nav_data.obstacles:
            print(f"[VisionManager] {len(nav_data.obstacles)} obstacles detected")
            # Can send warnings but don't override user control

    def _process_autonomous(self, frame):
        """Process frame in autonomous mode (full AI control)."""
        # Continuous Hailo processing
        nav_data = None
        if self.hailo:
            detections, depth_map = self.hailo.process_frame(frame)
            nav_data = self.hailo.get_navigation_data()

        # Periodic VLM reasoning
        if self.should_query_vlm():
            self._query_vlm(frame)

        # Fuse decisions and generate command
        command = self._decide_action(nav_data)

        if command:
            self._send_command(command)

    def should_query_vlm(self) -> bool:
        """Check if we should query VLM."""
        if not self.use_vlm:
            return False

        current_time = time.time()
        elapsed = current_time - self.last_vlm_query_time

        return elapsed >= self.vlm_interval

    def _query_vlm(self, frame):
        """Query VLM for high-level reasoning."""
        if not self.vlm:
            return

        try:
            print("[VisionManager] Querying VLM...")
            start_time = time.time()

            # Convert frame to PIL Image if needed
            if isinstance(frame, np.ndarray):
                pil_image = Image.fromarray(frame)
            else:
                pil_image = frame

            # Get navigation guidance
            guidance = self.vlm.navigate_assistance(pil_image)
            scene = self.vlm.describe_scene(pil_image)

            # Update strategy
            self.strategy = VisionStrategy(
                scene_description=scene,
                navigation_guidance=guidance,
                recommended_action=self._parse_vlm_action(guidance),
                confidence=0.8,  # TODO: Extract from VLM response
                timestamp=time.time()
            )

            query_time = time.time() - start_time
            print(f"[VisionManager] VLM query completed in {query_time:.2f}s")
            print(f"[VisionManager] Guidance: {guidance[:100]}...")

            self.last_vlm_query_time = time.time()

        except Exception as e:
            print(f"[VisionManager] VLM query failed: {e}")

    def _parse_vlm_action(self, guidance: str) -> str:
        """
        Parse VLM guidance into action recommendation.

        Args:
            guidance: VLM navigation guidance text

        Returns:
            Action keyword (FORWARD, STOP, LEFT, RIGHT, etc.)
        """
        guidance_lower = guidance.lower()

        # Simple keyword matching
        if any(word in guidance_lower for word in ["stop", "halt", "danger", "unsafe"]):
            return "STOP"
        elif any(word in guidance_lower for word in ["left", "turn left"]):
            return "LEFT"
        elif any(word in guidance_lower for word in ["right", "turn right"]):
            return "RIGHT"
        elif any(word in guidance_lower for word in ["forward", "ahead", "straight"]):
            return "FORWARD"
        elif any(word in guidance_lower for word in ["back", "reverse"]):
            return "BACKWARD"
        else:
            return "ASSESS"

    def _decide_action(self, nav_data: Optional[NavigationData]) -> Optional[Dict[str, Any]]:
        """
        Fuse Hailo + VLM data to decide action.

        Args:
            nav_data: Navigation data from Hailo

        Returns:
            Command dict or None
        """
        # Priority 1: Critical alerts (immediate stop)
        if nav_data and nav_data.critical_alerts:
            return {"action": "STOP", "reason": "critical_alert"}

        # Priority 2: VLM strategic guidance
        if self.strategy and self.strategy.recommended_action != "ASSESS":
            action = self.strategy.recommended_action
            return {"action": action, "source": "vlm"}

        # Priority 3: Hailo obstacle avoidance
        if nav_data and nav_data.safe_directions:
            # Find safest direction
            safe_dirs = nav_data.safe_directions
            safest = max(safe_dirs, key=safe_dirs.get)

            # Map to movement command
            if safest == "LEFT":
                return {"action": "LEFT", "source": "hailo"}
            elif safest == "RIGHT":
                return {"action": "RIGHT", "source": "hailo"}
            elif safest == "CENTER" and safe_dirs["CENTER"] > 100:
                return {"action": "FORWARD", "source": "hailo"}
            else:
                return {"action": "STOP", "reason": "no_safe_path"}

        # Default: Continue current behavior
        return None

    def _send_command(self, command: Dict[str, Any]):
        """
        Send movement command via callback.

        Args:
            command: Command dictionary
        """
        if self.command_callback:
            try:
                self.command_callback(command)
            except Exception as e:
                print(f"[VisionManager] Command callback error: {e}")
        else:
            print(f"[VisionManager] Command: {command}")

    def get_status(self) -> Dict[str, Any]:
        """Get current vision system status."""
        status = {
            "mode": self.mode.value,
            "running": self.running,
            "hailo_enabled": self.use_hailo,
            "vlm_enabled": self.use_vlm,
            "simulation": self.simulation_mode
        }

        if self.hailo:
            status["hailo_stats"] = self.hailo.get_stats()

        if self.strategy:
            status["strategy"] = {
                "action": self.strategy.recommended_action,
                "confidence": self.strategy.confidence,
                "age": time.time() - self.strategy.timestamp
            }

        return status

    def manual_vlm_query(self, prompt: str) -> str:
        """
        Manually query VLM with custom prompt.

        Args:
            prompt: Custom prompt for VLM

        Returns:
            VLM response
        """
        if not self.vlm or self.current_frame is None:
            return "VLM not available"

        try:
            with self.lock:
                frame = self.current_frame

            if isinstance(frame, np.ndarray):
                frame = Image.fromarray(frame)

            response = self.vlm.get_text_response(frame, prompt)
            return response

        except Exception as e:
            return f"Error: {e}"

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
