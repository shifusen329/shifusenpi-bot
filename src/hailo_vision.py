"""Hailo AI HAT+ Vision Processing Module.

Real-time object detection, depth estimation, and tracking using Hailo-8L.
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import threading
import queue

import numpy as np


class DetectionClass(Enum):
    """Detection priority classes for navigation."""

    CRITICAL = "critical"  # Immediate stop required
    WARNING = "warning"    # Slow down
    TRACKABLE = "trackable"  # Can follow
    NEUTRAL = "neutral"    # Informational only


@dataclass
class Detection:
    """Object detection result."""

    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    track_id: Optional[int] = None
    depth: Optional[float] = None
    priority: DetectionClass = DetectionClass.NEUTRAL


@dataclass
class NavigationData:
    """Navigation-relevant vision data."""

    obstacles: List[Detection]
    safe_directions: Dict[str, float]  # direction -> distance in cm
    critical_alerts: List[str]
    depth_center: Optional[float] = None
    person_tracks: List[int] = None


class HailoVision:
    """Real-time vision processing with Hailo AI HAT+."""

    # COCO class mappings to priority
    CRITICAL_CLASSES = {"person", "chair", "couch", "bed", "stairs"}
    WARNING_CLASSES = {"car", "bicycle", "motorcycle", "dog", "cat", "bird"}
    TRACKABLE_CLASSES = {"person", "sports ball", "frisbee"}

    def __init__(
        self,
        model_path: Optional[str] = None,
        enable_depth: bool = True,
        enable_tracking: bool = True,
        confidence_threshold: float = 0.5
    ):
        """
        Initialize Hailo vision processor.

        Args:
            model_path: Path to Hailo HEF model file
            enable_depth: Enable depth estimation pipeline
            enable_tracking: Enable object tracking
            confidence_threshold: Minimum confidence for detections
        """
        self.model_path = model_path
        self.enable_depth = enable_depth
        self.enable_tracking = enable_tracking
        self.confidence_threshold = confidence_threshold

        # Pipeline state
        self.detection_pipeline = None
        self.depth_pipeline = None
        self.running = False

        # Results
        self.latest_detections = []
        self.latest_depth_map = None
        self.result_queue = queue.Queue(maxsize=10)

        # Stats
        self.fps = 0.0
        self.frame_count = 0
        self.last_fps_time = time.time()

        # Initialize Hailo
        self._init_hailo()

    def _init_hailo(self):
        """Initialize Hailo pipelines."""
        try:
            # Import Hailo modules
            sys.path.insert(0, str(Path.home() / "hailo-rpi5-examples"))
            from hailo_apps_infra.hailo_rpi_common import get_default_parser

            print("[Hailo] Initializing Hailo AI HAT+...")

            # TODO: Initialize detection pipeline
            # self.detection_pipeline = self._create_detection_pipeline()

            if self.enable_depth:
                # TODO: Initialize depth pipeline
                # self.depth_pipeline = self._create_depth_pipeline()
                pass

            print("[Hailo] Initialization complete")

        except ImportError as e:
            print(f"[Hailo] WARNING: Hailo libraries not found: {e}")
            print("[Hailo] Running in simulation mode")

        except Exception as e:
            print(f"[Hailo] ERROR: Initialization failed: {e}")
            raise

    def _create_detection_pipeline(self):
        """Create GStreamer detection pipeline."""
        # TODO: Implement GStreamer pipeline creation
        # Based on hailo-rpi5-examples/basic_pipelines/detection.py
        pass

    def _create_depth_pipeline(self):
        """Create depth estimation pipeline."""
        # TODO: Implement depth pipeline
        # Based on hailo-rpi5-examples/basic_pipelines/depth.py
        pass

    def start(self):
        """Start vision processing."""
        if self.running:
            print("[Hailo] Already running")
            return

        self.running = True
        print("[Hailo] Starting vision processing...")

        # TODO: Start pipelines
        # if self.detection_pipeline:
        #     self.detection_pipeline.start()

    def stop(self):
        """Stop vision processing."""
        if not self.running:
            return

        self.running = False
        print("[Hailo] Stopping vision processing...")

        # TODO: Stop pipelines
        # if self.detection_pipeline:
        #     self.detection_pipeline.stop()

    def process_frame(self, frame: np.ndarray) -> Tuple[List[Detection], Optional[np.ndarray]]:
        """
        Process a single frame through Hailo.

        Args:
            frame: Input image (numpy array)

        Returns:
            Tuple of (detections, depth_map)
        """
        start_time = time.time()

        # TODO: Implement actual Hailo inference
        # For now, return empty results
        detections = []
        depth_map = None

        # Update FPS
        self._update_fps()

        processing_time = (time.time() - start_time) * 1000
        if processing_time > 50:
            print(f"[Hailo] WARNING: Frame processing took {processing_time:.1f}ms")

        return detections, depth_map

    def detect_objects(self, frame: np.ndarray) -> List[Detection]:
        """
        Detect objects in frame.

        Args:
            frame: Input image

        Returns:
            List of detections
        """
        # TODO: Implement object detection
        # Parse HAILO_DETECTION metadata from GStreamer buffer
        return []

    def estimate_depth(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Estimate depth map for frame.

        Args:
            frame: Input image

        Returns:
            Depth map (320x256) or None
        """
        if not self.enable_depth:
            return None

        # TODO: Implement depth estimation
        # Parse HAILO_DEPTH_MASK from GStreamer buffer
        return None

    def get_navigation_data(self) -> NavigationData:
        """
        Extract navigation-relevant data from current detections.

        Returns:
            NavigationData with obstacles and safe directions
        """
        obstacles = self._filter_obstacles()
        safe_directions = self._analyze_depth_zones()
        critical_alerts = self._check_critical_conditions()
        person_tracks = self._get_person_tracks()

        # Get center depth
        depth_center = None
        if self.latest_depth_map is not None:
            h, w = self.latest_depth_map.shape
            depth_center = float(self.latest_depth_map[h//2, w//2])

        return NavigationData(
            obstacles=obstacles,
            safe_directions=safe_directions,
            critical_alerts=critical_alerts,
            depth_center=depth_center,
            person_tracks=person_tracks
        )

    def _filter_obstacles(self) -> List[Detection]:
        """Filter detections to navigation-relevant obstacles."""
        obstacles = []
        for det in self.latest_detections:
            if det.priority in (DetectionClass.CRITICAL, DetectionClass.WARNING):
                obstacles.append(det)
        return obstacles

    def _analyze_depth_zones(self) -> Dict[str, float]:
        """
        Analyze depth map to find safe movement directions.

        Returns:
            Dict mapping direction (LEFT, CENTER, RIGHT) to distance in cm
        """
        if self.latest_depth_map is None:
            return {"LEFT": 0.0, "CENTER": 0.0, "RIGHT": 0.0}

        h, w = self.latest_depth_map.shape

        # Divide into three zones
        left_zone = self.latest_depth_map[:, :w//3]
        center_zone = self.latest_depth_map[:, w//3:2*w//3]
        right_zone = self.latest_depth_map[:, 2*w//3:]

        # Calculate average depth for each zone
        # Note: depth values are relative, need calibration for real distances
        return {
            "LEFT": float(np.mean(left_zone)),
            "CENTER": float(np.mean(center_zone)),
            "RIGHT": float(np.mean(right_zone))
        }

    def _check_critical_conditions(self) -> List[str]:
        """Check for critical navigation conditions."""
        alerts = []

        # Check for critical obstacles
        for det in self.latest_detections:
            if det.priority == DetectionClass.CRITICAL:
                alerts.append(f"CRITICAL: {det.label} detected at confidence {det.confidence:.2f}")

        # Check for cliff/edge
        if self.latest_depth_map is not None:
            # Check for sudden depth drop (cliff detection)
            depth_center = self.latest_depth_map[self.latest_depth_map.shape[0]//2, :]
            if np.std(depth_center) > 50:  # Threshold for cliff detection
                alerts.append("CRITICAL: Possible edge/cliff detected")

        return alerts

    def _get_person_tracks(self) -> List[int]:
        """Get list of currently tracked person IDs."""
        tracks = []
        for det in self.latest_detections:
            if det.label == "person" and det.track_id is not None:
                tracks.append(det.track_id)
        return tracks

    def _classify_detection(self, label: str) -> DetectionClass:
        """Classify detection by navigation priority."""
        if label in self.CRITICAL_CLASSES:
            return DetectionClass.CRITICAL
        elif label in self.WARNING_CLASSES:
            return DetectionClass.WARNING
        elif label in self.TRACKABLE_CLASSES:
            return DetectionClass.TRACKABLE
        else:
            return DetectionClass.NEUTRAL

    def _update_fps(self):
        """Update FPS counter."""
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_fps_time

        if elapsed >= 1.0:
            self.fps = self.frame_count / elapsed
            self.frame_count = 0
            self.last_fps_time = current_time

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            "fps": self.fps,
            "detection_count": len(self.latest_detections),
            "depth_enabled": self.enable_depth,
            "tracking_enabled": self.enable_tracking,
            "running": self.running
        }

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


# Simulation mode for testing without Hailo hardware
class HailoVisionSimulator(HailoVision):
    """Simulator for testing without Hailo hardware."""

    def _init_hailo(self):
        """Skip Hailo initialization in simulator."""
        print("[Hailo Simulator] Running in simulation mode")

    def detect_objects(self, frame: np.ndarray) -> List[Detection]:
        """Generate fake detections for testing."""
        import random

        detections = []

        # Simulate 0-3 random detections
        for i in range(random.randint(0, 3)):
            detections.append(Detection(
                label=random.choice(["person", "chair", "cup", "book"]),
                confidence=random.uniform(0.6, 0.95),
                bbox=(
                    random.randint(0, 300),
                    random.randint(0, 200),
                    random.randint(300, 600),
                    random.randint(200, 400)
                ),
                track_id=random.randint(1, 10),
                priority=DetectionClass.NEUTRAL
            ))

        self.latest_detections = detections
        return detections

    def estimate_depth(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Generate fake depth map."""
        if not self.enable_depth:
            return None

        # Create simple gradient depth map
        depth_map = np.linspace(50, 200, 320*256).reshape(256, 320).astype(np.float32)
        self.latest_depth_map = depth_map
        return depth_map
