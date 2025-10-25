#!/usr/bin/env python3
"""Test async robot brain with separated VLM + personality LLM."""

import sys
import time
import os
from pathlib import Path
import asyncio

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
from PIL import Image, ImageDraw
from dotenv import load_dotenv

from async_brain import AsyncRobotBrain, SceneUnderstanding, PersonalityResponse


def create_test_scene():
    """Create synthetic test scene."""
    img = Image.new('RGB', (640, 480), color='lightblue')
    draw = ImageDraw.Draw(img)

    # Draw environment
    draw.rectangle([0, 400, 640, 480], fill='gray')  # Floor
    draw.rectangle([100, 250, 200, 400], fill='brown', outline='black', width=3)  # Chair
    draw.ellipse([400, 300, 500, 400], fill='red', outline='black', width=3)  # Ball

    # Draw person
    draw.ellipse([500, 180, 580, 250], fill='peachpuff', outline='black', width=2)  # Head
    draw.rectangle([515, 250, 565, 350], fill='blue', outline='black', width=2)     # Body

    draw.text((10, 10), "Robot Test Scene", fill='black')

    return np.array(img)


def test_async_brain():
    """Test async brain with real API calls."""
    print("=" * 70)
    print(" ASYNC ROBOT BRAIN TEST")
    print("=" * 70)

    # Load credentials
    load_dotenv()
    base_url = os.getenv('LITELLM_BASE_URL')
    api_key = os.getenv('LITELLM_API_KEY')
    vision_model = os.getenv('VISION_MODEL')

    if not all([base_url, api_key, vision_model]):
        print("\n❌ Missing environment variables!")
        print("Required: LITELLM_BASE_URL, LITELLM_API_KEY, VISION_MODEL")
        return

    # Initialize async brain
    print(f"\nInitializing with:")
    print(f"  VLM: {vision_model}")
    print(f"  LLM: {vision_model} (same for now)")
    print(f"  Endpoint: {base_url}\n")

    brain = AsyncRobotBrain(
        vlm_url=base_url,
        vlm_model=vision_model,
        llm_url=base_url,
        llm_model=vision_model,  # Can be different model
        api_key=api_key,
        personality="friendly",
        vlm_interval=5.0  # Analyze scene every 5 seconds
    )

    try:
        brain.start()

        # Create test scene
        print("[1/4] Creating test scene...")
        scene_frame = create_test_scene()
        brain.update_frame(scene_frame)

        # Wait for first VLM analysis
        print("[2/4] Waiting for VLM scene analysis...")
        for i in range(10):
            time.sleep(1)
            scene = brain.get_latest_scene()
            if scene:
                print(f"\n✓ Scene analyzed!")
                print(f"  Scene type: {scene.scene_type}")
                print(f"  Objects: {[obj['name'] for obj in scene.objects]}")
                print(f"  People: {scene.people_count}")
                print(f"  Obstacles: {scene.obstacles}")
                print(f"  Safe directions: {scene.safe_directions}")
                print(f"  Description: {scene.description}")
                print(f"  Confidence: {scene.confidence:.2f}")
                break
        else:
            print("⚠️  No scene data received (timeout)")
            scene = None

        # Test personality responses
        print("\n[3/4] Testing personality LLM...")

        test_inputs = [
            "What do you see?",
            "Should I move forward?",
            "Is it safe here?"
        ]

        for user_input in test_inputs:
            print(f"\n👤 User: \"{user_input}\"")

            response = brain.get_personality_response(
                user_input,
                scene_context=scene
            )

            print(f"🤖 Robot: \"{response.text}\"")
            print(f"   Emotion: {response.emotion}")
            if response.action_suggested:
                print(f"   Suggested action: {response.action_suggested}")

            time.sleep(1)

        # Stats
        print("\n[4/4] System statistics:")
        stats = brain.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")

        print("\n" + "=" * 70)
        print(" TEST COMPLETE ✓")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        brain.stop()


def test_json_parsing():
    """Test JSON parsing from VLM responses."""
    print("=" * 70)
    print(" JSON PARSING TEST")
    print("=" * 70)

    from async_brain import AsyncRobotBrain

    brain = AsyncRobotBrain(
        vlm_url="http://test",
        vlm_model="test",
        llm_url="http://test",
        llm_model="test",
        api_key="test"
    )

    # Test various JSON response formats
    test_cases = [
        # Clean JSON
        '''{"objects": [{"name": "chair", "position": "left", "confidence": 0.9}], "scene_type": "indoor", "obstacles": ["chair"], "people_count": 1, "safe_directions": ["right"], "description": "Indoor room with chair", "confidence": 0.85}''',

        # JSON in markdown
        '''```json
{"objects": [], "scene_type": "outdoor", "obstacles": [], "people_count": 0, "safe_directions": ["forward", "left", "right"], "description": "Open outdoor area", "confidence": 0.9}
```''',

        # Invalid JSON (fallback)
        "This is just text describing a scene"
    ]

    for i, test_json in enumerate(test_cases, 1):
        print(f"\nTest case {i}:")
        print(f"Input: {test_json[:60]}...")

        result = brain._parse_scene_json(test_json)

        print(f"Parsed:")
        print(f"  Scene type: {result.scene_type}")
        print(f"  Objects: {len(result.objects)}")
        print(f"  Description: {result.description[:50]}...")
        print(f"  Confidence: {result.confidence}")

    print("\n" + "=" * 70)
    print(" JSON PARSING TEST COMPLETE ✓")
    print("=" * 70)


def demo_architecture():
    """Show the async architecture diagram."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║          ASYNC ROBOT BRAIN ARCHITECTURE                  ║
╚═══════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────┐
│                   CAMERA INPUT                          │
│                  (30 FPS stream)                        │
└──────────────┬──────────────────────────────────────────┘
               │
               ├────────────────────┬─────────────────────┐
               │                    │                     │
               ▼                    ▼                     ▼
        ┌──────────┐         ┌──────────┐        ┌──────────┐
        │  HAILO   │         │   VLM    │        │ DISPLAY  │
        │Real-time │         │  Async   │        │ (Client) │
        │30 FPS    │         │ 3-5 sec  │        │          │
        │Detection │         │intervals │        │          │
        └────┬─────┘         └────┬─────┘        └──────────┘
             │                    │
             │  Immediate         │  Structured JSON
             │  Obstacles         │  Scene Understanding
             │                    │
             ▼                    ▼
        ┌────────────────────────────────┐
        │    DECISION FUSION             │
        │  - VLM scene context           │
        │  - Hailo real-time obstacles   │
        │  - User voice commands         │
        └───────────────┬────────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │   PERSONALITY LLM (Async)     │
        │  - Natural language response  │
        │  - Emotion                    │
        │  - Action suggestion          │
        └───────────────┬───────────────┘
                        │
            ┌───────────┼──────────┐
            │           │          │
            ▼           ▼          ▼
      ┌─────────┐  ┌────────┐  ┌─────────┐
      │ SPEAKER │  │ MOTORS │  │ DISPLAY │
      │   TTS   │  │ Servos │  │  Debug  │
      └─────────┘  └────────┘  └─────────┘

KEY FEATURES:
✓ Non-blocking async API calls
✓ Structured JSON responses (easy parsing)
✓ Separate VLM (vision) and LLM (personality)
✓ Real-time Hailo for safety
✓ Periodic VLM for context (not every frame)
""")


if __name__ == "__main__":
    print("\n")

    # Show architecture
    demo_architecture()

    # Test JSON parsing
    test_json_parsing()

    print("\n\nReady to test with real API?")
    print("This will make actual calls to your LiteLLM gateway.")

    user_input = input("\nRun live test? (y/n): ").strip().lower()
    if user_input == 'y':
        test_async_brain()
    else:
        print("\nSkipping live test. Use 'python src/test_async_brain.py' to run later.")
