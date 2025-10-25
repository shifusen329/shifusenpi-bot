# Hailo AI HAT+ Quick Start Guide

Get your Shifusenpi-Bot up and running with AI vision in under 30 minutes.

## Prerequisites

- Raspberry Pi 5 (8GB recommended)
- Hailo AI HAT+ (HAT-8L or HAT-8) properly installed
- Raspberry Pi Camera (v2 or v3)
- Internet connection
- ~10GB free disk space

## Quick Installation

### Step 1: Run Setup Script

```bash
cd ~/shifusenpi-bot
./setup_hailo.sh
```

This script will:
- Detect Hailo hardware
- Clone and install hailo-rpi5-examples
- Download AI models (YOLOv8, depth estimation)
- Install Python dependencies
- Create necessary symlinks

**Time: 10-15 minutes**

### Step 2: Verify Hailo Hardware

```bash
# Check if Hailo is detected
lspci | grep Hailo

# Expected output:
# 0000:01:00.0 Co-processor: Hailo Technologies Ltd. Hailo-8 AI Processor
```

### Step 3: Test Hailo Detection

```bash
cd ~/hailo-rpi5-examples
source setup_env.sh
python basic_pipelines/detection_simple.py --input rpi
```

You should see a window with real-time object detection.
Press `Ctrl+C` to stop.

### Step 4: Test Vision Integration

```bash
cd ~/shifusenpi-bot
python src/test_vision_integration.py
```

This runs the integration test suite with:
- Hailo simulation
- VLM integration
- Vision Manager

## Usage Examples

### Example 1: Real-Time Detection Only

```python
from src.hailo_vision import HailoVision

with HailoVision(enable_depth=True, enable_tracking=True) as hailo:
    hailo.start()

    # Process frame from camera
    detections, depth_map = hailo.process_frame(camera_frame)

    # Get navigation data
    nav_data = hailo.get_navigation_data()
    print(f"Obstacles: {len(nav_data.obstacles)}")
    print(f"Safe directions: {nav_data.safe_directions}")
```

### Example 2: Hybrid Vision (Hailo + VLM)

```python
from src.vision_manager import VisionManager, VisionMode

def handle_command(cmd):
    print(f"Robot should: {cmd['action']}")

with VisionManager(simulation_mode=False) as manager:
    manager.set_command_callback(handle_command)
    manager.set_mode(VisionMode.AUTONOMOUS)

    # Update with camera frames
    while True:
        frame = capture_camera_frame()
        manager.update_frame(frame)
        time.sleep(0.033)  # 30 FPS
```

### Example 3: Manual VLM Query

```python
from src.vision_manager import VisionManager

with VisionManager() as manager:
    manager.update_frame(camera_frame)

    # Ask VLM custom questions
    response = manager.manual_vlm_query(
        "Is it safe for the robot to move forward?"
    )
    print(response)
```

## Vision Modes

### Manual Mode
- **No AI assistance**
- User has full control
- Use for: Manual driving, calibration

```python
manager.set_mode(VisionMode.MANUAL)
```

### Assisted Mode
- **Hailo obstacle avoidance only**
- User controls, AI prevents collisions
- Use for: Safe manual navigation

```python
manager.set_mode(VisionMode.ASSISTED)
```

### Autonomous Mode
- **Full AI control** (Hailo + VLM)
- Robot navigates independently
- Use for: Autonomous missions

```python
manager.set_mode(VisionMode.AUTONOMOUS)
```

## Integration with Robot Control

### Add to Server (`Code/Server/main.py`)

```python
from src.vision_manager import VisionManager, VisionMode

class Server:
    def __init__(self):
        # ... existing code ...
        self.vision = VisionManager(simulation_mode=False)
        self.vision.set_command_callback(self.handle_vision_command)
        self.vision.start()

    def handle_vision_command(self, cmd):
        """Handle vision-generated commands."""
        action = cmd['action']

        if action == 'STOP':
            self.control.stop_movement()
        elif action == 'FORWARD':
            self.control.move_forward()
        elif action == 'LEFT':
            self.control.turn_left()
        elif action == 'RIGHT':
            self.control.turn_right()
```

### Add Vision Commands

Edit `Code/Server/command.py`:

```python
# Vision system commands
CMD_VISION_MODE = "CMD_VISION_MODE"          # Set mode: MANUAL|ASSISTED|AUTONOMOUS
CMD_VISION_STATUS = "CMD_VISION_STATUS"      # Get vision system status
CMD_VISION_QUERY = "CMD_VISION_QUERY"        # Manual VLM query
CMD_DETECTIONS = "CMD_DETECTIONS"            # Get current detections
CMD_DEPTH = "CMD_DEPTH"                      # Get depth data
```

## Performance Tuning

### Optimize for Speed (30 FPS)

```python
hailo = HailoVision(
    enable_depth=False,  # Disable depth for faster detection
    enable_tracking=True,
    confidence_threshold=0.6  # Higher = fewer detections, faster
)
```

### Optimize for Accuracy (15-20 FPS)

```python
hailo = HailoVision(
    enable_depth=True,   # Enable depth estimation
    enable_tracking=True,
    confidence_threshold=0.4  # Lower = more detections, slower
)
```

### Balance Power Usage

```python
manager = VisionManager(
    use_hailo=True,
    use_vlm=True,
    vlm_interval=10.0  # Query VLM every 10s (saves power)
)
```

## Troubleshooting

### Hailo Not Detected

```bash
# Check PCIe connection
lspci

# Reboot and check
sudo reboot
lspci | grep Hailo
```

### Low FPS / Choppy Video

```bash
# Monitor CPU usage
htop

# Monitor Hailo usage
hailortcli monitor

# Solutions:
# 1. Reduce resolution
# 2. Disable depth estimation
# 3. Increase confidence threshold
```

### VLM Errors

```bash
# Check .env credentials
cat .env

# Test VLM directly
python src/test_vlm_quick.py
```

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements_hailo.txt

# Source Hailo environment
cd ~/hailo-rpi5-examples
source setup_env.sh
```

## Next Steps

1. **Read Full Documentation**: `docs/HAILO_INTEGRATION_PLAN.md`
2. **Customize Detection Classes**: Edit `src/hailo_vision.py` CRITICAL_CLASSES
3. **Train Custom Models**: Follow Hailo retraining guide
4. **Integrate with GUI**: Add vision overlay to PyQt5 client
5. **Add Voice Commands**: Combine with speech recognition

## Useful Commands

```bash
# Test Hailo detection
cd ~/hailo-rpi5-examples && source setup_env.sh
python basic_pipelines/detection.py --input rpi

# Test depth estimation
python basic_pipelines/depth.py --input rpi

# Test pose estimation
python basic_pipelines/pose_estimation.py --input rpi

# Monitor Hailo
hailortcli monitor

# Check Hailo firmware
hailortcli fw-control identify
```

## Resources

- [Hailo RPi5 Examples](https://github.com/hailo-ai/hailo-rpi5-examples)
- [Hailo Community Forum](https://community.hailo.ai/)
- [Hailo Developer Zone](https://hailo.ai/developer-zone/)
- [Integration Plan](HAILO_INTEGRATION_PLAN.md)

## Support

- **Hardware Issues**: Check connections, reboot
- **Software Issues**: Check hailo-rpi5-examples repo issues
- **Integration Issues**: Review `docs/HAILO_INTEGRATION_PLAN.md`
- **VLM Issues**: Verify `.env` credentials

---

**Happy Building! Your robot now has eyes AND a brain.** 🤖👁️🧠
