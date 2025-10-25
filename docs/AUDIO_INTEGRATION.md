# Audio Integration: Piper TTS + WM8960 HAT

## Hardware Stack

```
┌─────────────────────────────┐
│  Freenove Board             │ ← Long dupont cables (30-50cm)
│  (Robot Control)            │
└─────────────────────────────┘
              ↑
     20-50cm dupont cables
              ↑
┌─────────────────────────────┐
│  WM8960 Audio HAT           │ ← Piper TTS output
│  (Text-to-Speech)           │
├─────────────────────────────┤
│  Hailo AI HAT+              │ ← Vision (26 TOPS)
│  (Object Detection)         │
├─────────────────────────────┤
│  Raspberry Pi 5             │ ← Brain
└─────────────────────────────┘
```

## GPIO Pin Usage Analysis

### WM8960 Audio HAT Pins
**I2S Audio Interface:**
- BCM 18 (Pin 12) - I2S CLK
- BCM 19 (Pin 35) - I2S FS (Frame Select/LRCLK)
- BCM 20 (Pin 38) - I2S DIN (Data In - for recording)
- BCM 21 (Pin 40) - I2S DOUT (Data Out - for playback)

**I2C Control:**
- BCM 2 (Pin 3) - SDA (shared with Freenove!)
- BCM 3 (Pin 5) - SCL (shared with Freenove!)

**Power:**
- 3.3V, 5V, GND

### Freenove Board Pins (from codebase)
- BCM 17 - Buzzer
- BCM 4 - Servo Power
- BCM 27 - Ultrasonic Trigger
- BCM 22 - Ultrasonic Echo
- BCM 2 - I2C SDA (shared!)
- BCM 3 - I2C SCL (shared!)

### Hailo AI HAT+
- All GPIO pass-through
- Primary communication via PCIe
- Minimal GPIO usage

## ⚠️ I2C Conflict Resolution

**Shared I2C Bus (BCM 2, 3):**
- Freenove devices: PCA9685 (0x40, 0x41), MPU6050 (0x68), ADS7830 (0x48)
- WM8960: 0x1A (default address)
- Hailo: 0x60 (if used)

**Good news:** Different I2C addresses = NO CONFLICT! ✅

All devices can share the same I2C bus as long as addresses are unique.

## Cable Requirements

### Freenove Dupont Cable Specs
**Required length:** 30-50cm (to reach from top of stack to robot body)

**Option 1: Buy Pre-made**
- 2x10 female-to-female dupont cable, 40-50cm
- Example: [40cm Dupont Cables](https://www.amazon.com/s?k=40cm+dupont+cable+female+2x10)
- Cost: $5-8

**Option 2: Extend Existing Cable**
- Buy: 2x20 female-to-female dupont ribbon cable (40-50cm)
- Use: First 20 pins (2x10) for Freenove
- Remaining 20 pins available for future expansion
- Cost: $6-10

**Option 3: DIY Extension**
- Buy: Individual female-to-female dupont wires (50cm)
- Bundle: 20 wires together for 2x10 connector
- Cost: $3-5
- Benefit: Can mix and match lengths

### Recommended: Option 2
Get a **2x20 (40-pin) female-to-female ribbon cable, 40-50cm**
- Use half (2x10) for Freenove
- Keep other half for expansion
- Clean, organized wiring

## Piper TTS Integration

### What is Piper?
- Fast, local neural TTS (Text-to-Speech)
- Runs on Raspberry Pi
- Multiple voices available
- Low latency (~100-500ms)

### Installation

```bash
# Install Piper TTS
sudo apt-get update
sudo apt-get install -y portaudio19-dev

# Download Piper
cd ~
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_arm64.tar.gz
tar -xzf piper_arm64.tar.gz
cd piper

# Download a voice (en_US-lessac-medium is good quality)
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# Test Piper
echo "Hello, I am your hexapod robot" | ./piper --model en_US-lessac-medium.onnx --output-raw | aplay -r 22050 -f S16_LE -t raw -
```

### Configure WM8960 as Default Audio

```bash
# Create asound.conf
sudo nano /etc/asound.conf
```

Add:
```
pcm.!default {
    type hw
    card 1
}

ctl.!default {
    type hw
    card 1
}
```

Test:
```bash
aplay -l  # List audio devices, find WM8960 card number
speaker-test -c2  # Test stereo output
```

## Vision + Voice Integration

### Architecture

```
Camera Frame
    ↓
Hailo Vision (object detection)
    ↓
VLM Analysis (scene understanding)
    ↓
Text Generation (description/narration)
    ↓
Piper TTS (convert to speech)
    ↓
WM8960 HAT (audio output)
    ↓
🔊 Robot speaks!
```

### Implementation Module

**File:** `src/tts_manager.py`

```python
"""Text-to-Speech manager with Piper integration."""

import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional
import threading
import queue


class PiperTTS:
    """Piper TTS integration for robot voice."""

    def __init__(
        self,
        piper_path: str = "/home/administrator/piper/piper",
        model_path: str = "/home/administrator/piper/en_US-lessac-medium.onnx",
        sample_rate: int = 22050
    ):
        self.piper_path = Path(piper_path)
        self.model_path = Path(model_path)
        self.sample_rate = sample_rate

        # Speech queue for async processing
        self.speech_queue = queue.Queue()
        self.speaking = False
        self.enabled = True

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
        if not self.enabled:
            return

        if blocking:
            self._speak_blocking(text)
        else:
            self.speech_queue.put(text)

    def _speak_blocking(self, text: str):
        """Speak text synchronously."""
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

        except Exception as e:
            print(f"[TTS] Error: {e}")

    def _speech_loop(self):
        """Background thread for async speech."""
        while True:
            text = self.speech_queue.get()
            self.speaking = True
            self._speak_blocking(text)
            self.speaking = False

    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self.speaking

    def clear_queue(self):
        """Clear pending speech."""
        while not self.speech_queue.empty():
            self.speech_queue.get()

    def enable(self):
        """Enable TTS."""
        self.enabled = True

    def disable(self):
        """Disable TTS."""
        self.enabled = False
        self.clear_queue()


class VoiceNarrator:
    """Narrates robot vision and actions."""

    def __init__(self, tts: PiperTTS, vision_manager, verbose: bool = True):
        self.tts = tts
        self.vision = vision_manager
        self.verbose = verbose

        # Narration settings
        self.narrate_detections = True
        self.narrate_navigation = True
        self.narrate_actions = True

    def narrate_scene(self, scene_description: str):
        """Narrate what the robot sees."""
        if not self.narrate_detections:
            return

        # Simplify VLM output for speech
        summary = self._summarize_scene(scene_description)
        self.tts.speak(f"I see {summary}")

    def narrate_obstacle(self, obstacle_type: str, direction: str):
        """Narrate obstacle detection."""
        if not self.narrate_navigation:
            return

        self.tts.speak(f"Warning: {obstacle_type} detected {direction}")

    def narrate_action(self, action: str):
        """Narrate movement action."""
        if not self.narrate_actions:
            return

        action_map = {
            "FORWARD": "moving forward",
            "BACKWARD": "moving backward",
            "LEFT": "turning left",
            "RIGHT": "turning right",
            "STOP": "stopping"
        }

        speech = action_map.get(action, action)
        self.tts.speak(speech)

    def greet(self):
        """Robot greeting."""
        self.tts.speak("Hello! I am your hexapod robot. My vision system is online.")

    def acknowledge_command(self, command: str):
        """Acknowledge user command."""
        self.tts.speak(f"Executing: {command}")

    def _summarize_scene(self, description: str) -> str:
        """Simplify VLM description for speech."""
        # Extract key objects
        # This is simplified - could use NLP for better summarization
        if len(description) > 100:
            return description[:100] + "..."
        return description
```

### Enhanced Vision Manager with Voice

**Update:** `src/vision_manager.py`

```python
# Add to VisionManager.__init__():
from tts_manager import PiperTTS, VoiceNarrator

self.tts = PiperTTS()
self.narrator = VoiceNarrator(self.tts, self)

# Startup greeting
self.narrator.greet()

# In _query_vlm() after getting scene description:
if self.narrator.narrate_detections:
    self.narrator.narrate_scene(scene)

# In _decide_action() before sending command:
if command and self.narrator.narrate_actions:
    self.narrator.narrate_action(command['action'])

# In _process_assisted() when obstacle detected:
if nav_data.critical_alerts:
    for alert in nav_data.critical_alerts:
        self.narrator.narrate_obstacle("obstacle", "ahead")
```

## Voice Commands (Future Enhancement)

With audio HAT, you can also add **speech recognition**:

### Option 1: Vosk (Local, Offline)
```bash
pip install vosk
# Download model
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
```

### Option 2: Whisper (OpenAI, more accurate)
```bash
pip install openai-whisper
# Requires more compute, but very accurate
```

### Voice Control Flow
```
Microphone (WM8960)
    ↓
Speech Recognition (Vosk/Whisper)
    ↓
Command Parser
    ↓
Robot Action
    ↓
Voice Confirmation (Piper)
    ↓
Speaker (WM8960)
```

## Shopping List

### Required
- [ ] **40-50cm 2x20 female-to-female dupont ribbon cable** - $6-10
  - [40cm option](https://www.amazon.com/s?k=40cm+female+dupont+ribbon+cable+40pin)

### Optional (Voice Control)
- [ ] **Microphone** (if WM8960 doesn't have one)
  - USB microphone or
  - I2S microphone module

## Installation Script

**File:** `setup_audio.sh`

```bash
#!/bin/bash
# Audio integration setup

echo "Installing Piper TTS..."
cd ~
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_arm64.tar.gz
tar -xzf piper_arm64.tar.gz
cd piper

# Download voice
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

echo "Configuring WM8960 audio..."
sudo bash -c 'cat > /etc/asound.conf <<EOF
pcm.!default {
    type hw
    card 1
}
ctl.!default {
    type hw
    card 1
}
EOF'

echo "Testing audio..."
aplay -l

echo "Installing Python dependencies..."
pip install sounddevice soundfile

echo "Done! Test with: echo 'Hello robot' | ~/piper/piper --model ~/piper/en_US-lessac-medium.onnx --output-raw | aplay -r 22050 -f S16_LE -t raw -"
```

## Test Plan

### 1. Hardware Test
```bash
# Check I2C devices
i2cdetect -y 1
# Should see: 0x1A (WM8960), 0x40, 0x41 (PCA9685), 0x48 (ADS7830), 0x68 (MPU6050)

# Test audio
speaker-test -c2
```

### 2. TTS Test
```bash
echo "I am alive" | ~/piper/piper --model ~/piper/en_US-lessac-medium.onnx --output-raw | aplay -r 22050 -f S16_LE -t raw -
```

### 3. Integration Test
```python
from src.tts_manager import PiperTTS

tts = PiperTTS()
tts.speak("Vision system online. Preparing for autonomous navigation.")
```

### 4. Full System Test
```python
from src.vision_manager import VisionManager, VisionMode

with VisionManager(simulation_mode=False) as vision:
    vision.set_mode(VisionMode.AUTONOMOUS)
    # Robot will narrate what it sees!
```

## Cable Management Tips

With 3 HATs stacked:
1. **Use cable ties** to bundle dupont cables neatly
2. **Label cables** with colored tape or labels
3. **Route cables** away from moving parts (legs)
4. **Secure connectors** with hot glue or mounting tape
5. **Test before final mounting** - make sure everything works first!

## System Capabilities (Final)

```
🤖 Shifusenpi-Bot FULL STACK
├── 👁️  Vision: Hailo-8 (26 TOPS real-time object detection)
├── 🧠  Reasoning: VLM (Llama 3.2 90B scene understanding)
├── 🗣️  Speech: Piper TTS (neural voice synthesis)
├── 🔊  Audio: WM8960 HAT (stereo output)
├── 🦿  Mobility: 6-legged hexapod (32 servos)
└── 🎯  Navigation: Autonomous with voice narration

= FULLY SENTIENT ROBOT MODE ACTIVATED 🚀
```

## Next Steps

1. **Order:** 40-50cm dupont cables ($6-10)
2. **Install:** Stack HATs (RPi5 → Hailo → WM8960)
3. **Connect:** Freenove via long cables
4. **Setup:** Run `setup_audio.sh`
5. **Test:** Voice + Vision integration
6. **Deploy:** Talking autonomous robot! 🎉

---

**Status:** Architecture designed, ready for audio HAT integration
**Estimated time:** 1 hour setup + testing
**Coolness factor:** 📈📈📈 OFF THE CHARTS
