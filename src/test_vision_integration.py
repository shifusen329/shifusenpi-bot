#!/usr/bin/env python3
"""Test script for Hailo + VLM vision integration."""

import sys
import time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from vision_manager import VisionManager, VisionMode
from hailo_vision import HailoVisionSimulator


def create_test_frame():
    """Create synthetic test frame."""
    # Create 640x480 image
    img = Image.new('RGB', (640, 480), color='lightblue')
    draw = ImageDraw.Draw(img)

    # Draw floor
    draw.rectangle([0, 400, 640, 480], fill='gray')

    # Draw obstacles
    draw.rectangle([100, 250, 200, 400], fill='brown', outline='black', width=3)  # Box
    draw.ellipse([400, 200, 500, 300], fill='red', outline='black', width=3)      # Ball
    draw.polygon([(300, 350), (350, 400), (250, 400)], fill='green', outline='black', width=3)  # Pyramid

    # Draw person
    draw.ellipse([500, 180, 580, 250], fill='peachpuff', outline='black', width=2)  # Head
    draw.rectangle([515, 250, 565, 350], fill='blue', outline='black', width=2)     # Body

    # Add text
    draw.text((10, 10), "Robot Vision Test Frame", fill='black')

    return np.array(img)


def test_hailo_only():
    """Test Hailo vision only (simulation mode)."""
    print("=" * 70)
    print("TEST 1: Hailo Vision Only (Simulation)")
    print("=" * 70)

    hailo = HailoVisionSimulator(enable_depth=True, enable_tracking=True)
    hailo.start()

    try:
        # Create test frame
        frame = create_test_frame()

        # Process frame
        print("\nProcessing frame...")
        detections, depth_map = hailo.process_frame(frame)

        # Get navigation data
        nav_data = hailo.get_navigation_data()

        # Display results
        print(f"\nDetections: {len(detections)}")
        for det in detections:
            print(f"  - {det.label}: {det.confidence:.2f} (track_id: {det.track_id})")

        print(f"\nDepth zones:")
        for direction, distance in nav_data.safe_directions.items():
            print(f"  {direction}: {distance:.1f}cm")

        print(f"\nObstacles: {len(nav_data.obstacles)}")
        print(f"Critical alerts: {nav_data.critical_alerts}")

        stats = hailo.get_stats()
        print(f"\nStats: {stats}")

    finally:
        hailo.stop()

    print("\n✓ Hailo test passed\n")


def test_vision_manager():
    """Test VisionManager with both Hailo + VLM."""
    print("=" * 70)
    print("TEST 2: Vision Manager (Hailo + VLM)")
    print("=" * 70)

    # Track commands
    commands_received = []

    def command_callback(cmd):
        commands_received.append(cmd)
        print(f"  → Command: {cmd}")

    manager = VisionManager(
        use_hailo=True,
        use_vlm=True,
        vlm_interval=3.0,  # Query VLM every 3 seconds
        simulation_mode=True
    )

    manager.set_command_callback(command_callback)

    try:
        # Start manager
        manager.start()
        print("\nVision manager started")

        # Test manual mode
        print("\n--- Testing MANUAL mode ---")
        manager.set_mode(VisionMode.MANUAL)
        frame = create_test_frame()
        manager.update_frame(frame)
        time.sleep(1)

        # Test assisted mode
        print("\n--- Testing ASSISTED mode ---")
        manager.set_mode(VisionMode.ASSISTED)
        manager.update_frame(frame)
        time.sleep(2)

        # Test autonomous mode
        print("\n--- Testing AUTONOMOUS mode ---")
        manager.set_mode(VisionMode.AUTONOMOUS)
        manager.update_frame(frame)
        print("Waiting for VLM query (this may take 5-10 seconds)...")
        time.sleep(6)  # Wait for VLM query

        # Get status
        status = manager.get_status()
        print(f"\nVision Manager Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")

        print(f"\nTotal commands sent: {len(commands_received)}")

    finally:
        manager.stop()

    print("\n✓ Vision Manager test passed\n")


def test_manual_vlm_query():
    """Test manual VLM query."""
    print("=" * 70)
    print("TEST 3: Manual VLM Query")
    print("=" * 70)

    manager = VisionManager(
        use_hailo=False,
        use_vlm=True,
        simulation_mode=True
    )

    try:
        manager.start()

        frame = create_test_frame()
        manager.update_frame(frame)

        print("\nQuerying VLM: 'What objects do you see?'")
        response = manager.manual_vlm_query("What objects do you see in this image? List them.")
        print(f"\nVLM Response:\n{response}\n")

        print("\nQuerying VLM: 'Is it safe to move forward?'")
        response = manager.manual_vlm_query("Is it safe for a robot to move forward in this scene?")
        print(f"\nVLM Response:\n{response}\n")

    except Exception as e:
        print(f"Error: {e}")
        print("Note: VLM test requires valid .env credentials")

    finally:
        manager.stop()

    print("\n✓ Manual VLM query test completed\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print(" Hailo + VLM Vision Integration Test Suite")
    print("=" * 70 + "\n")

    try:
        # Test 1: Hailo only
        test_hailo_only()

        # Test 2: Vision Manager
        test_vision_manager()

        # Test 3: Manual VLM query (requires .env credentials)
        print("Would you like to test VLM integration? (requires .env credentials)")
        print("This will make actual API calls to your LiteLLM gateway.")

        user_input = input("Run VLM test? (y/n): ").strip().lower()
        if user_input == 'y':
            test_manual_vlm_query()
        else:
            print("\nSkipping VLM test")

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
