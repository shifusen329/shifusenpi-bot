#!/usr/bin/env python3
"""Test script for Piper TTS and audio integration."""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from tts_manager import PiperTTS, VoiceNarrator


def test_basic_tts():
    """Test basic TTS functionality."""
    print("=" * 70)
    print("TEST 1: Basic TTS")
    print("=" * 70)

    tts = PiperTTS()

    print("\nTest 1.1: Simple speech (blocking)")
    tts.speak("Hello! I am your hexapod robot.", blocking=True)

    print("\nTest 1.2: Multiple phrases (async)")
    tts.speak("Testing asynchronous speech.")
    tts.speak("This should queue up.")
    tts.speak("And play in sequence.")

    # Wait for queue to finish
    time.sleep(5)

    print("\n✓ Basic TTS test passed\n")


def test_narrator():
    """Test voice narrator functionality."""
    print("=" * 70)
    print("TEST 2: Voice Narrator")
    print("=" * 70)

    tts = PiperTTS()
    narrator = VoiceNarrator(tts)

    print("\nTest 2.1: Greeting")
    narrator.greet()
    time.sleep(3)

    print("\nTest 2.2: Scene narration")
    narrator.narrate_scene("I can see a room with a chair, table, and a person standing near the door.")
    time.sleep(4)

    print("\nTest 2.3: Obstacle warning")
    narrator.narrate_obstacle("chair", "ahead", "2 meters")
    time.sleep(3)

    print("\nTest 2.4: Action narration")
    narrator.set_verbosity(actions=True)
    narrator.narrate_action("LEFT")
    time.sleep(2)
    narrator.narrate_action("FORWARD")
    time.sleep(2)

    print("\n✓ Narrator test passed\n")


def test_vision_integration():
    """Test TTS with vision system (simulation)."""
    print("=" * 70)
    print("TEST 3: Vision + Voice Integration")
    print("=" * 70)

    from vision_manager import VisionManager, VisionMode
    from PIL import Image, ImageDraw
    import numpy as np

    # Create test image
    img = Image.new('RGB', (640, 480), color='lightblue')
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 200, 300, 400], fill='brown', outline='black', width=3)
    draw.ellipse([400, 200, 550, 350], fill='red', outline='black', width=3)
    frame = np.array(img)

    # Create vision manager with TTS
    manager = VisionManager(
        use_hailo=True,
        use_vlm=True,
        vlm_interval=3.0,
        simulation_mode=True
    )

    try:
        manager.start()

        # Test manual mode (no narration)
        print("\nTest 3.1: Manual mode (silent)")
        manager.set_mode(VisionMode.MANUAL)
        manager.update_frame(frame)
        time.sleep(2)

        # Test autonomous mode (with narration)
        print("\nTest 3.2: Autonomous mode (with narration)")
        manager.set_mode(VisionMode.AUTONOMOUS)
        manager.update_frame(frame)

        # Wait for VLM query and narration
        print("Waiting for VLM + TTS (5 seconds)...")
        time.sleep(5)

        # Test manual VLM query
        print("\nTest 3.3: Manual VLM query")
        response = manager.manual_vlm_query("What objects do you see?")
        if manager.narrator:
            manager.narrator.narrate_scene(response[:100])  # Summarize
        time.sleep(3)

    finally:
        manager.stop()

    print("\n✓ Vision + Voice integration test passed\n")


def test_interactive():
    """Interactive TTS test."""
    print("=" * 70)
    print("TEST 4: Interactive TTS")
    print("=" * 70)

    tts = PiperTTS()
    narrator = VoiceNarrator(tts)

    print("\nInteractive mode - type text for robot to speak")
    print("Commands:")
    print("  greet - Robot greeting")
    print("  status - Report status")
    print("  quit - Exit")
    print()

    while True:
        try:
            text = input("Robot says> ").strip()

            if not text:
                continue

            if text.lower() in ['quit', 'exit', 'q']:
                narrator.say("Goodbye!")
                time.sleep(2)
                break

            elif text.lower() == 'greet':
                narrator.greet()

            elif text.lower() == 'status':
                narrator.report_status({'mode': 'manual'})

            else:
                narrator.say(text)

            # Wait for speech to complete
            time.sleep(0.5)
            while tts.is_speaking():
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break

    print("\n✓ Interactive test completed\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print(" Piper TTS + Audio Integration Test Suite")
    print("=" * 70 + "\n")

    try:
        # Check if Piper is installed
        piper_path = Path.home() / "piper" / "piper"
        if not piper_path.exists():
            print("⚠ Piper TTS not installed")
            print("\nRun: ./setup_audio.sh")
            print("\nRunning tests in SIMULATION mode (no audio)\n")

        # Run tests
        print("Select test to run:")
        print("  1. Basic TTS test")
        print("  2. Voice Narrator test")
        print("  3. Vision + Voice integration test")
        print("  4. Interactive mode")
        print("  5. Run all tests")
        print()

        choice = input("Enter choice (1-5): ").strip()

        if choice == '1':
            test_basic_tts()
        elif choice == '2':
            test_narrator()
        elif choice == '3':
            test_vision_integration()
        elif choice == '4':
            test_interactive()
        elif choice == '5':
            test_basic_tts()
            test_narrator()
            test_vision_integration()
        else:
            print("Invalid choice")

    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print(" Test Suite Complete")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
