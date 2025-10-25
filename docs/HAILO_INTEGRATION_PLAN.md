# Hailo AI HAT+ Integration Plan for Shifusenpi-Bot

## Executive Summary

Integration of Hailo AI HAT+ (13 TOPS Hailo-8L) with the hexapod robot to enable:
- **Real-time on-device AI** for low-latency obstacle detection, tracking, and navigation
- **Hybrid AI architecture** combining Hailo (fast, local) + VLM (intelligent, cloud)
- **Autonomous navigation** with depth estimation and obstacle avoidance
- **Enhanced vision** with object detection, pose estimation, and tracking

---

## Hardware Capabilities

### Hailo-8 AI Processor
- **Performance**: 26 TOPS (double the Hailo-8L)
- **Latency**: < 50ms for inference
- **Power**: ~2.5W typical
- **Interface**: PCIe on RPi5

### Supported AI Tasks
1. **Object Detection** - YOLOv8m/l (80 COCO classes) - larger models enabled by 26 TOPS
2. **Pose Estimation** - YOLOv8m-pose (17 keypoints) - higher accuracy
3. **Instance Segmentation** - Per-object masks with better resolution
4. **Depth Estimation** - SCDepthV3 (320x256 depth maps)
5. **Object Tracking** - Multi-object tracking with IDs at full framerate

---

## Architecture: Hybrid AI System

### Three-Tier Processing Model

```
┌─────────────────────────────────────────────────────────────┐
│                    HEXAPOD ROBOT BRAIN                      │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌────────────────┐    ┌──────────────┐
│  TIER 1: HAILO│    │  TIER 2: VLM   │    │ TIER 3: USER │
│   (REACTIVE)  │    │  (COGNITIVE)   │    │  (MANUAL)    │
├───────────────┤    ├────────────────┤    ├──────────────┤
│ • Real-time   │    │ • Scene        │    │ • Remote     │
│ • <50ms       │    │   understanding│    │   control    │
│ • On-device   │    │ • Planning     │    │ • GUI        │
│ • Continuous  │    │ • Reasoning    │    │ • Override   │
└───────┬───────┘    └────────┬───────┘    └──────┬───────┘
        │                     │                    │
        │                     │                    │
        ▼                     ▼                    ▼
┌──────────────────────────────────────────────────────────┐
│              ROBOT CONTROL SYSTEM (control.py)           │
│  Movement • Gait • Attitude • Position • Servo Control   │
└──────────────────────────────────────────────────────────┘
```

### Processing Flow

```
Camera Frame (Picamera2)
    │
    ├─────────────────────┬──────────────────────┬─────────────┐
    │                     │                      │             │
    ▼                     ▼                      ▼             ▼
┌─────────┐      ┌────────────┐        ┌──────────────┐  ┌────────┐
│ Hailo   │      │ VLM Queue  │        │ TCP Stream   │  │ Record │
│Pipeline │      │(Async/Low  │        │(Client GUI)  │  │(Optional)│
│(30 FPS) │      │Frequency)  │        │(10-15 FPS)   │  │        │
└────┬────┘      └─────┬──────┘        └──────────────┘  └────────┘
     │                 │
     ▼                 ▼
┌─────────────┐  ┌──────────────┐
│Real-time    │  │Scene Analysis│
│Detections   │  │& Planning    │
│• Objects    │  │• Description │
│• Depth      │  │• Strategy    │
│• Tracking   │  │• Goals       │
└──────┬──────┘  └──────┬───────┘
       │                │
       └────────┬───────┘
                ▼
        ┌──────────────┐
        │Decision Fusion│
        │   Module      │
        └───────┬───────┘
                ▼
        ┌──────────────┐
        │ Movement      │
        │ Commands      │
        └───────────────┘
```

---

## Tier 1: Hailo Real-Time Processing

### Use Cases
- **Obstacle Detection**: Identify objects in path (30 FPS)
- **Depth Mapping**: Measure distances to objects
- **Person Tracking**: Follow humans with persistent IDs
- **Edge Detection**: Detect stairs, ledges, drop-offs
- **Collision Avoidance**: Real-time path adjustments

### Implementation

**Module**: `src/hailo_vision.py`

```python
class HailoVision:
    """Real-time vision processing with Hailo AI HAT+"""

    def __init__(self):
        self.detection_pipeline = None  # YOLOv8s detection
        self.depth_pipeline = None      # SCDepthV3 depth
        self.tracking_enabled = True

    def process_frame(self, frame):
        """Process single frame through Hailo"""
        detections = self.detect_objects(frame)
        depth_map = self.estimate_depth(frame)
        return detections, depth_map

    def get_navigation_data(self):
        """Extract navigation-relevant data"""
        obstacles = self.filter_obstacles()
        safe_directions = self.analyze_depth_zones()
        return NavigationData(obstacles, safe_directions)
```

### Detection Categories (Priority)
1. **Critical** (immediate stop): person, chair, stairs, edge
2. **Warning** (slow down): car, bicycle, dog, cat
3. **Trackable** (follow mode): person, ball
4. **Neutral** (informational): cup, book, plant

---

## Tier 2: VLM High-Level Reasoning

### Use Cases
- **Scene Understanding**: "What room is this?"
- **Goal Planning**: "Find the kitchen"
- **Object Recognition**: "Is this a charging station?"
- **Safety Assessment**: "Is this surface safe to walk on?"
- **Command Interpretation**: "Bring me the red cup"

### Implementation

**Module**: `src/vision_manager.py`

```python
class VisionManager:
    """Coordinates Hailo + VLM vision systems"""

    def __init__(self):
        self.hailo = HailoVision()
        self.vlm = VLMClient()
        self.vlm_interval = 5.0  # Query VLM every 5 seconds

    def autonomous_loop(self):
        """Main autonomous vision loop"""
        while self.running:
            # Continuous Hailo processing
            nav_data = self.hailo.get_navigation_data()

            # Periodic VLM reasoning (low frequency)
            if self.should_query_vlm():
                frame = self.get_current_frame()
                scene = self.vlm.describe_scene(frame)
                guidance = self.vlm.navigate_assistance(frame)
                self.update_strategy(scene, guidance)

            # Fuse decisions
            command = self.decide_action(nav_data, self.strategy)
            self.send_to_control(command)
```

### VLM Query Triggers
- **Timed**: Every 5-10 seconds
- **Event-driven**: New room detected, obstacle encountered
- **User-requested**: Manual analysis request
- **Uncertainty**: Hailo confidence < 0.5

---

## Tier 3: User Manual Control

### Existing System (Preserve)
- PyQt5 GUI remote control
- TCP video streaming
- Manual WASD movement
- Servo calibration
- Face recognition

### Enhancements
- **Overlay**: Show Hailo detections on video stream
- **Assisted Mode**: Collision prevention while manual driving
- **Autonomy Toggle**: Switch between manual/autonomous
- **Debug View**: Depth maps, bounding boxes, tracking IDs

---

## Module Structure

```
shifusenpi-bot/
├── src/
│   ├── hailo_vision.py          # Hailo pipeline integration
│   ├── vision_manager.py        # Hybrid Hailo + VLM coordinator
│   ├── vlm_client.py            # Existing VLM client
│   ├── navigation_ai.py         # AI-based navigation logic
│   ├── obstacle_map.py          # Spatial obstacle mapping
│   └── decision_fusion.py       # Multi-source decision making
│
├── Code/Server/
│   ├── hailo_server.py          # Hailo integration for server
│   ├── autonomous_control.py    # Autonomous movement controller
│   └── vision_command.py        # New vision-based commands
│
├── hailo_configs/
│   ├── detection.json           # Detection pipeline config
│   ├── depth.json               # Depth pipeline config
│   └── tracking.json            # Object tracking config
│
├── models/                      # Hailo HEF model files
│   ├── yolov8s_h8l.hef
│   ├── scdepthv3.hef
│   └── custom_obstacles.hef     # Future custom model
│
└── test/
    ├── test_hailo_vision.py
    ├── test_vision_manager.py
    └── test_autonomous_nav.py
```

---

## Command Protocol Extensions

### New Commands (Add to server.py)

```python
CMD_AUTONOMOUS_START   # Start autonomous navigation
CMD_AUTONOMOUS_STOP    # Stop autonomous mode
CMD_FOLLOW_PERSON      # Enable person-following mode
CMD_AVOID_OBSTACLES    # Toggle obstacle avoidance
CMD_DEPTH_MAP          # Request depth map data
CMD_DETECTIONS         # Get current detections list
CMD_VLM_QUERY          # Trigger manual VLM analysis
CMD_VISION_MODE        # Set: MANUAL | ASSISTED | AUTONOMOUS
```

### Response Format

```python
# Detection event
CMD_DETECTION#person#0.92#120#150#200#250#track_id_5

# Obstacle warning
CMD_OBSTACLE#chair#0.85#CENTER#85cm#STOP

# Depth zones
CMD_DEPTH_ZONES#LEFT:120cm#CENTER:45cm#RIGHT:200cm

# VLM analysis (async)
CMD_VLM_RESULT#Scene: Living room with couch and table. Safe to navigate left.
```

---

## Installation & Setup

### Phase 1: Hailo Software Stack

```bash
# 1. Verify Hailo HAT+ detected
lspci | grep Hailo

# 2. Install Hailo drivers (if not present)
# Follow: hailo-rpi5-examples/doc/install-raspberry-pi5.md

# 3. Install hailo-apps-infra
cd hailo-rpi5-examples
./install.sh
source setup_env.sh

# 4. Test Hailo
python basic_pipelines/detection_simple.py --input rpi
```

### Phase 2: Integration Dependencies

```bash
# Install vision integration packages
pip install -r requirements_hailo.txt
```

**requirements_hailo.txt**:
```
# Hailo integration
hailo-platform>=4.18.0
gstreamer-python>=1.0.0

# Spatial reasoning
scikit-learn>=1.3.0
scipy>=1.11.0

# Performance
multiprocessing-logging>=0.3.4

# Existing requirements
-r requirements.txt
```

### Phase 3: Model Setup

```bash
# Download Hailo models
cd hailo-rpi5-examples
./download_resources.sh --all

# Verify models
ls resources/models/*.hef

# Link to robot project
ln -s ~/hailo-rpi5-examples/resources ~/shifusenpi-bot/hailo_resources
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [x] VLM integration complete
- [ ] Install Hailo software stack
- [ ] Test basic detection pipeline
- [ ] Create `hailo_vision.py` wrapper
- [ ] Unit tests for Hailo integration

**Deliverable**: Real-time object detection working with camera

### Phase 2: Hybrid Vision (Week 2)
- [ ] Implement `vision_manager.py`
- [ ] Coordinate Hailo + VLM workflows
- [ ] Add depth estimation pipeline
- [ ] Create `navigation_ai.py`
- [ ] Test obstacle detection

**Deliverable**: Robot detects and reports obstacles in real-time

### Phase 3: Autonomous Navigation (Week 3)
- [ ] Implement `autonomous_control.py`
- [ ] Integrate vision with movement control
- [ ] Add safety zones and collision avoidance
- [ ] Person following mode
- [ ] Emergency stop logic

**Deliverable**: Robot navigates autonomously avoiding obstacles

### Phase 4: GUI Integration (Week 4)
- [ ] Add detection overlays to video stream
- [ ] Vision mode selector (manual/assisted/auto)
- [ ] Real-time detection display
- [ ] Depth map visualization
- [ ] Debug/monitoring panel

**Deliverable**: Enhanced GUI with AI vision feedback

### Phase 5: Advanced Features (Week 5+)
- [ ] Custom model training (robot-specific objects)
- [ ] Semantic SLAM (map building)
- [ ] Multi-robot coordination
- [ ] Voice command integration
- [ ] Gesture recognition with pose estimation

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| **Hailo Inference** | < 50ms | Object detection latency |
| **VLM Query** | 2-5s | Async, non-blocking |
| **Overall FPS** | 25-30 FPS | Camera + Hailo processing |
| **Obstacle Detection Range** | 50cm - 3m | Ultrasonic + depth fusion |
| **Tracking Accuracy** | > 90% | Person tracking retention |
| **CPU Usage** | < 40% | Leave headroom for control |
| **Memory** | < 2GB | Total system usage |

---

## Safety Features

### Fail-Safes
1. **Vision Loss**: Revert to ultrasonic-only navigation
2. **Hailo Failure**: Continue with VLM-only mode (degraded)
3. **High Uncertainty**: Reduce speed, increase sensor polling
4. **Cliff Detection**: Immediate stop if depth drop > 30cm
5. **Emergency Stop**: Any critical detection triggers stop

### Validation
- **Depth Cross-Check**: Validate with ultrasonic sensor
- **Detection Confidence**: Require > 0.7 for critical objects
- **Tracking Consistency**: Verify track ID stability
- **Battery Monitor**: Reduce AI load at < 20% battery

---

## Testing Strategy

### Unit Tests
```python
# test/test_hailo_vision.py
def test_detection_latency():
    """Ensure detection < 50ms"""

def test_depth_accuracy():
    """Validate depth estimation"""

def test_tracking_persistence():
    """Track object through occlusion"""
```

### Integration Tests
```python
# test/test_autonomous_nav.py
def test_obstacle_avoidance():
    """Navigate around chair"""

def test_person_following():
    """Follow tracked person"""

def test_edge_detection():
    """Detect stairs/ledges"""
```

### Real-World Tests
1. **Obstacle Course**: Chairs, boxes, stairs
2. **Person Following**: Track moving human
3. **Room Navigation**: Find objects in cluttered space
4. **Battery Endurance**: 60 min autonomous operation

---

## Cost-Benefit Analysis

### Hailo Benefits
✅ **13 TOPS** on-device AI (vs. 0 TOPS without)
✅ **< 50ms latency** (vs. 2-5s VLM cloud)
✅ **No internet required** for basic navigation
✅ **Privacy**: All processing on-device
✅ **30 FPS** real-time detection
✅ **Low power**: ~1-2W

### VLM Benefits
✅ **High-level reasoning** Hailo can't match
✅ **Language understanding** for commands
✅ **Scene context** beyond object detection
✅ **Novel object recognition** (zero-shot)
✅ **Strategic planning** capabilities

### Hybrid Advantage
🚀 **Best of both worlds**: Fast reaction (Hailo) + Smart planning (VLM)
🚀 **Graceful degradation**: System works if either fails
🚀 **Efficient**: VLM only when needed (5-10s intervals)
🚀 **Scalable**: Add more AI tiers as needed

---

## Future Enhancements

### Custom Models
- **Robot-Specific Objects**: Charging dock, obstacles, toys
- **Terrain Classification**: Carpet, tile, grass, gravel
- **Door Detection**: Navigate through doorways
- **Face Recognition**: Integrate with existing Face.py

### Advanced AI
- **Semantic SLAM**: Build semantic maps (couch in living room)
- **Predictive Pathing**: Anticipate human movement
- **Reinforcement Learning**: Optimize gait for terrain
- **Multi-Modal Fusion**: Audio + vision (sound localization)

### Ecosystem
- **Fleet Coordination**: Multiple robots share vision data
- **Remote Monitoring**: Cloud dashboard for robot fleet
- **Continuous Learning**: Upload edge cases for retraining
- **AR Visualization**: Project robot's "vision" via AR app

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Hailo compatibility** | High | Test on RPi5 before integration |
| **Performance overhead** | Medium | Profile CPU/memory, optimize pipelines |
| **Model accuracy** | Medium | Validate with real-world tests, tune thresholds |
| **Integration complexity** | Medium | Incremental phases, thorough testing |
| **Power consumption** | Low | Monitor battery, add power management |

---

## Success Metrics

### Milestone 1: Detection Working
- [ ] Hailo detects objects at 25+ FPS
- [ ] Latency < 100ms end-to-end
- [ ] CPU usage < 50%

### Milestone 2: Hybrid Vision
- [ ] Hailo + VLM both functional
- [ ] Decision fusion working
- [ ] No conflicts between systems

### Milestone 3: Autonomous Navigation
- [ ] Robot navigates 10m obstacle course
- [ ] Zero collisions in 10 test runs
- [ ] Person following works for 60s continuously

### Milestone 4: Production Ready
- [ ] 60 min battery life in autonomous mode
- [ ] < 5% false positive rate
- [ ] GUI fully integrated
- [ ] Documentation complete

---

## Resources

### Documentation
- [Hailo RPi5 Examples](https://github.com/hailo-ai/hailo-rpi5-examples)
- [Hailo Apps Infra](https://github.com/hailo-ai/hailo-apps-infra)
- [Hailo Developer Zone](https://hailo.ai/developer-zone/)
- [Hailo Community Forum](https://community.hailo.ai/)

### Models
- YOLOv8s/m: Object detection (80 classes)
- SCDepthV3: Depth estimation
- YOLOv8-pose: Human pose (17 keypoints)
- YOLACT: Instance segmentation

### Tools
- HailoRT: Runtime library
- Hailo Dataflow Compiler: Custom model compilation
- Hailo Model Zoo: Pre-trained models

---

## Team & Timeline

### Skills Needed
- **Python**: Hailo/VLM integration
- **GStreamer**: Pipeline customization
- **Robotics**: Navigation algorithms
- **ML/AI**: Model selection, tuning

### Estimated Timeline
- **Phase 1**: 1 week (Foundation)
- **Phase 2**: 1 week (Hybrid Vision)
- **Phase 3**: 1 week (Autonomous Nav)
- **Phase 4**: 1 week (GUI)
- **Phase 5**: Ongoing (Advanced Features)

**Total MVP**: 4 weeks
**Production Ready**: 6-8 weeks

---

## Conclusion

Integrating the Hailo AI HAT+ with the shifusenpi-bot creates a **world-class robotics platform**:

1. **Real-time AI** for instant obstacle detection and avoidance
2. **Intelligent reasoning** via VLM for high-level planning
3. **Hybrid architecture** combining speed + intelligence
4. **Autonomous navigation** with depth estimation and tracking
5. **Scalable foundation** for future AI enhancements

This positions the hexapod robot as a **cutting-edge AI robotics platform** capable of autonomous navigation, human interaction, and complex task execution.

**Next Step**: Begin Phase 1 - Install Hailo software stack and test basic detection.

---

**Document Version**: 1.0
**Last Updated**: 2025-10-25
**Author**: Claude Code AI Assistant
