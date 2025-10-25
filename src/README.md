# VLM Integration for Shifusenpi-Bot

Vision Language Model (VLM) integration for enhanced robot perception and navigation.

## Features

- **Image Analysis**: Analyze images from robot camera
- **Object Detection**: Identify objects in the environment
- **Scene Description**: Get detailed scene descriptions
- **Navigation Assistance**: AI-powered navigation guidance
- **REST API**: LiteLLM gateway integration

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```
LITELLM_BASE_URL=http://your-gateway.com
LITELLM_API_KEY=sk-your-key
VISION_MODEL=llama3.2-vision:90b-instruct-q4_K_M
```

### 3. Run Tests

```bash
# Run all tests
pytest test/test_vlm_api.py -v

# Run only integration tests
pytest test/test_vlm_api.py -v -m integration

# Run manual test script
python test/test_vlm_api.py
```

## Usage Example

```python
from src.vlm_client import VLMClient
from PIL import Image

# Initialize client
with VLMClient() as client:
    # Load image
    img = Image.open("robot_view.jpg")

    # Analyze scene
    description = client.describe_scene(img)
    print(f"Scene: {description}")

    # Get navigation guidance
    guidance = client.navigate_assistance(img)
    print(f"Navigation: {guidance}")

    # Detect objects
    objects = client.detect_objects(img)
    print(f"Objects: {objects}")
```

## API Methods

### VLMClient

- `analyze_image(image, prompt, max_tokens, temperature)` - Full API response
- `get_text_response(image, prompt)` - Text-only response
- `detect_objects(image)` - Object detection
- `describe_scene(image)` - Scene description
- `navigate_assistance(image)` - Navigation guidance

### Image Input Formats

Supports multiple image sources:
- File path: `"path/to/image.jpg"`
- PIL Image: `Image.open("image.jpg")`
- Bytes: `image_bytes`

## Integration with Robot

The VLM client can be integrated with the robot's camera:

```python
from picamera2 import Picamera2
from src.vlm_client import VLMClient

# Capture from camera
picam2 = Picamera2()
picam2.start()
image_path = "current_view.jpg"
picam2.capture_file(image_path)

# Analyze with VLM
with VLMClient() as vlm:
    guidance = vlm.navigate_assistance(image_path)
    # Use guidance for robot control decisions
```

## Architecture

```
┌─────────────────┐
│  Robot Camera   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│   VLM Client    │─────▶│ LiteLLM Gateway  │
│  (vlm_client.py)│      │  (REST API)      │
└─────────────────┘      └────────┬─────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐      ┌──────────────────┐
│ Robot Control   │      │  Vision Model    │
│   (control.py)  │      │ (Llama 3.2 90B)  │
└─────────────────┘      └──────────────────┘
```

## License

Same as parent project (CC BY-NC-SA 3.0)
